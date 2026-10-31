"""
backend/services/repo_service.py

Handles cloning and updating GitHub repositories into the workspace directory.

Security:
 - Only allows HTTPS github.com URLs (no arbitrary git servers)
 - Sanitises repo name to prevent path traversal
 - Validates clone was successful before returning

If the repo already exists locally it does a `git pull` to refresh it.
"""
from __future__ import annotations

import os
import re
import shutil
from typing import Any

from git import Repo, GitCommandError, InvalidGitRepositoryError

WORKSPACE_DIR = "workspace"
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[\w.\-]+/[\w.\-]+(\.git)?/?$", re.IGNORECASE
)
_SAFE_NAME_RE = re.compile(r"[^\w.\-]")


def _safe_repo_name(repo_url: str) -> str:
    raw = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    return _SAFE_NAME_RE.sub("_", raw)[:80]


def clone_repository(repo_url: str) -> dict[str, Any]:
    """
    Clone *repo_url* into workspace/<repo_name>.

    If the directory already exists, attempt a git pull instead.
    Raises ValueError for disallowed URLs.
    """
    repo_url = repo_url.strip()

    if not _GITHUB_URL_RE.match(repo_url):
        raise ValueError(
            f"Only public HTTPS github.com URLs are supported. Got: {repo_url!r}"
        )

    repo_name = _safe_repo_name(repo_url)
    local_path = os.path.join(WORKSPACE_DIR, repo_name)

    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    # ── Already cloned? pull instead ──────────────────────────────────────
    if os.path.exists(local_path):
        try:
            repo = Repo(local_path)
            origin = repo.remotes.origin
            origin.pull()
            return {
                "message": "Repository updated (git pull)",
                "local_path": local_path,
                "repo_name": repo_name,
                "updated": True,
            }
        except InvalidGitRepositoryError:
            # Corrupt directory — remove and re-clone
            shutil.rmtree(local_path, ignore_errors=True)
        except GitCommandError as exc:
            # Pull failed (e.g. detached HEAD) — return existing clone
            return {
                "message": f"Pull skipped: {exc}",
                "local_path": local_path,
                "repo_name": repo_name,
                "updated": False,
            }

    # ── Fresh clone ───────────────────────────────────────────────────────
    try:
        Repo.clone_from(repo_url, local_path, depth=1)   # shallow clone — faster
    except GitCommandError as exc:
        raise RuntimeError(f"git clone failed: {exc}") from exc

    if not os.path.isdir(local_path):
        raise RuntimeError("Clone reported success but directory was not created.")

    return {
        "message": "Repository cloned successfully",
        "local_path": local_path,
        "repo_name": repo_name,
        "updated": False,
    }