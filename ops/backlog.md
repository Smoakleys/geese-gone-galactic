# Autopilot backlog — next increments (highest value first)

The Stop hook points the agent here every turn. Keep it current: when you finish an
increment, tick it and add the next. This is guidance, not the stop condition — the
ONLY stop condition is the `ops/STOP` kill switch (or Bridger saying stop).

## Now
- [ ] **Harvest the predator check from a real Stage-C proposal** — right now the predator
      subsystem's check was hand-authored. Close the loop the honest way: run tickets whose
      builds trip a recurring subjective "unsafe pond" Stage-B defect, let Stage C surface the
      proposal, then author the check against that proposal's signature. (Or: pick the next
      mechanic and drive its check through Stage C rather than by hand.)
- [ ] **Render T-POND-05 through the visual gate** — extend `StubScreenshotWorker` (or the
      real Godot drop-in) to draw fences/predators so the sanctuary pond is visually gated too.

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
- [x] Stage C wired into the live pipeline: runner harvests staging decision logs after
      run_pending, persists `stage_c_proposals` to the store, autopilot prints them; e2e
      test proves a recurring cross-ticket defect yields a proposal (89 tests)
- [x] First full flywheel turn: `onepond_liveliness` check makes the subjective "lifeless
      pond" (granary capacity, no hatched geese) defect a mechanical Stage-A gate; certified
      w/ good+bad fixtures, tests prove it closes the gap, 4/4 still green (94 tests)
- [x] Liveliness gate driven through real tickets: T-POND-03/04 carry an `AC_LIVE` criterion
      citing `onepond_liveliness`; e2e mints a `.onepond_geese_hatched` floor and a loop test
      proves the gate forces rework (Icarus adds a hatchery) before acceptance (95 tests)
- [x] New predator mechanic + `onepond_predator_safe` check: foxes eat un-fenced geese, a
      new `fence` building protects them; T-POND-05 (all five building types) fences out two
      foxes while launching, driven to acceptance 5/5 at autonomy 1.0 (98 tests)
