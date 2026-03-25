# 08-05: Failure Mode & Stress Simulation

## Task

- Implement or script stress scenarios: (1) missing data (e.g. drop bars, NaN features), (2) volatility spike (e.g. scaled returns), (3) API outage (e.g. broker unavailable). Document system behavior under each scenario (no trade, abstain, fallback, etc.) in `docs/` as a runbook or ADR. Simulations can be scripts, config-driven tests, or documented manual procedures; the deliverable is clear documentation and, where feasible, repeatable scripts.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **anomaly-detection**, **risk-control-logic**, **abstention-logic**, **backend-service-architect**, **documentation-generator**, **refactor-engine** (if hardening error paths). Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-8-observability-safety-spec.md`
- `plans/task_plan.md` (Sprint 8, Failure Mode & Stress Simulation)
- `docs/risk-policy.md` (kill switch, circuit breaker)
- `services/risk/`, `services/execution/` (how system reacts to failures)
- `deep-review.md` (failure handling recommendations)

## Allowed files (ONLY these)

- `docs/` (runbook or ADR for failure modes and stress scenarios; e.g. `docs/runbooks/stress-scenarios.md` or `docs/sprint-8-failure-modes.md`)
- `tests/` (optional: scripts or test cases that simulate missing data, volatility spike, or API outage for documentation/reproducibility)
- `services/ml/` or `services/execution/` (only if minimal code changes are required to make behavior under stress explicit, e.g. logging or a single fallback path; prefer documenting current behavior first)

> If stress simulations should live in a dedicated service or repo, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** run live trading or destructive tests against real brokers.
- Do **not** run build, test, or verification commands unless the user explicitly asks.
- **If blocked:** Stop and ask (e.g. “Should we add a mock broker mode for API-outage simulation?”).

## Instructions

1. Use skills as above; read the spec, risk policy, and execution/risk code.
2. For each scenario (missing data, volatility spike, API outage), document: trigger, expected system behavior (e.g. no trade, abstain, fallback, error log), and any manual or automated steps to reproduce. Prefer a single runbook or ADR in `docs/` (e.g. `docs/runbooks/stress-scenarios.md` or `adr/0008-stress-scenarios.md`).
3. Where feasible, add a small script or test that simulates the scenario (e.g. inject NaN features, mock broker timeout) so behavior can be reproduced; document how to run it.
4. If current behavior under a scenario is undefined or unclear, document “Current behavior: TBD” and **pause for user input** on desired behavior before implementing any code changes.
5. Cross-reference the runbook/ADR from the spec or main docs so future work can find it.

## Done criteria

- Failure modes and stress scenarios are documented in `docs/` (runbook or ADR); system behavior under missing data, volatility spike, and API outage is described.
- Where feasible, a repeatable script or test exists for reproduction; how to run it is documented.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
