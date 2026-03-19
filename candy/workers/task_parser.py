"""Parse task references from VCS metadata (commits, branch names)."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from candy.adapters.registry import get_adapter
from candy.config import settings
from candy.models.db import CommitRecord, Repo, Task, engine

_TASK_RE = re.compile(settings.task_ref_pattern)
_MILESTONE_RE = re.compile(settings.milestone_ref_pattern)


def _infer_status(branch_name: str, is_merged: bool) -> str:
    if is_merged:
        return "merged"
    name = branch_name.lower()
    if any(k in name for k in ("done", "release", "closed")):
        return "done"
    return "in_progress"


def sync_repo(repo: Repo) -> dict:
    """Fetch VCS data and update the cache DB. Returns summary dict."""
    adapter = get_adapter(repo.vcs_type, repo.url)
    since = repo.last_synced_at or (datetime.now(timezone.utc) - timedelta(days=90))

    commits = adapter.list_commits(since=since)
    branches = adapter.list_branches()
    tags = adapter.get_tags()

    new_commits = 0
    new_tasks = 0

    with Session(engine) as session:
        # ── Upsert commits ──────────────────────────────────────────────
        for c in commits:
            existing = session.exec(
                select(CommitRecord).where(
                    CommitRecord.repo_id == repo.id,
                    CommitRecord.sha == c.sha,
                )
            ).first()
            if existing:
                continue
            task_ref = None
            m = _TASK_RE.search(c.message)
            if m:
                task_ref = m.group("id")
            rec = CommitRecord(
                repo_id=repo.id,
                sha=c.sha,
                author=c.author,
                message=c.message,
                committed_at=c.committed_at,
                task_ref=task_ref,
            )
            session.add(rec)
            new_commits += 1

        # ── Upsert tasks from branches ──────────────────────────────────
        for b in branches:
            m = _TASK_RE.search(b.name)
            if not m:
                continue
            task_id = m.group("id")
            existing_task = session.exec(
                select(Task).where(
                    Task.repo_id == repo.id,
                    Task.task_id == task_id,
                )
            ).first()
            status = _infer_status(b.name, b.is_merged)
            if existing_task:
                existing_task.status = status
                existing_task.updated_at = b.last_commit_at
            else:
                title = b.name.split("/")[-1].replace("-", " ").replace("_", " ")
                title = re.sub(r"\[.*?\]", "", title).strip()
                task = Task(
                    repo_id=repo.id,
                    task_id=task_id,
                    title=title or task_id,
                    branch=b.name,
                    status=status,
                    author=b.author,
                    created_at=b.last_commit_at,
                    updated_at=b.last_commit_at,
                )
                session.add(task)
                new_tasks += 1

        # ── Update last_synced_at ───────────────────────────────────────
        db_repo = session.get(Repo, repo.id)
        if db_repo:
            db_repo.last_synced_at = datetime.now(timezone.utc)

        session.commit()

    return {"new_commits": new_commits, "new_tasks": new_tasks, "tags": len(tags)}
