"""A thin, read-only control dashboard on the Python stdlib http server.

Off the critical path by construction: it only reads the ``RunStore`` for display and writes
exactly one thing — the control ``mode`` — via Start/Stop/Pause. No harness internals are
importable from here, so the dashboard can never wedge or bypass the gate; the worst a bug
here can do is show a stale number.

Stdlib rather than FastAPI/uvicorn on purpose: the standing order is "keep running unattended,"
and every extra dependency is one more thing that can fail to import at 3am. Endpoints:

* ``GET  /``               — HTML status page with Start/Stop/Pause buttons
* ``GET  /heartbeat``      — JSON liveness (age in seconds) for a phone to poll
* ``GET  /api/state``      — full JSON snapshot
* ``POST /control/{start,pause,stop}`` — flip the mode, then redirect back to ``/``
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlsplit

from control.store import ControlMode, RunStore


_LOGIN_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>GGG control — unlock</title>
<style>body{font-family:system-ui,sans-serif;margin:3rem;max-width:420px}
input,button{font-size:1.1rem;padding:.6rem;width:100%;box-sizing:border-box;margin:.3rem 0}</style>
</head><body><h1>GGG control</h1><p>Enter the access token.</p>
<form method="get" action="/"><input name="token" type="password" placeholder="access token" autofocus>
<button>Unlock</button></form></body></html>"""


def render_html(store: RunStore) -> str:
    snap = store.snapshot()
    age = snap["heartbeat_age"]
    age_str = "never" if age is None else f"{age:.0f}s ago"
    rows = "".join(
        f"<tr><td>{r.ticket_id}</td><td>{r.final_state}</td>"
        f"<td>{'yes' if r.committed else 'no'}</td><td>{r.rounds}</td>"
        f"<td>{'escape' if r.escape_hatch else 'icarus'}</td></tr>"
        for r in reversed(store.records()[-20:])
    ) or "<tr><td colspan=5><em>no runs yet</em></td></tr>"
    blocked = ", ".join(snap["blocked"]) or "none"
    audit = snap.get("audit", {"blocked": False, "summary": "", "count": 0})
    audit_str = ("no audit yet" if not audit.get("count") else
                 ("BLOCKED — " + audit.get("summary", "") if audit.get("blocked")
                  else f"clean (x{audit.get('count')})"))
    floors = snap.get("floors", {})
    floor_rows = "".join(
        f"<tr><td><code>{k}</code></td><td>{v:g}</td></tr>"
        for k, v in sorted(floors.items())
    ) or "<tr><td colspan=2><em>no floors minted yet</em></td></tr>"
    status = snap.get("status", {})
    st_activity = status.get("activity", "(idle — no live session status yet)")
    st_bits = []
    if status.get("tests"):
        st_bits.append(f"{status['tests']} tests")
    if status.get("last_change"):
        st_bits.append(f"last change: {status['last_change']}")
    if status.get("updated"):
        st_bits.append(f"updated {status['updated']}")
    st_detail = "  |  ".join(st_bits)
    proposals = snap.get("stage_c_proposals", [])
    prop_rows = "".join(
        f"<tr><td>{p.get('kind','')}</td><td><code>{p.get('suggested_check_id','')}</code></td>"
        f"<td>{p.get('occurrences','')}</td><td>{p.get('signature','')}</td></tr>"
        for p in proposals
    ) or "<tr><td colspan=4><em>none — no recurring subjective defect above threshold</em></td></tr>"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GGG harness — control</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:2rem;max-width:820px}}
 .mode{{font-weight:700}} table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 td,th{{border:1px solid #ccc;padding:.35rem .6rem;text-align:left;font-size:.9rem}}
 form{{display:inline}} button{{padding:.5rem 1rem;margin-right:.4rem;cursor:pointer}}
 .kpi{{display:flex;gap:2rem;margin:1rem 0}} .kpi div{{font-size:1.4rem}}
 small{{color:#666}}
 .live{{background:#f3f7f3;border:1px solid #cdd;border-radius:8px;padding:.8rem 1rem;margin:1rem 0}}
 .live .act{{font-size:1.15rem;font-weight:600}}
</style></head><body>
<h1>Geese Gone Galactic — harness control</h1>
<div class="live"><div class="act">{st_activity}</div><small>{st_detail}</small></div>
<p>Mode: <span class="mode">{snap['mode']}</span> &nbsp; Heartbeat: {age_str}</p>
<div class="kpi">
 <div>{snap['autonomy_rate']*100:.0f}%<br><small>autonomy rate</small></div>
 <div>{snap['accepted']}<br><small>accepted</small></div>
 <div>{snap['total_records']}<br><small>runs</small></div>
 <div>{len(proposals)}<br><small>stage-C proposals</small></div>
 <div>{len(floors)}<br><small>ratchet floors</small></div>
</div>
<p>Blocked tickets: {blocked}</p>
<p>Cold audit: {audit_str}</p>
<form method="post" action="/control/start"><button>Start</button></form>
<form method="post" action="/control/pause"><button>Pause</button></form>
<form method="post" action="/control/stop"><button>Stop</button></form>
<table><thead><tr><th>ticket</th><th>final state</th><th>committed</th>
<th>rounds</th><th>builder</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Stage C — taste&rarr;gate proposals</h2>
<p><small>recurring subjective defects Stage C suggests turning into deterministic checks</small></p>
<table><thead><tr><th>kind</th><th>check</th><th>occurrences</th><th>defect signature</th></tr></thead>
<tbody>{prop_rows}</tbody></table>
<h2>Ratchet floors — quality can never regress below these</h2>
<table><thead><tr><th>metric</th><th>floor</th></tr></thead><tbody>{floor_rows}</tbody></table>
<p><small>read-only view; the only mutation is Start/Stop/Pause. Poll /heartbeat for liveness.</small></p>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    store: RunStore = None  # type: ignore[assignment]  # injected by make_server
    token: Optional[str] = None  # None => auth disabled (localhost dev / tests); set => required
    sentinel_dir: Optional[Path] = None  # if set, Start/Stop also manage ops/STOP + AUTOPILOT_ON

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8",
              extra_headers: Optional[list[tuple[str, str]]] = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def _authed(self, query: dict) -> bool:
        """Token gate. Open when no token is configured; else needs the cookie or ``?token=``."""
        if self.token is None:
            return True
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        if "ggg_token" in cookie and cookie["ggg_token"].value == self.token:
            return True
        return query.get("token", [None])[0] == self.token

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        if not self._authed(query):
            self._send(401, _LOGIN_PAGE)
            return
        # Authenticated via ?token= (first unlock): plant an httponly cookie, then redirect to a
        # clean URL so the token never lingers in the address bar / history.
        if self.token is not None and query.get("token"):
            c = SimpleCookie(); c["ggg_token"] = self.token
            c["ggg_token"]["path"] = "/"; c["ggg_token"]["httponly"] = True; c["ggg_token"]["samesite"] = "Lax"
            self.send_response(303)
            self.send_header("Set-Cookie", c["ggg_token"].OutputString())
            self.send_header("Location", path or "/")
            self.end_headers()
            return

        if path in ("/", "/index.html"):
            self._send(200, render_html(self.store))
        elif path == "/heartbeat":
            snap = self.store.snapshot()
            self._send(200, json.dumps({
                "mode": snap["mode"], "heartbeat_age": snap["heartbeat_age"],
                "autonomy_rate": snap["autonomy_rate"], "accepted": snap["accepted"],
            }), "application/json")
        elif path == "/api/state":
            self._send(200, json.dumps(self.store.snapshot()), "application/json")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        if not self._authed(query):
            self._send(401, "unauthorized", "text/plain")
            return
        actions = {
            "/control/start": ControlMode.RUNNING,
            "/control/pause": ControlMode.PAUSED,
            "/control/stop": ControlMode.STOPPED,
        }
        if path in actions:
            self.store.set_mode(actions[path])
            self._apply_sentinels(path)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self._send(404, "not found", "text/plain")

    def _apply_sentinels(self, path: str) -> None:
        """Make Start/Stop also govern the autonomous Claude loop, not just the runner.

        The runner reads ``store.mode``; the Claude autopilot loop reads the ``ops/STOP`` /
        ``AUTOPILOT_ON`` sentinels. When a sentinel dir is wired, remote **Stop** creates STOP
        (halting the loop at its next safe boundary) and **Start** clears it + arms AUTOPILOT_ON,
        so one button governs the whole system. Pause is runner-only (resumable, loop keeps its
        heartbeat)."""
        d = self.sentinel_dir
        if d is None:
            return
        stop, autopilot = d / "STOP", d / "AUTOPILOT_ON"
        if path == "/control/stop":
            stop.write_text("stopped via remote control\n")
        elif path == "/control/start":
            stop.unlink(missing_ok=True)
            autopilot.write_text("armed via remote control\n")

    def log_message(self, *args) -> None:  # keep the console quiet in unattended runs
        pass


def make_server(store: RunStore, host: str = "127.0.0.1", port: int = 8787,
                token: Optional[str] = None, sentinel_dir: Optional[Path] = None) -> HTTPServer:
    """Build (but do not start) an HTTP server bound to ``host:port`` serving ``store``.

    ``token`` gates access when set (required for remote exposure); ``None`` leaves it open for
    localhost/tests. ``sentinel_dir`` (when set) lets Start/Stop also manage the ``ops`` autopilot
    sentinels so remote control governs the whole system. ``port=0`` picks a free port (tests)."""
    handler = type("BoundHandler", (_Handler,),
                   {"store": store, "token": token,
                    "sentinel_dir": Path(sentinel_dir) if sentinel_dir else None})
    return HTTPServer((host, port), handler)


def serve(store_path: Path, host: str = "127.0.0.1", port: int = 8787,
          token: Optional[str] = None, sentinel_dir: Optional[Path] = None) -> None:  # pragma: no cover
    """Entry point for running the dashboard against a store file until interrupted."""
    server = make_server(RunStore(Path(store_path)), host, port, token=token, sentinel_dir=sentinel_dir)
    lock = " (token-protected)" if token else ""
    print(f"GGG control dashboard on http://{host}:{server.server_port}/{lock}")
    server.serve_forever()


def main(argv: Optional[list[str]] = None) -> int:  # pragma: no cover - thin CLI wrapper
    import argparse
    import os
    ap = argparse.ArgumentParser(description="Serve the GGG control dashboard.")
    ap.add_argument("--store", required=True, help="path to the RunStore state.json")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--token", default=os.environ.get("GGG_DASHBOARD_TOKEN"),
                    help="access token; also read from $GGG_DASHBOARD_TOKEN. Omit for open localhost.")
    args = ap.parse_args(argv)
    serve(Path(args.store), args.host, args.port, token=args.token)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
