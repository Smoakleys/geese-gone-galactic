# Operations — running the harness unattended

The harness is designed to run without a babysitter. You can intervene, but you never have to.

## One command

```bash
pip install -r requirements.txt
python scripts/run_onepond_autopilot.py            # throwaway sandbox
python scripts/run_onepond_autopilot.py --workdir .autopilot --serve --port 8787
```

`run_onepond_autopilot.py` builds the certified registry (harness + One Pond game checks),
stands up the Gatekeeper + durable run store, and drives the One Pond ticket set through the
strict loop with `AutonomousRunner`. It prints a summary (accepted / autonomy rate / blocked)
and, with `--serve`, starts the read-only control dashboard.

With `--workdir` the workspace persists: accepted artifacts land in `<workdir>/game/accepted/`
as real Gatekeeper-authored git commits, and run state in `<workdir>/.harness/state.json`.

## Intervening (optional)

The dashboard (`--serve`) exposes:

- `GET /` — status page with **Start / Stop / Pause** buttons
- `GET /heartbeat` — JSON liveness (poll from a phone)
- `GET /api/state` — full snapshot (autonomy rate, accepted, blocked, records)
- `POST /control/{start,pause,stop}` — flip the control mode

The runner reads the control mode between tickets: **Pause** stops it cleanly (queue intact,
resumable), **Stop** halts until an explicit **Start**. That is the entire intervention surface
— one lever, nothing else shared.

## Why it never needs you

- **Escape hatch, not a prompt.** When a ticket plateaus, the runner auto-escalates to the
  escape-hatch builder for one more attempt. If that also fails, the ticket is marked `blocked`
  and the runner moves on. It never stops to ask a human.
- **The gate is structural.** Commit authority lives only in `harness/gatekeeper.py`; the
  builder has no commit path. Bad work cannot be self-approved, so unattended running is safe.
- **Everything is durable.** Progress is real git commits + JSON state on disk, and (for this
  project) merged PRs on GitHub — visible from anywhere without any live connection.

## Going to production (drop-ins behind existing seams)

- **Real reviewer:** swap `_reviewer()` in the entrypoint for
  `LLMReviewer(AnthropicChatClient())` (needs `ANTHROPIC_API_KEY`), or a `ConsensusReviewer`
  over several models.
- **Real Icarus:** back `LLMBuilder` with a local-model/API `GenerationClient` instead of the
  scripted One Pond client.
- **Real 3D + renders:** swap `RemoteGpuWorker` (`harness/gen3d`) and `GodotXvfbWorker`
  (`game/onepond/render.py`) in when a GPU host / Godot+Xvfb are available.
