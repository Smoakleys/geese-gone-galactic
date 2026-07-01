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
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from control.store import ControlMode, RunStore


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
</style></head><body>
<h1>Geese Gone Galactic — harness control</h1>
<p>Mode: <span class="mode">{snap['mode']}</span> &nbsp; Heartbeat: {age_str}</p>
<div class="kpi">
 <div>{snap['autonomy_rate']*100:.0f}%<br><small>autonomy rate</small></div>
 <div>{snap['accepted']}<br><small>accepted</small></div>
 <div>{snap['total_records']}<br><small>runs</small></div>
</div>
<p>Blocked tickets: {blocked}</p>
<form method="post" action="/control/start"><button>Start</button></form>
<form method="post" action="/control/pause"><button>Pause</button></form>
<form method="post" action="/control/stop"><button>Stop</button></form>
<table><thead><tr><th>ticket</th><th>final state</th><th>committed</th>
<th>rounds</th><th>builder</th></tr></thead><tbody>{rows}</tbody></table>
<p><small>read-only view; the only mutation is Start/Stop/Pause. Poll /heartbeat for liveness.</small></p>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    store: RunStore = None  # type: ignore[assignment]  # injected by make_server

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path in ("/", "/index.html"):
            self._send(200, render_html(self.store))
        elif self.path == "/heartbeat":
            snap = self.store.snapshot()
            self._send(200, json.dumps({
                "mode": snap["mode"], "heartbeat_age": snap["heartbeat_age"],
                "autonomy_rate": snap["autonomy_rate"], "accepted": snap["accepted"],
            }), "application/json")
        elif self.path == "/api/state":
            self._send(200, json.dumps(self.store.snapshot()), "application/json")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        actions = {
            "/control/start": ControlMode.RUNNING,
            "/control/pause": ControlMode.PAUSED,
            "/control/stop": ControlMode.STOPPED,
        }
        if self.path in actions:
            self.store.set_mode(actions[self.path])
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *args) -> None:  # keep the console quiet in unattended runs
        pass


def make_server(store: RunStore, host: str = "127.0.0.1", port: int = 8787) -> HTTPServer:
    """Build (but do not start) an HTTP server bound to ``host:port`` serving ``store``.

    Call ``.serve_forever()`` to run it, or ``.handle_request()`` to serve one request. Use
    ``port=0`` to get an ephemeral port (tests do this)."""
    handler = type("BoundHandler", (_Handler,), {"store": store})
    return HTTPServer((host, port), handler)


def serve(store_path: Path, host: str = "127.0.0.1", port: int = 8787) -> None:  # pragma: no cover
    """Entry point for running the dashboard against a store file until interrupted."""
    server = make_server(RunStore(Path(store_path)), host, port)
    print(f"GGG control dashboard on http://{host}:{server.server_port}/")
    server.serve_forever()
