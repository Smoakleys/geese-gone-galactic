"""Play One Pond in the browser — the real art game, clickable.

Ties the whole game together: the `game/pond` logic + the `game/art_view` real-art renderer behind a tiny
stdlib web server. Open the page, click Build Bakery / Granary / Nest / Well / Fence / Tick, and watch your
cozy island grow as painterly art. No dependencies beyond the repo (http.server + Pillow).

    python ops/play_web.py        # then open http://localhost:8770

The game CORE (`GameSession`) is separate from the server so it's unit-tested without a live socket.
"""

from __future__ import annotations

import http.server
import io
import urllib.parse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.pond import add_building, step, goose_count, pond_score, pond_rank, pond_status   # noqa: E402
from game.art_view import compose_pond_art                                                   # noqa: E402

GRID = 8
REACH = 2
_SLOTS = [(x, y) for y in range(GRID) for x in range(GRID)]
KINDS = ("bakery", "granary", "nest", "well", "fence")


class GameSession:
    """One player's pond: mutable state + the actions the web buttons trigger. Renders to a PNG in memory."""

    def __init__(self) -> None:
        self.state: dict = {"bread": 30, "buildings": []}

    def act(self, action: str) -> str:
        """Apply a button action ('build_<kind>' | 'tick'); return a short status message."""
        if action == "tick":
            self.state = step(self.state)
            return f"ticked -> {self.state['bread']} bread"
        if action.startswith("build_"):
            kind = action[len("build_"):]
            if kind not in KINDS:
                return f"unknown building: {kind}"
            for x, y in _SLOTS:                       # first free cell
                nxt = add_building(self.state, kind, x, y, GRID)
                if len(nxt["buildings"]) > len(self.state["buildings"]):
                    self.state = nxt
                    return f"built {kind}"
            return f"no room for {kind}"
        return f"unknown action: {action}"

    def status(self) -> str:
        st = pond_status(self.state, REACH)
        return (f"bread {self.state['bread']} · geese {goose_count(self.state['buildings'])} · "
                f"{pond_rank(pond_score(self.state))} · {'safe' if st['safe'] else 'unsafe'}")

    def render_png(self) -> bytes:
        out = Path(compose_pond_art(self.state, Path(_tmp_png())))
        data = out.read_bytes()
        out.unlink(missing_ok=True)
        return data


def _tmp_png() -> str:
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".png", prefix="webpond_")
    os.close(fd)        # close the descriptor so compose_pond_art can write + we can unlink (Windows locks open files)
    return path


def _page(session: GameSession, msg: str = "") -> bytes:
    import time
    buttons = "".join(
        f'<a class="btn" href="/act?do=build_{k}">Build {k.title()}</a>' for k in KINDS)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>One Pond</title>
<style>
 body{{background:#dce9f2;font-family:system-ui,sans-serif;text-align:center;margin:0;padding:18px}}
 h1{{color:#3a6b4f;margin:6px}} .status{{color:#456;margin:6px 0 12px}}
 img{{max-width:96%;border-radius:16px;box-shadow:0 8px 30px #0003}}
 .bar{{margin:14px auto}}
 .btn{{display:inline-block;margin:4px;padding:9px 15px;background:#7cc06a;color:#fff;border-radius:10px;
   text-decoration:none;font-weight:600;box-shadow:0 3px 0 #5a9a4c}} .btn:hover{{background:#8fce7d}}
 .tick{{background:#e8a54c;box-shadow:0 3px 0 #c6842f}} .msg{{color:#789;font-size:13px;height:16px}}
</style></head><body>
<h1>🪿 One Pond</h1>
<div class="status">{session.status()}</div>
<img src="/pond.png?t={int(time.time()*1000)}" alt="your pond">
<div class="bar">{buttons}<a class="btn tick" href="/act?do=tick">Tick ⏱</a></div>
<div class="msg">{msg}</div>
</body></html>"""
    return html.encode("utf-8")


def make_handler(session: GameSession):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):    # quiet
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/pond.png":
                data = session.render_png()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif parsed.path == "/act":
                q = urllib.parse.parse_qs(parsed.query)
                session.act(q.get("do", [""])[0])
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
            else:
                body = _page(session)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
    return Handler


def main(port: int = 8770) -> None:
    session = GameSession()
    httpd = http.server.HTTPServer(("127.0.0.1", port), make_handler(session))
    print(f"One Pond — open http://localhost:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
