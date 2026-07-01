"""Operator entrypoint: run the One Pond build unattended, then (optionally) serve the dashboard.

This is the "turn it on and walk away" program. It wires the real pieces together — certified
registry (harness + One Pond game checks), the Gatekeeper, the durable run store, and the
AutonomousRunner driving the One Pond ticket set through the strict loop — then prints a
summary and, with ``--serve``, starts the read-only control dashboard (Start/Stop/Pause +
heartbeat).

By default it operates in a throwaway sandbox git repo so a demo run never touches your project
tree. Point ``--workdir`` at a persistent directory to keep the accepted artifacts and run
state across runs.

Offline by default it uses a scripted reviewer (no API cost). In production, pass a real
reviewer: ``LLMReviewer(AnthropicChatClient())`` when ``ANTHROPIC_API_KEY`` is set — a one-line
swap, since the runner only depends on the ``Reviewer`` seam.

Examples:
    python scripts/run_onepond_autopilot.py
    python scripts/run_onepond_autopilot.py --workdir .autopilot --serve --port 8787
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

# Make the repo importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control.runner import AutonomousRunner
from control.store import RunStore
from game.onepond.checks import build_onepond_registry
from game.onepond.tickets import onepond_generation_client, onepond_tickets
from harness.gatekeeper import Gatekeeper
from harness.icarus.llm_builder import LLMBuilder
from harness.review.base import StubReviewer


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "autopilot@ggg.local"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.name", "ggg-autopilot"], cwd=path, check=True)
        (path / "README.md").write_text("One Pond autopilot workspace\n")
        subprocess.run(["git", "add", "-A"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init autopilot workspace"], cwd=path, check=True)
    return path


def _reviewer(render_dir=None):
    """Stage B: the visual gate (mechanical CV floor) wrapping an offline scripted reviewer.

    The scripted reviewer supplies the (here, always-pass) subjective judgement; the visual
    reviewer renders each config and blocks anything that doesn't read as a real pond. Swap the
    scripted inner reviewer for a real Anthropic reviewer in production — the wiring is unchanged.
    """
    from game.onepond.review import OnePondVisualReviewer
    return OnePondVisualReviewer(StubReviewer(lambda rnd: True), render_dir=render_dir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the One Pond build unattended.")
    ap.add_argument("--workdir", default=None,
                    help="persistent workspace (default: a throwaway temp sandbox)")
    ap.add_argument("--serve", action="store_true", help="serve the control dashboard after the run")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args(argv)

    repo = _init_repo(Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="onepond_")))
    harness_dir = repo / ".harness"
    registry = build_onepond_registry(harness_dir / "lock")
    gatekeeper = Gatekeeper(repo, ratchet_dir=harness_dir / "ratchet")
    store = RunStore(harness_dir / "state.json")

    runner = AutonomousRunner(
        store=store, repo_root=repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=_reviewer(render_dir=harness_dir / "renders"),
        icarus_builder=LLMBuilder(onepond_generation_client()),
        staging_root=repo / "run" / "staging",
    )
    for ticket in onepond_tickets():
        runner.submit(ticket)

    print(f"workspace: {repo}")
    print(f"certified checks: {[c.id for c in registry.certified_checks()]}")
    records = runner.run_pending()

    print("\n=== run summary ===")
    for r in records:
        flag = "escape-hatch" if r.escape_hatch else "icarus"
        print(f"  {r.ticket_id:10} committed={r.committed!s:5} rounds={r.rounds} "
              f"builder={flag} state={r.final_state}")
    print(f"\naccepted: {store.metrics()['accepted']}/{len(records)}  "
          f"autonomy_rate: {store.autonomy_rate()*100:.0f}%  "
          f"blocked: {store.blocked() or 'none'}")

    proposals = store.proposals()
    print("\n=== stage C: recurring subjective defects -> proposed checks ===")
    if proposals:
        for p in proposals:
            print(f"  {p['suggested_check_id']:24} x{p['occurrences']}  "
                  f"({p['signature']})")
    else:
        print("  none above threshold")

    if args.serve:
        from control.dashboard import serve
        print(f"\nserving dashboard on http://{args.host}:{args.port}/  (Ctrl-C to stop)")
        serve(store.path, args.host, args.port)

    return 0 if all(r.committed for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
