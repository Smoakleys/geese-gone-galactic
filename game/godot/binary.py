"""Locate the Godot 4 binary — PATH first, else the gitignored ``ops/bin/`` bundle.

Mirrors the ``cloudflared`` pattern (see ``ops/serve_remote.py``). On Windows we prefer the
``*_console.exe`` build: the plain editor exe is a GUI-subsystem binary that does not attach to a
console, so ``--check-only`` / import error output would be lost. The console build attaches, so
subprocess stdout/stderr capture actually contains the parser errors the gate (and Icarus's
self-repair loop) depend on.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[2]
_BIN = _REPO / "ops" / "bin"


def godot_path() -> Optional[str]:
    """Absolute path to a runnable Godot 4 binary, or None if none is found."""
    for name in ("godot", "godot4", "Godot"):
        found = shutil.which(name)
        if found:
            return found
    # Prefer an explicit console build, then any bundled Godot exe.
    if _BIN.exists():
        for pattern in ("*_console.exe", "Godot*win64*.exe", "godot*", "Godot*"):
            hits = sorted(p for p in _BIN.glob(pattern) if p.is_file())
            if hits:
                return str(hits[0])
    return None
