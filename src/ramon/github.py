# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""Fetch repository state from GitHub with batched GraphQL queries via 'gh'."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

# Smaller queries return sooner; with 37 repositories, chunks of 5 took 2.0 s
# and chunks of 25 took 5.6 s. The cap stays below GitHub's limit on
# concurrent requests.
CHUNK_SIZE = 5
MAX_CONCURRENT = 8
PR_LIMIT = 30
ISSUE_LIMIT = 30

FAILING = {"FAILURE", "ERROR"}

REPO_FIELDS = f"""
  nameWithOwner url isArchived pushedAt
  defaultBranchRef {{
    name
    target {{ ... on Commit {{ messageHeadline statusCheckRollup {{ state }} }} }}
  }}
  pullRequests(states: OPEN, first: {PR_LIMIT},
               orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
    totalCount
    nodes {{
      number title url isDraft updatedAt reviewDecision
      author {{ login }}
      reviewRequests(first: 20) {{
        nodes {{ requestedReviewer {{ ... on User {{ login }} }} }}
      }}
      commits(last: 1) {{ nodes {{ commit {{ statusCheckRollup {{ state }} }} }} }}
    }}
  }}
  issues(states: OPEN, first: {ISSUE_LIMIT},
         orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
    totalCount
    nodes {{
      number title url updatedAt
      author {{ login }}
      labels(first: 5) {{ nodes {{ name }} }}
    }}
  }}
  latestRelease {{ tagName publishedAt }}
"""

OWNER_QUERY = """
query($login: String!, $after: String) {
  repositoryOwner(login: $login) {
    repositories(first: 100, after: $after, isArchived: false,
                 orderBy: {field: NAME, direction: ASC}) {
      nodes { nameWithOwner }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


class GhError(Exception):
    pass


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    author: str
    is_draft: bool
    updated_at: datetime | None
    review_decision: str | None
    checks: str | None
    reviewers: list[str] = field(default_factory=list)


@dataclass
class Issue:
    number: int
    title: str
    url: str
    author: str
    updated_at: datetime | None
    labels: list[str] = field(default_factory=list)


@dataclass
class Repo:
    name: str
    url: str = ""
    archived: bool = False
    pushed_at: datetime | None = None
    branch: str | None = None
    head_headline: str = ""
    checks: str | None = None
    pr_count: int = 0
    prs: list[PullRequest] = field(default_factory=list)
    issue_count: int = 0
    issues: list[Issue] = field(default_factory=list)
    release: str | None = None
    released_at: datetime | None = None
    error: str | None = None

    def needs_attention(self, viewer: str) -> bool:
        """True when the default branch fails, a PR awaits the viewer's
        review, or one of the viewer's PRs fails its checks."""

        if self.error or self.checks in FAILING:
            return True
        for pr in self.prs:
            if viewer in pr.reviewers:
                return True
            if pr.author == viewer and pr.checks in FAILING:
                return True
        return False


@dataclass
class Snapshot:
    viewer: str
    repos: list[Repo]
    fetched_at: datetime


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _login(node: dict | None) -> str:
    # A deleted account is returned as a null author.
    return (node or {}).get("login") or "ghost"


def build_query(names: list[str]) -> tuple[str, dict[str, str]]:
    """Return a query with one aliased 'repository' field per name, and its
    variables. Names go in as variables so that they need no escaping."""

    params = []
    fields = []
    variables = {}
    for idx, name in enumerate(names):
        owner, repo = name.split("/", 1)
        params.append(f"$o{idx}: String!, $n{idx}: String!")
        fields.append(
            f"r{idx}: repository(owner: $o{idx}, name: $n{idx}) {{ ...repo }}"
        )
        variables[f"o{idx}"] = owner
        variables[f"n{idx}"] = repo

    query = (
        f"query({', '.join(params)}) {{\n  viewer {{ login }}\n  "
        + "\n  ".join(fields)
        + f"\n}}\nfragment repo on Repository {{{REPO_FIELDS}}}\n"
    )
    return query, variables


def parse_pr(node: dict) -> PullRequest:
    commits = node.get("commits", {}).get("nodes") or []
    rollup = commits[0]["commit"].get("statusCheckRollup") if commits else None
    reviewers = [
        r["requestedReviewer"]["login"]
        for r in node.get("reviewRequests", {}).get("nodes", [])
        if r.get("requestedReviewer") and r["requestedReviewer"].get("login")
    ]
    return PullRequest(
        number=node["number"],
        title=node["title"],
        url=node["url"],
        author=_login(node.get("author")),
        is_draft=node["isDraft"],
        updated_at=_ts(node["updatedAt"]),
        review_decision=node.get("reviewDecision"),
        checks=(rollup or {}).get("state"),
        reviewers=reviewers,
    )


def parse_issue(node: dict) -> Issue:
    return Issue(
        number=node["number"],
        title=node["title"],
        url=node["url"],
        author=_login(node.get("author")),
        updated_at=_ts(node["updatedAt"]),
        labels=[label["name"] for label in node.get("labels", {}).get("nodes", [])],
    )


def parse_repo(node: dict) -> Repo:
    ref = node.get("defaultBranchRef") or {}
    target = ref.get("target") or {}
    release = node.get("latestRelease") or {}
    return Repo(
        name=node["nameWithOwner"],
        url=node["url"],
        archived=node["isArchived"],
        pushed_at=_ts(node.get("pushedAt")),
        branch=ref.get("name"),
        head_headline=target.get("messageHeadline", ""),
        checks=(target.get("statusCheckRollup") or {}).get("state"),
        pr_count=node["pullRequests"]["totalCount"],
        prs=[parse_pr(n) for n in node["pullRequests"]["nodes"]],
        issue_count=node["issues"]["totalCount"],
        issues=[parse_issue(n) for n in node["issues"]["nodes"]],
        release=release.get("tagName"),
        released_at=_ts(release.get("publishedAt")),
    )


def parse_response(names: list[str], payload: dict) -> tuple[str, list[Repo]]:
    """Return the viewer login and one Repo per name, in the order given.
    A repository GraphQL could not resolve becomes a Repo with 'error' set."""

    data = payload.get("data") or {}
    errors = {}
    for err in payload.get("errors", []):
        path = err.get("path") or []
        if path:
            errors[path[0]] = err.get("message", "unknown error")

    if not data and payload.get("errors"):
        raise GhError("; ".join(e.get("message", "?") for e in payload["errors"]))

    viewer = (data.get("viewer") or {}).get("login", "")
    repos = []
    for idx, name in enumerate(names):
        alias = f"r{idx}"
        node = data.get(alias)
        if node is None:
            repos.append(Repo(name=name, error=errors.get(alias, "not found")))
        else:
            repos.append(parse_repo(node))
    return viewer, repos


async def graphql(query: str, variables: dict) -> dict:
    """Run a query with 'gh api graphql' and return the decoded response.

    'gh' exits non-zero when any part of the query fails, also when the rest
    of the response holds data, so the exit status alone is not used."""

    body = json.dumps({"query": query, "variables": variables}).encode()
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "api",
            "graphql",
            "--input",
            "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise GhError("'gh' is not installed or not on PATH") from None

    stdout, stderr = await proc.communicate(body)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        msg = stderr.decode(errors="replace").strip() or f"gh exited {proc.returncode}"
        raise GhError(msg) from None
    if not isinstance(payload, dict):
        raise GhError(f"unexpected response from gh: {stdout[:200]!r}")
    return payload


async def owner_repos(login: str) -> list[str]:
    names: list[str] = []
    after = None
    while True:
        payload = await graphql(OWNER_QUERY, {"login": login, "after": after})
        owner = (payload.get("data") or {}).get("repositoryOwner")
        if owner is None:
            msgs = [e.get("message", "?") for e in payload.get("errors", [])]
            raise GhError(f"owner {login!r}: {'; '.join(msgs) or 'not found'}")
        page = owner["repositories"]
        names.extend(n["nameWithOwner"] for n in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return names
        after = page["pageInfo"]["endCursor"]


async def fetch_chunk(
    names: list[str], limit: asyncio.Semaphore
) -> tuple[str, list[Repo]]:
    query, variables = build_query(names)
    try:
        async with limit:
            payload = await graphql(query, variables)
        return parse_response(names, payload)
    except GhError as exc:
        return "", [Repo(name=name, error=str(exc)) for name in names]


async def fetch(repos: list[str], owners: list[str]) -> Snapshot:
    """Fetch every repository in 'repos' and every non-archived repository of
    'owners', in chunks of CHUNK_SIZE with MAX_CONCURRENT queries in flight."""

    names = list(repos)
    for found in await asyncio.gather(*(owner_repos(o) for o in owners)):
        names.extend(found)
    names = list(dict.fromkeys(names))

    chunks = [names[i : i + CHUNK_SIZE] for i in range(0, len(names), CHUNK_SIZE)]
    limit = asyncio.Semaphore(MAX_CONCURRENT)
    results = await asyncio.gather(*(fetch_chunk(c, limit) for c in chunks))

    viewer = next((v for v, _ in results if v), "")
    return Snapshot(
        viewer=viewer,
        repos=[repo for _, chunk in results for repo in chunk],
        fetched_at=datetime.now(UTC),
    )
