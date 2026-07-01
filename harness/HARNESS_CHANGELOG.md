# Harness changelog

Every change to `harness/` is logged here with rationale. The self-mod validator
(`harness/selfmod/validator.py`) mechanically rejects a change that touches `harness/`
without a matching entry. Reverts are one command via the token in `harness/reverts.log`.

## harness-mod-0 — Phase 0.5 walking skeleton
- Core data model with `criteria_hash` freeze and default-FAIL verdicts (`models.py`).
- State machine whose only edge into `COMMIT_PENDING` is `STAGE_B_PASS` (`states.py`).
- Check runner with fixture-based certification and `registry.lock` (`checks/`).
- Gatekeeper as sole commit authority + monotonic ratchet (`gatekeeper.py`, `ratchet.py`).
- Stub builder/reviewer + reviewer-isolation packet builder (`icarus/`, `review/`).
- Self-mod validator + revert bookkeeping (`selfmod/`).
- Rationale: prove the governance thesis end-to-end with zero LLM/art cost before wiring
  real reviewers, Icarus, and the art pipeline. See `docs/PLAN.md` Phase 0.5.
