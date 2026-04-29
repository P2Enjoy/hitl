"""Install the native messaging host for the HITL browser extension."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path


MANIFESTS_DIR = Path(__file__).parent.parent / "data" / "signing-host"

_CHROME_PATHS: dict[str, str] = {
    "linux": str(
        Path.home() / ".config/google-chrome/NativeMessagingHosts/com.hitl.signer.json"
    ),
    "darwin": str(
        Path.home()
        / "Library/Application Support/Google/Chrome/NativeMessagingHosts/com.hitl.signer.json"
    ),
}

_FIREFOX_PATHS: dict[str, str] = {
    "linux": str(
        Path.home() / ".mozilla/native-messaging-hosts/com.hitl.signer.json"
    ),
    "darwin": str(
        Path.home()
        / "Library/Application Support/Mozilla/NativeMessagingHosts/com.hitl.signer.json"
    ),
}


def _find_host_script() -> Path | None:
    """Find the signing-host index.js in common locations."""
    candidates = [
        Path.cwd() / "extension" / "src" / "signing-host" / "index.js",
        Path.home() / ".hitl" / "signing-host" / "index.js",
        Path("/usr/local/lib/hitl/signing-host/index.js"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _write_manifest(dest: Path, host_path: Path, browser: str) -> None:
    if browser == "firefox":
        manifest = {
            "name": "com.hitl.signer",
            "description": "HITL signing host",
            "path": str(host_path),
            "type": "stdio",
            "allowed_extensions": ["hitl-signer@hitl.dev"],
        }
    else:
        extension_id = os.environ.get("EXTENSION_ID", "")
        manifest = {
            "name": "com.hitl.signer",
            "description": "HITL signing host",
            "path": str(host_path),
            "type": "stdio",
            "allowed_origins": [
                f"chrome-extension://{extension_id}/" if extension_id
                else "chrome-extension://YOUR_EXTENSION_ID/"
            ],
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  Wrote {dest}")


def install(browser: str = "chrome", host_script: Path | None = None) -> int:
    plat = platform.system().lower()
    if plat not in ("linux", "darwin"):
        print(f"Error: platform '{plat}' not supported for automatic host install.", file=sys.stderr)
        print("See extension/src/signing-host/install.js for manual instructions.", file=sys.stderr)
        return 1

    if host_script is None:
        host_script = _find_host_script()
        if host_script is None:
            print(
                "Error: cannot find signing-host/index.js. "
                "Build the extension first (cd extension && npm run build) "
                "or set EXTENSION_HOST_SCRIPT.",
                file=sys.stderr,
            )
            return 1

    if not shutil.which("node"):
        print("Error: node is required to run the signing host.", file=sys.stderr)
        return 1

    paths = _FIREFOX_PATHS if browser == "firefox" else _CHROME_PATHS
    dest_str = paths.get(plat)
    if not dest_str:
        print(f"Error: no manifest path known for {browser} on {plat}.", file=sys.stderr)
        return 1

    dest = Path(dest_str)

    wrapper = Path.home() / ".local" / "bin" / "hitl-signing-host"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(f'#!/usr/bin/env bash\nexec node "{host_script}" "$@"\n')
    wrapper.chmod(0o755)
    print(f"  Wrote wrapper: {wrapper}")

    _write_manifest(dest, wrapper, browser)
    return 0
