"""Abstract VCS adapter — add new VCS support by subclassing this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Branch:
    name: str
    is_merged: bool = False
    author: Optional[str] = None
    last_commit_at: Optional[datetime] = None


@dataclass
class Commit:
    sha: str
    author: str
    message: str
    committed_at: datetime
    branch: Optional[str] = None


@dataclass
class Tag:
    name: str
    sha: Optional[str] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None


@dataclass
class WorktreeContext:
    """Represents a temporary isolated working area for file submission."""
    session_id: str
    path: str
    branch: str
    repo_url: str
    cleanup_called: bool = False


class BaseVCSAdapter(ABC):
    """
    All VCS adapters must implement this interface.
    All read operations are non-destructive.
    Write operations go through explicit methods to enable conflict checks.
    """

    def __init__(self, repo_url: str, **kwargs):
        self.repo_url = repo_url

    # ── Read operations ────────────────────────────────────────────────────

    @abstractmethod
    def list_branches(self) -> list[Branch]:
        """Return all branches, including merged ones."""
        ...

    @abstractmethod
    def list_commits(self, since: Optional[datetime] = None, branch: Optional[str] = None) -> list[Commit]:
        """Return commits, optionally filtered by time and branch."""
        ...

    @abstractmethod
    def get_tags(self) -> list[Tag]:
        ...

    @abstractmethod
    def list_files(self, path: str = "", branch: Optional[str] = None) -> list[dict]:
        """Return file tree at path. Each item: {name, type('file'|'dir'), path}"""
        ...

    @abstractmethod
    def read_file(self, file_path: str, branch: Optional[str] = None) -> bytes:
        """Read file content at a given branch/revision."""
        ...

    # ── Write operations (for .candy/ metadata only) ───────────────────────

    @abstractmethod
    def append_to_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        """Append content to a file and commit. Returns new commit sha."""
        ...

    # ── Worktree operations (for business file submission) ─────────────────

    @abstractmethod
    def create_worktree(self, session_id: str, branch: str) -> WorktreeContext:
        """Create an isolated working copy for a file-submission session."""
        ...

    @abstractmethod
    def check_conflicts(self, ctx: WorktreeContext) -> list[str]:
        """
        Fetch remote and return list of conflicting files.
        Empty list means safe to commit.
        """
        ...

    @abstractmethod
    def commit_worktree(
        self,
        ctx: WorktreeContext,
        message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        """Commit and push changes in the worktree. Returns commit sha."""
        ...

    @abstractmethod
    def cleanup_worktree(self, ctx: WorktreeContext) -> None:
        """Remove the worktree directory."""
        ...
