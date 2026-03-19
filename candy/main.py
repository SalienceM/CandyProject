"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from candy.config import settings
from candy.models.db import create_db_and_tables
from candy.api import repos, tasks, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    settings.worktree_base.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_title, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_title}


# Serve built React app in production
_static = Path(__file__).parent.parent / "web" / "dist"
if _static.exists():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
