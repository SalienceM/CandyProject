"""Handles all writes to .candy/ namespace.

Rules:
- .candy/ is ONLY written by this module, never by developers.
- All writes are append-only (progress, tracelog).
- File-level locking prevents concurrent append corruption.
- Each write produces a dedicated micro-commit so history is clean.
"""

from datetime import datetime, timezone
from pathlib import Path

from candy.adapters.registry import get_adapter
from candy.config import settings
from candy.models.db import Repo


def _timestamp_line(author_name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"\n## {now}  @{author_name}\n"


def append_progress(
    repo: Repo,
    task_id: str,
    content: str,
    author_name: str,
    author_email: str,
) -> str:
    """Append a progress entry to .candy/tasks/{task_id}/progress.md"""
    adapter = get_adapter(repo.vcs_type, repo.url)
    file_path = f"{settings.candy_dir}/tasks/{task_id}/progress.md"
    entry = _timestamp_line(author_name) + content.strip() + "\n"
    sha = adapter.append_to_file(
        file_path=file_path,
        content=entry,
        commit_message=f"candy: progress update for {task_id}",
        author_name=author_name,
        author_email=author_email,
    )
    return sha


def append_tracelog(
    repo: Repo,
    task_id: str,
    content: str,
    author_name: str,
    author_email: str,
) -> str:
    """Append a tracelog entry to .candy/tasks/{task_id}/tracelog.md"""
    adapter = get_adapter(repo.vcs_type, repo.url)
    file_path = f"{settings.candy_dir}/tasks/{task_id}/tracelog.md"
    entry = _timestamp_line(author_name) + content.strip() + "\n"
    sha = adapter.append_to_file(
        file_path=file_path,
        content=entry,
        commit_message=f"candy: tracelog for {task_id}",
        author_name=author_name,
        author_email=author_email,
    )
    return sha


def read_progress(repo: Repo, task_id: str) -> str:
    """Read the full progress log for a task."""
    adapter = get_adapter(repo.vcs_type, repo.url)
    file_path = f"{settings.candy_dir}/tasks/{task_id}/progress.md"
    try:
        return adapter.read_file(file_path).decode("utf-8")
    except Exception:
        return ""


def read_tracelog(repo: Repo, task_id: str) -> str:
    """Read the full tracelog for a task."""
    adapter = get_adapter(repo.vcs_type, repo.url)
    file_path = f"{settings.candy_dir}/tasks/{task_id}/tracelog.md"
    try:
        return adapter.read_file(file_path).decode("utf-8")
    except Exception:
        return ""
