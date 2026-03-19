"""SQLModel database models — these are the cache layer, not source of truth.
The VCS repo is always the source of truth; this DB can be rebuilt at any time."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from candy.config import settings


# ── Repo ──────────────────────────────────────────────────────────────────────

class Repo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    vcs_type: str  # "git" | "svn"
    url: str       # local path or remote URL
    default_branch: str = "main"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced_at: Optional[datetime] = None


# ── Task ──────────────────────────────────────────────────────────────────────

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_id: int = Field(foreign_key="repo.id", index=True)
    task_id: str = Field(index=True)   # e.g. "TASK-001"
    title: str
    branch: Optional[str] = None
    status: str = "in_progress"        # in_progress | merged | done | archived
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Commit ────────────────────────────────────────────────────────────────────

class CommitRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_id: int = Field(foreign_key="repo.id", index=True)
    sha: str = Field(index=True)
    author: str
    message: str
    committed_at: datetime
    task_ref: Optional[str] = None     # parsed task ID from message


# ── Engine & helpers ──────────────────────────────────────────────────────────

engine = create_engine(settings.database_url, echo=settings.debug)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
