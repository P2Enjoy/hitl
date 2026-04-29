"""Docker Compose management for the HITL stack."""

from __future__ import annotations

import importlib.resources
import shutil
import subprocess
import sys
from pathlib import Path


def _compose_file() -> Path:
    """Return path to the bundled docker-compose.yml."""
    with importlib.resources.path("hitl.data", "docker-compose.yml") as p:
        return Path(p)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def start(detach: bool = True) -> int:
    if not _docker_available():
        print("Error: docker is not installed or not in PATH.", file=sys.stderr)
        return 1

    compose_file = _compose_file()
    cmd = ["docker", "compose", "-f", str(compose_file), "up"]
    if detach:
        cmd.append("-d")
    return subprocess.call(cmd)


def stop() -> int:
    if not _docker_available():
        print("Error: docker is not installed or not in PATH.", file=sys.stderr)
        return 1

    compose_file = _compose_file()
    return subprocess.call(["docker", "compose", "-f", str(compose_file), "down"])


def status() -> int:
    if not _docker_available():
        print("Error: docker is not installed or not in PATH.", file=sys.stderr)
        return 1

    compose_file = _compose_file()
    return subprocess.call(["docker", "compose", "-f", str(compose_file), "ps"])


def logs(service: str | None = None) -> int:
    if not _docker_available():
        print("Error: docker is not installed or not in PATH.", file=sys.stderr)
        return 1

    compose_file = _compose_file()
    cmd = ["docker", "compose", "-f", str(compose_file), "logs", "--tail=50"]
    if service:
        cmd.append(service)
    return subprocess.call(cmd)
