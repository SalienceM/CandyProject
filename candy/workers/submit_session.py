"""File-submission session manager.

Each session corresponds to one user's "submit files" action.
Uses VCS worktrees (Git) or checkouts (SVN) for full isolation.
Conflict detection happens before any commit is made.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from candy.adapters.base import WorktreeContext
from candy.adapters.registry import get_adapter
from candy.models.db import Repo

# In-memory session store (replaced by Redis in multi-process deployments)
_sessions: dict[str, "SubmitSession"] = {}


@dataclass
class SubmitSession:
    session_id: str
    repo: Repo
    branch: str
    author_name: str
    author_email: str
    ctx: WorktreeContext
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    committed: bool = False


def create_session(
    repo: Repo,
    branch: str,
    author_name: str,
    author_email: str,
) -> SubmitSession:
    session_id = str(uuid.uuid4())
    adapter = get_adapter(repo.vcs_type, repo.url)
    ctx = adapter.create_worktree(session_id, branch)
    session = SubmitSession(
        session_id=session_id,
        repo=repo,
        branch=branch,
        author_name=author_name,
        author_email=author_email,
        ctx=ctx,
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SubmitSession]:
    return _sessions.get(session_id)


def check_conflicts(session_id: str) -> list[str]:
    """Returns list of conflicting file paths. Empty = safe to commit."""
    session = _sessions[session_id]
    adapter = get_adapter(session.repo.vcs_type, session.repo.url)
    return adapter.check_conflicts(session.ctx)


def commit_session(session_id: str, commit_message: str) -> str:
    """Commit and push. Raises RuntimeError if conflicts exist."""
    session = _sessions[session_id]
    conflicts = check_conflicts(session_id)
    if conflicts:
        raise RuntimeError(
            f"Cannot commit: conflicts detected in {conflicts}. "
            "Please download the latest version and re-upload."
        )
    adapter = get_adapter(session.repo.vcs_type, session.repo.url)
    sha = adapter.commit_worktree(
        session.ctx,
        message=commit_message,
        author_name=session.author_name,
        author_email=session.author_email,
    )
    session.committed = True
    _cleanup_session(session_id)
    return sha


def abort_session(session_id: str) -> None:
    """Discard changes and clean up worktree."""
    _cleanup_session(session_id)


def _cleanup_session(session_id: str) -> None:
    session = _sessions.pop(session_id, None)
    if session:
        adapter = get_adapter(session.repo.vcs_type, session.repo.url)
        adapter.cleanup_worktree(session.ctx)
