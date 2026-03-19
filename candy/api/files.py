"""File submission API — worktree-based, with conflict detection."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from candy.adapters.registry import get_adapter
from candy.models.db import Repo, get_session
from candy.workers import submit_session as ss

router = APIRouter(prefix="/files", tags=["files"])


# ── Browse file tree ──────────────────────────────────────────────────────────

@router.get("/tree")
def browse_tree(repo_id: int, path: str = "", branch: str | None = None, session: Session = Depends(get_session)):
    repo = session.get(Repo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    adapter = get_adapter(repo.vcs_type, repo.url)
    return adapter.list_files(path=path, branch=branch)


# ── Submit session lifecycle ──────────────────────────────────────────────────

class SessionCreate(BaseModel):
    repo_id: int
    branch: str
    author_name: str
    author_email: str


@router.post("/sessions", status_code=201)
def create_submit_session(body: SessionCreate, session: Session = Depends(get_session)):
    repo = session.get(Repo, body.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    s = ss.create_session(repo, body.branch, body.author_name, body.author_email)
    return {"session_id": s.session_id, "worktree_path": s.ctx.path}


@router.get("/sessions/{session_id}/conflicts")
def check_conflicts(session_id: str):
    if not ss.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    conflicts = ss.check_conflicts(session_id)
    return {"conflicts": conflicts, "safe_to_commit": len(conflicts) == 0}


@router.post("/sessions/{session_id}/upload")
async def upload_file(session_id: str, target_path: str, file: UploadFile):
    """Upload a file into the active worktree at target_path."""
    s = ss.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    dest = Path(s.ctx.path) / target_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)
    return {"status": "ok", "path": target_path, "size": len(content)}


class CommitBody(BaseModel):
    message: str


@router.post("/sessions/{session_id}/commit")
def commit_session(session_id: str, body: CommitBody):
    s = ss.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        sha = ss.commit_session(session_id, body.message)
        return {"status": "ok", "sha": sha}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/sessions/{session_id}")
def abort_session(session_id: str):
    ss.abort_session(session_id)
    return {"status": "aborted"}
