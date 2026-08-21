"""Four-node system topology loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .catalog import repository_root


@dataclass(frozen=True)
class Node:
    id: str
    title: str
    role: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    reference_devices: Tuple[str, ...]


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    contract: str


@dataclass(frozen=True)
class Platform:
    name: str
    version: int
    source_repository: str
    nodes: Tuple[Node, ...]
    links: Tuple[Link, ...]


@dataclass(frozen=True)
class Device:
    id: str
    domain: str
    roles: Tuple[str, ...]


def platform_path(root: Optional[Path] = None) -> Path:
    checkout = root or repository_root()
    if not checkout:
        raise FileNotFoundError("platform manifest requires a source checkout")
    return checkout / "systems" / "platform.json"


def load_platform(path: Optional[Path] = None) -> Platform:
    raw = json.loads((path or platform_path()).read_text(encoding="utf-8"))
    nodes = tuple(Node(
        id=item["id"], title=item["title"], role=item["role"],
        inputs=tuple(item["inputs"]), outputs=tuple(item["outputs"]),
        reference_devices=tuple(item["reference_devices"]),
    ) for item in raw["nodes"])
    links = tuple(Link(item["from"], item["to"], item["contract"]) for item in raw["links"])
    return Platform(raw["name"], raw["version"], raw["source_repository"], nodes, links)


def load_devices(path: Path) -> Tuple[Device, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(Device(item["id"], item["domain"], tuple(item["roles"])) for item in raw["devices"])


def validate_platform(platform: Platform, root: Optional[Path] = None) -> List[str]:
    errors: List[str] = []
    ids = [node.id for node in platform.nodes]
    if len(platform.nodes) != 4:
        errors.append(f"platform must define exactly 4 nodes, found {len(platform.nodes)}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate node id")
    known = set(ids)
    for link in platform.links:
        if link.source not in known or link.target not in known:
            errors.append(f"invalid link: {link.source} -> {link.target}")
    if root:
        device_root = root / "systems" / "soc-devices"
        devices = load_devices(root / "systems" / "devices.json")
        registered = [device.id for device in devices]
        discovered = sorted(path.name for path in device_root.iterdir()
                            if path.is_dir() and (path / "README.md").is_file())
        if len(registered) != len(set(registered)):
            errors.append("duplicate device id in registry")
        missing = sorted(set(discovered) - set(registered))
        extra = sorted(set(registered) - set(discovered))
        if missing:
            errors.append(f"unregistered devices: {', '.join(missing)}")
        if extra:
            errors.append(f"registered devices missing from checkout: {', '.join(extra)}")
        for device in devices:
            unknown_roles = sorted(set(device.roles) - known)
            if not device.roles:
                errors.append(f"{device.id}: no system role")
            if unknown_roles:
                errors.append(f"{device.id}: unknown roles {', '.join(unknown_roles)}")
        for node in platform.nodes:
            for device in node.reference_devices:
                if device not in registered:
                    errors.append(f"{node.id}: missing reference device {device}")
    return errors
