"""Catalog loading, validation, and search."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable, List, Optional

APP_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
INTERFACES = {"cli", "interactive", "curses", "animation", "audio"}


@dataclass(frozen=True)
class App:
    id: str
    title: str
    description: str
    date: str
    path: str
    entrypoint: str
    category: str
    interface: str
    dependencies: tuple = ()
    tags: tuple = ()
    smoke_args: tuple = ()

    @classmethod
    def from_dict(cls, value: dict) -> "App":
        value = dict(value)
        for key in ("dependencies", "tags", "smoke_args"):
            value[key] = tuple(value.get(key, ()))
        return cls(**value)


def repository_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find a source checkout containing both the catalog and app directories."""
    override = __import__("os").environ.get("DAILY_IDEAS_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if (candidate / "src/daily_ideas/apps.json").is_file():
            return candidate
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "src/daily_ideas/apps.json").is_file():
            return candidate
    return None


def load_apps(catalog_path: Optional[Path] = None) -> List[App]:
    if catalog_path:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    else:
        # read_text is available on every supported Python version (3.8+).
        raw = json.loads(resources.read_text("daily_ideas", "apps.json", encoding="utf-8"))
    return [App.from_dict(item) for item in raw["apps"]]


def validate_apps(apps: Iterable[App], root: Optional[Path] = None) -> List[str]:
    errors: List[str] = []
    seen = set()
    for app in apps:
        if app.id in seen:
            errors.append(f"duplicate id: {app.id}")
        seen.add(app.id)
        if not APP_DIR_RE.fullmatch(app.path):
            errors.append(f"{app.id}: invalid directory name {app.path}")
        if app.interface not in INTERFACES:
            errors.append(f"{app.id}: invalid interface {app.interface}")
        if root and not (root / app.path / app.entrypoint).is_file():
            errors.append(f"{app.id}: missing entrypoint {app.path}/{app.entrypoint}")
    return errors


def search(apps: Iterable[App], query: str) -> List[App]:
    terms = query.lower().split()
    return [
        app for app in apps
        if all(term in " ".join((app.id, app.title, app.description, app.category, *app.tags)).lower()
               for term in terms)
    ]
