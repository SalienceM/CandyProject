"""SVN VCS adapter using subprocess + svn CLI.
SVN's native file-lock support gives us conflict-free binary file editing."""

import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from candy.adapters.base import BaseVCSAdapter, Branch, Commit, Tag, WorktreeContext
from candy.config import settings


def _run(cmd: list[str], cwd: Optional[str] = None) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, cwd=cwd
    )
    return result.stdout


def _parse_svn_date(s: str) -> datetime:
    # e.g. "2026-03-19T10:30:00.000000Z"
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


class SVNAdapter(BaseVCSAdapter):
    def __init__(self, repo_url: str, username: Optional[str] = None, password: Optional[str] = None, **kwargs):
        super().__init__(repo_url, **kwargs)
        self._auth: list[str] = []
        if username:
            self._auth += ["--username", username]
        if password:
            self._auth += ["--password", password, "--no-auth-cache"]

    def _svn(self, *args, cwd: Optional[str] = None) -> str:
        return _run(["svn", *self._auth, *args], cwd=cwd)

    # ── Read ──────────────────────────────────────────────────────────────

    def list_branches(self) -> list[Branch]:
        branches = []
        for path in ("branches", "trunk"):
            try:
                xml_out = self._svn("list", "--xml", f"{self.repo_url}/{path}")
                root = ET.fromstring(xml_out)
                for entry in root.findall(".//entry"):
                    name_el = entry.find("name")
                    date_el = entry.find("commit/date")
                    author_el = entry.find("commit/author")
                    branches.append(Branch(
                        name=f"{path}/{name_el.text}" if name_el is not None else path,
                        author=author_el.text if author_el is not None else None,
                        last_commit_at=_parse_svn_date(date_el.text) if date_el is not None else None,
                    ))
            except subprocess.CalledProcessError:
                pass
        return branches

    def list_commits(
        self, since: Optional[datetime] = None, branch: Optional[str] = None
    ) -> list[Commit]:
        url = f"{self.repo_url}/{branch}" if branch else self.repo_url
        try:
            xml_out = self._svn("log", "--xml", "--limit", "500", url)
        except subprocess.CalledProcessError:
            return []
        root = ET.fromstring(xml_out)
        commits = []
        for entry in root.findall("logentry"):
            date_el = entry.find("date")
            committed_at = _parse_svn_date(date_el.text) if date_el is not None else datetime.utcnow().replace(tzinfo=timezone.utc)
            if since and committed_at < since:
                break
            author_el = entry.find("author")
            msg_el = entry.find("msg")
            commits.append(Commit(
                sha=entry.get("revision", ""),
                author=author_el.text if author_el is not None else "",
                message=msg_el.text.strip() if msg_el is not None and msg_el.text else "",
                committed_at=committed_at,
                branch=branch,
            ))
        return commits

    def get_tags(self) -> list[Tag]:
        tags = []
        try:
            xml_out = self._svn("list", "--xml", f"{self.repo_url}/tags")
            root = ET.fromstring(xml_out)
            for entry in root.findall(".//entry"):
                name_el = entry.find("name")
                date_el = entry.find("commit/date")
                rev = entry.find("commit")
                tags.append(Tag(
                    name=name_el.text if name_el is not None else "",
                    sha=rev.get("revision") if rev is not None else None,
                    created_at=_parse_svn_date(date_el.text) if date_el is not None else None,
                ))
        except subprocess.CalledProcessError:
            pass
        return tags

    def list_files(self, path: str = "", branch: Optional[str] = None) -> list[dict]:
        url = f"{self.repo_url}/{branch or 'trunk'}"
        if path:
            url = f"{url}/{path}"
        try:
            xml_out = self._svn("list", "--xml", url)
            root = ET.fromstring(xml_out)
            result = []
            for entry in root.findall(".//entry"):
                name_el = entry.find("name")
                kind = entry.get("kind", "file")
                if name_el is not None:
                    p = f"{path}/{name_el.text}".lstrip("/")
                    result.append({
                        "name": name_el.text,
                        "type": "dir" if kind == "dir" else "file",
                        "path": p,
                    })
            return result
        except subprocess.CalledProcessError:
            return []

    def read_file(self, file_path: str, branch: Optional[str] = None) -> bytes:
        url = f"{self.repo_url}/{branch or 'trunk'}/{file_path}"
        result = subprocess.run(
            ["svn", *self._auth, "cat", url],
            capture_output=True, check=True
        )
        return result.stdout

    # ── Write (.candy/ metadata) ──────────────────────────────────────────

    def append_to_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        # Use a temporary checkout just for this file
        tmp_dir = settings.worktree_base / f"svn-meta-{os.getpid()}"
        try:
            self._svn("checkout", "--depth", "empty", self.repo_url, str(tmp_dir))
            rel_dir = str(Path(file_path).parent)
            if rel_dir and rel_dir != ".":
                self._svn("update", "--depth", "empty", rel_dir, cwd=str(tmp_dir))
            self._svn("update", file_path, cwd=str(tmp_dir))

            full_path = tmp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            is_new = not full_path.exists()
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)

            if is_new:
                self._svn("add", file_path, cwd=str(tmp_dir))

            out = self._svn("commit", "-m", commit_message, file_path, cwd=str(tmp_dir))
            # Extract revision number
            m = re.search(r"Committed revision (\d+)", out)
            return m.group(1) if m else ""
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Worktree (file submission) ─────────────────────────────────────────

    def create_worktree(self, session_id: str, branch: str) -> WorktreeContext:
        wt_path = settings.worktree_base / f"svn-{session_id}"
        url = f"{self.repo_url}/{branch}"
        self._svn("checkout", url, str(wt_path))
        return WorktreeContext(
            session_id=session_id,
            path=str(wt_path),
            branch=branch,
            repo_url=self.repo_url,
        )

    def check_conflicts(self, ctx: WorktreeContext) -> list[str]:
        try:
            self._svn("update", "--accept", "postpone", cwd=ctx.path)
            xml_out = self._svn("status", "--xml", cwd=ctx.path)
            root = ET.fromstring(xml_out)
            conflicts = []
            for entry in root.findall(".//entry"):
                wc_status = entry.find("wc-status")
                if wc_status is not None and wc_status.get("item") == "conflicted":
                    path_el = entry.get("path")
                    if path_el:
                        conflicts.append(path_el)
            return conflicts
        except subprocess.CalledProcessError:
            return []

    def commit_worktree(
        self,
        ctx: WorktreeContext,
        message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        out = self._svn("commit", "-m", message, cwd=ctx.path)
        m = re.search(r"Committed revision (\d+)", out)
        return m.group(1) if m else ""

    def cleanup_worktree(self, ctx: WorktreeContext) -> None:
        if ctx.cleanup_called:
            return
        ctx.cleanup_called = True
        shutil.rmtree(ctx.path, ignore_errors=True)

    # ── SVN-specific: file locking ────────────────────────────────────────

    def lock_file(self, file_path: str, comment: str = "") -> None:
        url = f"{self.repo_url}/trunk/{file_path}"
        self._svn("lock", "--message", comment or "Locked by CandyProject", url)

    def unlock_file(self, file_path: str) -> None:
        url = f"{self.repo_url}/trunk/{file_path}"
        self._svn("unlock", url)
