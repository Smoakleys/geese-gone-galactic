# ops/ — autonomous-operation controls

The harness is designed to run unattended. This directory holds the controls that make
"do not stop" a **structural** property instead of a prose instruction the model can
rationalize away (which is exactly how it failed once).

## Two enforcement layers

1. **Stop hook** (`.claude/hooks/keep_going.py`, wired in `.claude/settings.json`).
   Fires when the agent tries to end its turn. In autonomous mode it returns
   `decision=block` with a resume instruction, forcing the next turn. The *harness*
   runs this, not the model — so the model cannot choose to stop.

2. **External driver** (`autopilot_driver.ps1`). Keeps the *process* alive: relaunches
   the CLI if it crashes or exits. The hook drives turns; the driver drives processes.

## Sentinels (both gitignored — never committed, never in a clone)

| File | Meaning |
|------|---------|
| `ops/AUTOPILOT_ON` | Present ⇒ enforced autonomous mode. **Absent by default**, so ordinary interactive sessions are not trapped. Created by the driver or the resume prompt. |
| `ops/STOP` | The **kill switch**. Present ⇒ autonomous mode ends immediately, even if `AUTOPILOT_ON` still exists. |

## Operating it

Start autonomous mode (survives process death):
```
pwsh ops/autopilot_driver.ps1
```
Or, in a normal interactive session, tell the agent to create `ops/AUTOPILOT_ON` and the
Stop hook will drive that session.

**Stop everything (reclaim control):**
```
New-Item -ItemType File ops/STOP      # PowerShell
touch ops/STOP                        # bash
```
Then delete `ops/STOP` and `ops/AUTOPILOT_ON` when you next want a clean interactive session.

## Cost note
Autonomous mode intentionally keeps working turn after turn — that consumes tokens/budget
continuously by design. The kill switch is the single, reliable way to stop it.

See `ops/backlog.md` for the current increment queue and `docs/HANDOFF.md` for full state.
