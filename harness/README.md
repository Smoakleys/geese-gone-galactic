# Harness (Phase 0.5 — walking skeleton)

This is the **structural core** of the GGG v3 harness: the strict gate that no builder can
route around. It is deliberately built and proven *before* any real LLM builder, reviewer, or
art pipeline exists (see `docs/PLAN.md`, Phase 0.5). Everything here is stdlib-only Python and
runs with zero LLM/GPU cost.

## The one idea

**Commit authority lives in the `Gatekeeper`, not in any agent.** Builders write only to a
gitignored staging dir and have no commit function. The `Gatekeeper` is the only code path
that promotes staging → the protected tree and runs `git commit`, and it does so only after an
independent reviewer's default-FAIL `Verdict` passes. "The builder can't approve its own work"
is therefore a property of the wiring, not of anyone's discipline.

## Modules

| Module | Role |
|---|---|
| `models.py` | Ticket / Verdict / BuildPacket data model; `criteria_hash` freeze; default-FAIL verdicts |
| `states.py` | State machine; the only edge into `COMMIT_PENDING` is `STAGE_B_PASS` |
| `loop.py` | Drives the iteration; holds **no** commit authority |
| `checks/` | Check contract + fixture-based **certification** + `registry.lock`; Stage A runner |
| `gatekeeper.py` | Sole commit authority; tamper checks; ratchet minting |
| `ratchet.py` | Monotonic quality floors (`floor = max(old, new)`); regression fixtures |
| `review/` | Reviewer contract, stub reviewer, and the isolation **packet builder** |
| `icarus/` | The swappable `Builder` seam + stub builder |
| `selfmod/` | The guard-railed self-modification validator + revert bookkeeping |
| `metrics/` | Autonomy-rate flywheel metric |

## Run the governance suite

```bash
pip install -r requirements.txt      # pytest (+ PyYAML for later phases)
python -m pytest tests/ -q
```

The suite proves, in order: the state graph has a single commit predecessor; a broken check is
refused certification; a bad artifact FAILs and does not commit; a builder's `COMPLETED` claim
does not commit if review fails; a good artifact commits exactly once; empty-evidence "PASS" is
FAIL; post-freeze criteria edits abort as tamper; a reintroduced defect is caught by the
ratchet; self-mod is blocked when it reddens the suite / adds an uncertified check / omits the
changelog / silently lowers a floor; and the Stage-B review packet never sees the decision log.

## What is intentionally still stubbed

`StubBuilder` and `StubReviewer` stand in for Icarus and the clean Opus reviewer. Phase 1
replaces the trivial `non_empty_artifact` check with real code/CV checks; Phase 2 replaces the
stub reviewer with a fresh zero-context Opus reviewer + the visual gate; Phase 3 replaces the
stub builder with a local model behind the same `Builder` seam. Because those are seams, each
is a drop-in behind an already-proven control loop.
