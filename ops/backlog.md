# Autopilot backlog — next increments (highest value first)

The Stop hook points the agent here every turn. Keep it current: when you finish an
increment, tick it and add the next. This is guidance, not the stop condition — the
ONLY stop condition is the `ops/STOP` kill switch (or Bridger saying stop).

## Now
- [ ] **Turn Stage C in the live pipeline** — `harness/review/decision_log_review.py`
      (`DecisionLogReview` / `load_defect_records`) is only used in tests; it is NOT
      invoked by `control/runner.py` or `scripts/run_onepond_autopilot.py`. Wire it in:
      after `run_pending`, harvest builder decision logs from the STAGING trees (the
      logs are in `FORBIDDEN_ARTIFACT_NAMES`, so never in `game/accepted`), run
      `analyze`, and surface `ProposedAdjustment`s in the run summary + `RunStore`
      snapshot (new field, don't break the existing shape). Test: a recurring defect
      (>= threshold) yields a proposal end-to-end through the runner.
- [ ] **Close one full flywheel turn** — take a proposal Stage C surfaces and author the
      deterministic check it suggests (with good/bad fixtures + certification), proving a
      subjective Stage-B defect became a mechanical Stage-A gate.

## Candidate increments (pick by value, not order)
- [ ] Extend One Pond through the harness: a 4th mechanic, more tickets, a new
      harvested check. Drive to acceptance at autonomy 1.0.
- [ ] Quality hardening: hunt real correctness bugs across `harness/`, `control/`,
      `game/`; fix with tests (high-confidence work only).
- [ ] External drop-ins IF hardware/keys appear: real Godot+Xvfb (`GodotXvfbWorker`),
      GPU text-to-3D worker (`harness/gen3d`), live `AnthropicChatClient`
      (`ANTHROPIC_API_KEY`). Each is a drop-in behind an existing tested seam.

## Done this session
- [x] Phase 4.1 launch mechanic (PR #8)
- [x] harness-mod-5 ratchet floor gate (PR #9)
- [x] docs sync (PR #10)
- [x] anti-stop enforcement: Stop hook + sentinels + external driver (this PR)
