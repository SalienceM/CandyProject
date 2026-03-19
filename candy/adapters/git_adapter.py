"""Git VCS adapter using GitPython."""

import asyncio
import fcntl
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import git
from git import Repo as GitRepo, InvalidGitRepositoryError

from candy.adapters.base import BaseVCSAdapter, Branch, Commit, Tag, WorktreeContext
from candy.config import settings


def _dt(ts) -> datetime:
    """Convert git timestamp to UTC datetime."""
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


class GitAdapter(BaseVCSAdapter):
    def __init__(self, repo_url: str, **kwargs):
        super().__init__(repo_url, **kwargs)
        try:
            self._repo = GitRepo(repo_url)
        except InvalidGitRepositoryError as e:
            raise ValueError(f"Not a valid git repository: {repo_url}") from e

    # ── Read ──────────────────────────────────────────────────────────────

    def list_branches(self) -> list[Branch]:
        results = []
        merged_names = {
            b.name
            for b in self._repo.git.branch("--merged", "HEAD").splitlines()
            if b.strip()
        } if self._repo.heads else set()

        for ref in self._repo.references:
            if not hasattr(ref, "commit"):
                continue
            if str(ref).startswith("origin/HEAD"):
                continue
            name = ref.name
            commit = ref.commit
            results.append(Branch(
                name=name,
                is_merged=name in merged_names,
                author=str(commit.author),
                last_commit_at=_dt(commit.committed_date),
            ))
        return results

    def list_commits(
        self, since: Optional[datetime] = None, branch: Optional[str] = None
    ) -> list[Commit]:
        kwargs: dict = {"max_count": 500}
        if branch:
            ref = branch
        else:
            ref = self._repo.active_branch.name if self._repo.heads else "HEAD"

        commits = []
        try:
            for c in self._repo.iter_commits(ref, **kwargs):
                committed_at = _dt(c.committed_date)
                if since and committed_at < since:
                    break
                commits.append(Commit(
                    sha=c.hexsha,
                    author=str(c.author),
                    message=c.message.strip(),
                    committed_at=committed_at,
                    branch=branch,
                ))
        except git.GitCommandError:
            pass
        return commits

    def get_tags(self) -> list[Tag]:
        tags = []
        for t in self._repo.tags:
            tags.append(Tag(
                name=t.name,
                sha=t.commit.hexsha,
                created_at=_dt(t.commit.committed_date),
                message=t.tag.message if hasattr(t, "tag") and t.tag else None,
            ))
        return tags

    def list_files(self, path: str = "", branch: Optional[str] = None) -> list[dict]:
        try:
            ref = branch or (self._repo.active_branch.name if self._repo.heads else "HEAD")
            tree = self._repo.commit(ref).tree
            if path:
                for part in Path(path).parts:
                    tree = tree[part]
            result = []
            for item in tree:
                result.append({
                    "name": item.name,
                    "type": "dir" if item.type == "tree" else "file",
                    "path": item.path,
                })
            return result
        except (KeyError, git.GitCommandError):
            return []

    def read_file(self, file_path: str, branch: Optional[str] = None) -> bytes:
        ref = branch or (self._repo.active_branch.name if self._repo.heads else "HEAD")
        blob = self._repo.commit(ref).tree / file_path
        return blob.data_stream.read()

    # ── Write (.candy/ metadata) ──────────────────────────────────────────

    def append_to_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        full_path = Path(self._repo.working_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # File-level lock to serialize concurrent appends
        lock_path = str(full_path) + ".lock"
        with open(lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(content)
                self._repo.index.add([file_path])
                author = git.Actor(author_name, author_email)
                commit = self._repo.index.commit(
                    commit_message, author=author, committer=author
                )
                # Push if remote exists
                if self._repo.remotes:
                    self._repo.remotes[0].push()
                return commit.hexsha
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
        os.unlink(lock_path)

    # ── Worktree (business file submission) ───────────────────────────────

    def create_worktree(self, session_id: str, branch: str) -> WorktreeContext:
        worktree_path = str(settings.worktree_base / f"candy-{session_id}")
        settings.worktree_base.mkdir(parents=True, exist_ok=True)
        self._repo.git.worktree("add", worktree_path, branch)
        return WorktreeContext(
            session_id=session_id,
            path=worktree_path,
            branch=branch,
            repo_url=self.repo_url,
        )

    def check_conflicts(self, ctx: WorktreeContext) -> list[str]:
        wt_repo = GitRepo(ctx.path)
        if not wt_repo.remotes:
            return []
        # Fetch latest from remote
        wt_repo.remotes[0].fetch()
        remote_ref = f"origin/{ctx.branch}"
        try:
            merge_base = wt_repo.merge_base("HEAD", remote_ref)
            if not merge_base:
                return []
            # Diff between working tree and remote
            diff = wt_repo.index.diff(remote_ref)
            return [d.a_path for d in diff if d.change_type == "M"]
        except git.GitCommandError:
            return []

    def commit_worktree(
        self,
        ctx: WorktreeContext,
        message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        wt_repo = GitRepo(ctx.path)
        wt_repo.git.add(".")
        author = git.Actor(author_name, author_email)
        commit = wt_repo.index.commit(message, author=author, committer=author)
        if wt_repo.remotes:
            wt_repo.remotes[0].push()
        return commit.hexsha

    def cleanup_worktree(self, ctx: WorktreeContext) -> None:
        if ctx.cleanup_called:
            return
        ctx.cleanup_called = True
        try:
            self._repo.git.worktree("remove", "--force", ctx.path)
        except git.GitCommandError:
            shutil.rmtree(ctx.path, ignore_errors=True)
