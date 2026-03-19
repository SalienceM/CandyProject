"""Adapter registry — maps vcs_type string to adapter class."""

from candy.adapters.base import BaseVCSAdapter
from candy.adapters.git_adapter import GitAdapter
from candy.adapters.svn_adapter import SVNAdapter

_REGISTRY: dict[str, type[BaseVCSAdapter]] = {
    "git": GitAdapter,
    "svn": SVNAdapter,
}


def get_adapter(vcs_type: str, repo_url: str, **kwargs) -> BaseVCSAdapter:
    cls = _REGISTRY.get(vcs_type.lower())
    if cls is None:
        raise ValueError(f"Unsupported VCS type: {vcs_type!r}. Available: {list(_REGISTRY)}")
    return cls(repo_url, **kwargs)


def register_adapter(vcs_type: str, cls: type[BaseVCSAdapter]) -> None:
    """Extension point: register a custom VCS adapter at runtime."""
    _REGISTRY[vcs_type.lower()] = cls
