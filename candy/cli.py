"""Candy CLI — works standalone without the web server."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="candy", help="CandyProject — VCS-native project management")
console = Console()


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
):
    """Start the Candy web server."""
    import uvicorn
    uvicorn.run("candy.main:app", host=host, port=port, reload=reload)


@app.command("task")
def task_list(repo: str = typer.Argument(..., help="Path to git/svn repo")):
    """List tasks extracted from a repo."""
    from candy.adapters.registry import get_adapter
    import re
    from candy.config import settings

    # Auto-detect vcs type
    from pathlib import Path
    vcs_type = "git" if (Path(repo) / ".git").exists() else "svn"

    try:
        adapter = get_adapter(vcs_type, repo)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    branches = adapter.list_branches()
    task_re = re.compile(settings.task_ref_pattern)

    table = Table(title=f"Tasks in {repo}", show_lines=True)
    table.add_column("Task ID", style="cyan")
    table.add_column("Branch")
    table.add_column("Status")
    table.add_column("Author")

    for b in branches:
        m = task_re.search(b.name)
        if not m:
            continue
        status = "merged" if b.is_merged else "in_progress"
        table.add_row(m.group("id"), b.name, status, b.author or "")

    console.print(table)


@app.command("report")
def report(
    repo: str = typer.Argument(...),
    output: str = typer.Option("report.md", "--output", "-o"),
):
    """Generate a Markdown project report from a repo."""
    from pathlib import Path
    from candy.adapters.registry import get_adapter
    import re
    from candy.config import settings
    from datetime import datetime, timezone, timedelta

    vcs_type = "git" if (Path(repo) / ".git").exists() else "svn"
    adapter = get_adapter(vcs_type, repo)

    commits = adapter.list_commits(since=datetime.now(timezone.utc) - timedelta(days=30))
    branches = adapter.list_branches()
    tags = adapter.get_tags()
    task_re = re.compile(settings.task_ref_pattern)

    lines = [
        f"# Project Report — {Path(repo).name}",
        f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
        "## Tasks\n",
    ]
    for b in branches:
        m = task_re.search(b.name)
        if not m:
            continue
        status = "✅ merged" if b.is_merged else "🔄 in progress"
        lines.append(f"- **{m.group('id')}** — `{b.name}` {status}")

    lines += ["\n## Recent Commits (last 30 days)\n"]
    for c in commits[:20]:
        lines.append(f"- `{c.sha[:8]}` {c.committed_at.strftime('%Y-%m-%d')} **{c.author}** {c.message.splitlines()[0]}")

    lines += ["\n## Milestones / Tags\n"]
    for t in tags:
        lines.append(f"- **{t.name}** `{t.sha[:8] if t.sha else ''}` {t.created_at.strftime('%Y-%m-%d') if t.created_at else ''}")

    Path(output).write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Report written to {output}[/green]")


@app.command("rebuild")
def rebuild_db(repo_id: int = typer.Argument(..., help="Repo ID to rebuild cache for")):
    """Rebuild the cache DB from VCS (use after DB loss)."""
    from sqlmodel import Session, select
    from candy.models.db import engine, Repo, create_db_and_tables
    from candy.workers.task_parser import sync_repo

    create_db_and_tables()
    with Session(engine) as session:
        repo = session.get(Repo, repo_id)
        if not repo:
            console.print(f"[red]Repo {repo_id} not found[/red]")
            raise typer.Exit(1)
        summary = sync_repo(repo)
    console.print(f"[green]Rebuilt: {summary}[/green]")


if __name__ == "__main__":
    app()
