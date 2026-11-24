# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import json
import stat

import pytest
from conftest import pr_node, repo_node

from ramon import github


def test_build_query_passes_names_as_variables():
    query, variables = github.build_query(["o/a", "x-y/b.c"])
    assert variables == {"o0": "o", "n0": "a", "o1": "x-y", "n1": "b.c"}
    assert "r1: repository(owner: $o1, name: $n1)" in query
    assert "b.c" not in query


def test_parse_response_keeps_order_and_marks_unresolved(payload):
    viewer, repos = github.parse_response(["o/ok", "o/missing", "o/red"], payload)
    assert viewer == "me"
    assert [r.name for r in repos] == ["o/ok", "o/missing", "o/red"]
    assert repos[1].error.startswith("Could not resolve")

    ok = repos[0]
    assert ok.checks == "SUCCESS"
    assert ok.release == "v0.8.0"
    assert ok.issue_count == 91
    assert ok.issues[0].author == "ghost"
    assert ok.prs[1].reviewers == ["me"]


def test_parse_response_raises_without_data():
    with pytest.raises(github.GhError, match="Bad credentials"):
        github.parse_response(["o/a"], {"errors": [{"message": "Bad credentials"}]})


def test_needs_attention(payload):
    _, (ok, missing, red) = github.parse_response(
        ["o/ok", "o/missing", "o/red"], payload
    )
    assert ok.needs_attention("me")  # a PR awaits the viewer's review
    assert not ok.needs_attention("someone-else")
    assert missing.needs_attention("me")
    assert red.needs_attention("someone-else")

    ok.prs = []
    assert not ok.needs_attention("me")


def test_needs_attention_for_viewers_failing_pr():
    pr = github.parse_pr(pr_node(3, author="me", checks="FAILURE"))
    repo = github.Repo(name="o/r", checks="SUCCESS", prs=[pr])
    assert repo.needs_attention("me")
    assert not repo.needs_attention("other")


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """Put a 'gh' on PATH that records its stdin and prints a canned response."""

    def install(stdout: str, stderr: str = "", code: int = 0):
        (tmp_path / "out").write_text(stdout)
        (tmp_path / "err").write_text(stderr)
        script = tmp_path / "gh"
        script.write_text(
            "#!/bin/sh\n"
            f'cat >> "{tmp_path}/requests"\n'
            f'echo >> "{tmp_path}/requests"\n'
            f'cat "{tmp_path}/out"\n'
            f'cat "{tmp_path}/err" >&2\n'
            f"exit {code}\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
        return tmp_path / "requests"

    return install


async def test_graphql_reads_data_despite_nonzero_exit(fake_gh, payload):
    requests = fake_gh(json.dumps(payload), "gh: Could not resolve", code=1)
    result = await github.graphql("query { viewer { login } }", {"a": "b"})
    assert result == payload
    sent = json.loads(requests.read_text())
    assert sent == {"query": "query { viewer { login } }", "variables": {"a": "b"}}


async def test_graphql_raises_stderr_when_output_is_not_json(fake_gh):
    fake_gh("", "gh: To get started with GitHub CLI, please run:  gh auth login", 4)
    with pytest.raises(github.GhError, match="gh auth login"):
        await github.graphql("query {}", {})


async def test_graphql_without_gh(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(github.GhError, match="not installed"):
        await github.graphql("query {}", {})


async def test_fetch_chunks_and_expands_owners(monkeypatch):
    calls = []

    async def graphql(query, variables):
        calls.append(variables)
        if "login" in variables:
            return {
                "data": {
                    "repositoryOwner": {
                        "repositories": {
                            "nodes": [
                                {"nameWithOwner": "org/x"},
                                {"nameWithOwner": "a/1"},
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        names = [
            f"{variables[f'o{i}']}/{variables[f'n{i}']}"
            for i in range(len(variables) // 2)
        ]
        data = {f"r{i}": repo_node(n) for i, n in enumerate(names)}
        data["viewer"] = {"login": "me"}
        return {"data": data}

    monkeypatch.setattr(github, "graphql", graphql)
    monkeypatch.setattr(github, "CHUNK_SIZE", 2)

    snap = await github.fetch(["a/1", "a/2", "a/3"], ["org"])
    assert snap.viewer == "me"
    assert [r.name for r in snap.repos] == ["a/1", "a/2", "a/3", "org/x"]
    # One owner listing, and two chunks for the four distinct repositories
    assert len(calls) == 3


async def test_fetch_marks_a_failed_chunk_without_failing_the_rest(monkeypatch):
    async def graphql(query, variables):
        if variables["o0"] == "bad":
            raise github.GhError("HTTP 502")
        return {"data": {"viewer": {"login": "me"}, "r0": repo_node("good/r")}}

    monkeypatch.setattr(github, "graphql", graphql)
    monkeypatch.setattr(github, "CHUNK_SIZE", 1)

    snap = await github.fetch(["bad/r", "good/r"], [])
    assert snap.repos[0].error == "HTTP 502"
    assert snap.repos[1].error is None
    assert snap.viewer == "me"


async def test_fetch_caps_concurrent_queries(monkeypatch):
    in_flight = 0
    peak = 0

    async def graphql(query, variables):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return {"data": {"viewer": {"login": "me"}, "r0": repo_node("o/r")}}

    monkeypatch.setattr(github, "graphql", graphql)
    monkeypatch.setattr(github, "CHUNK_SIZE", 1)
    monkeypatch.setattr(github, "MAX_CONCURRENT", 3)

    snap = await github.fetch([f"o/r{i}" for i in range(10)], [])
    assert len(snap.repos) == 10
    assert peak == 3
