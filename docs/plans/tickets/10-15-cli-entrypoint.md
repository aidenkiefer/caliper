# Ticket: 10-15-cli-entrypoint

## Task
Create CLI entrypoint for running a single Polymarket trading session.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/cli.py`
- Create: `services/polymarket/__main__.py`
- Modify: `services/polymarket/pyproject.toml` (add CLI script)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 2.2)

### Optional read-only references
- `services/polymarket/session.py`
- `services/polymarket/config.py`

## Agent type
backend-agent

## Skill pack
None required (straightforward CLI)

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 2
- Max total tool calls: 10

## Done criteria
- `cli.py` implements `main()` function using `typer` or `click`
- CLI loads config from environment variables (via `PolymarketConfig`)
- CLI accepts optional flags: `--dry-run` (no real orders), `--target-hour` (override config)
- Runs `SessionOrchestrator.run_session(config)`
- Logs to stdout and file (`logs/polymarket_<session_id>.log`)
- `__main__.py` calls `cli.main()` for `python -m polymarket` invocation
- `pyproject.toml` adds script: `polymarket-session = "polymarket.cli:main"`
- `docs/plans/PROGRESS.md` updated
