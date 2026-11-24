# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

import pytest


def pr_node(number, author="alice", checks="SUCCESS", reviewers=(), draft=False):
    return {
        "number": number,
        "title": f"PR {number}",
        "url": f"https://github.com/o/r/pull/{number}",
        "isDraft": draft,
        "updatedAt": "2026-11-24T10:40:44Z",
        "reviewDecision": "REVIEW_REQUIRED",
        "author": {"login": author},
        "reviewRequests": {
            "nodes": [{"requestedReviewer": {"login": r}} for r in reviewers]
            # A team as reviewer has no 'login' in the User fragment.
            + [{"requestedReviewer": {}}]
        },
        "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": checks}}}]},
    }


def repo_node(name, checks="SUCCESS", prs=()):
    return {
        "nameWithOwner": name,
        "url": f"https://github.com/{name}",
        "isArchived": False,
        "pushedAt": "2026-11-24T10:17:41Z",
        "defaultBranchRef": {
            "name": "main",
            "target": {
                "messageHeadline": "docs: a change",
                "statusCheckRollup": {"state": checks} if checks else None,
            },
        },
        "pullRequests": {"totalCount": len(prs), "nodes": list(prs)},
        "issues": {
            "totalCount": 91,
            "nodes": [
                {
                    "number": 841,
                    "title": "bump the pin",
                    "url": f"https://github.com/{name}/issues/841",
                    "updatedAt": "2026-11-24T10:39:49Z",
                    "author": None,
                    "labels": {"nodes": [{"name": "dependencies"}]},
                }
            ],
        },
        "latestRelease": {"tagName": "v0.8.0", "publishedAt": "2026-11-23T17:38:50Z"},
    }


@pytest.fixture
def payload():
    """A response for ["o/ok", "o/missing", "o/red"], where 'o/missing' does
    not resolve, as GitHub returns it: data for the rest, plus an error."""

    return {
        "data": {
            "viewer": {"login": "me"},
            "r0": repo_node("o/ok", prs=[pr_node(1), pr_node(2, reviewers=["me"])]),
            "r1": None,
            "r2": repo_node("o/red", checks="FAILURE"),
        },
        "errors": [
            {
                "type": "NOT_FOUND",
                "path": ["r1"],
                "message": "Could not resolve to a Repository with the name 'o/missing'.",
            }
        ],
    }
