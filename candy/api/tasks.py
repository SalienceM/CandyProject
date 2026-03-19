from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from candy.models.db import Task, Repo, get_session
from candy.workers.candy_writer import append_progress, append_tracelog, read_progress, read_tracelog

router = APIRouter(prefix="/tasks", tags=["tasks"])


class ProgressWrite(BaseModel):
    content: str
    author_name: str
    author_email: str


@router.get("/")
def list_tasks(repo_id: int | None = None, status: str | None = None, session: Session = Depends(get_session)):
    q = select(Task)
    if repo_id is not None:
        q = q.where(Task.repo_id == repo_id)
    if status:
        q = q.where(Task.status == status)
    return session.exec(q).all()


@router.get("/{task_db_id}")
def get_task(task_db_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_db_id}/progress")
def get_progress(task_db_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    repo = session.get(Repo, task.repo_id)
    content = read_progress(repo, task.task_id)
    return {"task_id": task.task_id, "content": content}


@router.post("/{task_db_id}/progress")
def write_progress(task_db_id: int, body: ProgressWrite, session: Session = Depends(get_session)):
    task = session.get(Task, task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    repo = session.get(Repo, task.repo_id)
    sha = append_progress(repo, task.task_id, body.content, body.author_name, body.author_email)
    return {"status": "ok", "sha": sha}


@router.get("/{task_db_id}/tracelog")
def get_tracelog(task_db_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    repo = session.get(Repo, task.repo_id)
    content = read_tracelog(repo, task.task_id)
    return {"task_id": task.task_id, "content": content}


@router.post("/{task_db_id}/tracelog")
def write_tracelog(task_db_id: int, body: ProgressWrite, session: Session = Depends(get_session)):
    task = session.get(Task, task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    repo = session.get(Repo, task.repo_id)
    sha = append_tracelog(repo, task.task_id, body.content, body.author_name, body.author_email)
    return {"status": "ok", "sha": sha}
