from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CANDY_", env_file=".env", extra="ignore")

    app_title: str = "CandyProject"
    debug: bool = False

    # Storage
    database_url: str = "sqlite:///./candy.db"

    # VCS worker
    worktree_base: Path = Path("/tmp/candy-worktrees")
    repo_cache_dir: Path = Path("/var/candy/repo-cache")

    # Scheduler
    vcs_poll_interval_seconds: int = 300  # 5 min

    # Task parsing
    task_ref_pattern: str = r"\[(?P<id>[A-Z]+-\d+)\]"
    milestone_ref_pattern: str = r"\[(?P<id>MILESTONE-[^\]]+)\]"

    # Candy metadata directory inside repo
    candy_dir: str = ".candy"


settings = Settings()
