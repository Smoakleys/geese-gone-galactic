"""Serve the GGG control dashboard and expose it remotely via a Cloudflare quick tunnel.

The dashboard runs on this machine (that's where the harness state lives); this wraps it with a
token gate and a Cloudflare tunnel so the Owner can Start/Pause/Stop from a phone browser.

Flow:
1. Resolve an access token (``$GGG_DASHBOARD_TOKEN`` → gitignored ``ops/dashboard_token.local``
   → generate + persist one).
2. Serve the token-gated dashboard on ``127.0.0.1:PORT`` (Start/Stop also drive the ``ops``
   autopilot sentinels, so remote Stop halts the whole autonomous system).
3. If ``cloudflared`` is on PATH, launch a **quick tunnel** (no Cloudflare account needed) and
   surface the printed ``https://<random>.trycloudflare.com`` URL — printed to console and, if
   the email notifier is configured, emailed to the Owner along with the token.
4. If ``cloudflared`` is missing, keep serving locally and print install instructions.

Runs until Ctrl-C. The quick-tunnel URL changes each launch; for a stable URL set up a named
tunnel (see docs/REMOTE_SETUP.md).

    python ops/serve_remote.py --store .autopilot/.harness/state.json --port 8787
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

TOKEN_PATH = _REPO / "ops" / "dashboard_token.local"   # gitignored
_TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def resolve_token() -> str:
    """Env → gitignored file → freshly generated (and persisted). Never empty."""
    import os
    tok = os.environ.get("GGG_DASHBOARD_TOKEN")
    if tok:
        return tok.strip()
    if TOKEN_PATH.exists():
        tok = TOKEN_PATH.read_text().strip()
        if tok:
            return tok
    tok = secrets.token_urlsafe(18)
    TOKEN_PATH.write_text(tok)
    print(f"[serve_remote] generated a new access token -> {TOKEN_PATH}")
    return tok


def extract_tunnel_url(text: str) -> Optional[str]:
    """Pull the https://<sub>.trycloudflare.com URL out of a line of cloudflared output."""
    m = _TUNNEL_RE.search(text)
    return m.group(0) if m else None


def cloudflared_path() -> Optional[str]:
    """Locate cloudflared: PATH first, else the bundled ops/bin/cloudflared[.exe] we download."""
    found = shutil.which("cloudflared")
    if found:
        return found
    for name in ("cloudflared.exe", "cloudflared"):
        local = _REPO / "ops" / "bin" / name
        if local.exists():
            return str(local)
    return None


def _render_showcase_base(out_path: Path) -> Optional[Path]:
    """Render a representative goose base to a PNG so the site shows the game, not just numbers.

    Prefers the biggest accepted pond in the workspace; falls back to the canonical full base.
    Returns the path, or None if rendering isn't available (e.g. no Pillow) — the site then just
    omits the image.
    """
    try:
        import json
        from game.onepond.render import StubScreenshotWorker
        from game.onepond.tickets import POND_CONFIGS

        accepted = _REPO / ".autopilot" / "game" / "accepted"
        configs = list(accepted.glob("*/onepond_config.json")) if accepted.exists() else []
        if configs:
            config = json.loads(max(configs, key=lambda p: p.stat().st_size).read_text())
        else:
            config = POND_CONFIGS["T-POND-06"]  # the full sanctuary, all building types
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return StubScreenshotWorker(tile_px=28, margin=16).render(config, out_path)
    except Exception as e:
        print(f"[serve_remote] (no base image: {e})")
        return None


def _announce(url: str, token: str) -> None:
    """Print the live URL+token and, if the notifier is configured, email it to the Owner."""
    banner = f"Remote control live: {url}   (access token: {token})"
    print("\n" + "=" * len(banner) + f"\n{banner}\n" + "=" * len(banner) + "\n", flush=True)
    try:
        from ops import notify  # optional; only sends if the SMTP config exists
        notify.send_email("GGG control: remote URL",
                          f"Open on your phone:\n  {url}\n\nAccess token:\n  {token}\n")
    except Exception as e:  # notifier problems must never take down the server
        print(f"[serve_remote] (URL not emailed: {e})")


def main(argv: Optional[list[str]] = None) -> int:  # pragma: no cover - orchestration/subprocess
    ap = argparse.ArgumentParser(description="Serve the control dashboard behind a Cloudflare tunnel.")
    ap.add_argument("--store", default=str(_REPO / ".autopilot" / ".harness" / "state.json"),
                    help="RunStore state.json (match the autopilot's --workdir so control is shared)")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-tunnel", action="store_true", help="serve locally only; skip cloudflared")
    args = ap.parse_args(argv)

    from control.dashboard import make_server
    from control.store import RunStore

    token = resolve_token()
    store_path = Path(args.store)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    base_image = _render_showcase_base(store_path.parent.parent / "base.png")
    server = make_server(RunStore(store_path), "127.0.0.1", args.port,
                         token=token, sentinel_dir=_REPO / "ops", base_image=base_image)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[serve_remote] dashboard on http://127.0.0.1:{port}/  (token-protected)")

    cfd = cloudflared_path()
    if args.no_tunnel or cfd is None:
        if not args.no_tunnel:
            print("[serve_remote] cloudflared not found (PATH or ops/bin) — serving locally only.")
            print("  Install it (Windows): winget install --id Cloudflare.cloudflared")
            print("  Then re-run, or see docs/REMOTE_SETUP.md for a stable named tunnel.")
        print(f"[serve_remote] local URL: http://127.0.0.1:{port}/?token={token}")
        _block()
        return 0

    proc = subprocess.Popen(
        [cfd, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    announced = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line.rstrip())
            if not announced:
                url = extract_tunnel_url(line)
                if url:
                    _announce(url, token)
                    announced = True
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        server.shutdown()
    return 0


def _block() -> None:  # pragma: no cover
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
