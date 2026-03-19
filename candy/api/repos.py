from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from candy.models.db import Repo, get_session
from candy.workers.task_parser import sync_repo

router = APIRouter(prefix="/repos", tags=["repos"])


class RepoCreate(BaseModel):
    name: str
    vcs_type: str   # "git" | "svn"
    url: str
    default_branch: str = "main"


@router.get("/")
def list_repos(session: Session = Depends(get_session)):
    return session.exec(select(Repo)).all()


@router.post("/", status_code=201)
def create_repo(body: RepoCreate, session: Session = Depends(get_session)):
    repo = Repo(**body.model_dump())
    session.add(repo)
    session.commit()
    session.refresh(repo)
    return repo


@router.post("/{repo_id}/sync")
def trigger_sync(repo_id: int, session: Session = Depends(get_session)):
    repo = session.get(Repo, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    summary = sync_repo(repo)
    return {"status": "ok", **summary}
