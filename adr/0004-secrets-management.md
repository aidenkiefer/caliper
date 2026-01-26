# 4. Secrets Management Strategy

date: 2026-01-25
status: accepted

## Context
Trading bots hold keys to real money. Security leaks are catastrophic. We need a way to manage secrets (Broker Keys, DB Passwords) that:
- Never exposes them in Git.
- Separates "Paper" credentials from "Live" credentials.
- Is easy to inject into Docker containers.

## Decision
We will use **Doppler** (or similar external Secrets Manager) for all environments, enforcing strict **Environment Isolation**.

## Consequences
### Positive
- **No .env in Prod:** Removes the risk of accidentally `cat`ing a .env file or committing it.
- **Centralized Rotation:** Can rotate a Broker Key in Doppler and restart services, rather than SSHing into servers to edit files.
- **Audit Logs:** We can see exactly who accepted/viewed the production keys.

### Negative
- **Setup Friction:** Requires installing `doppler-cli` and `doppler run` command in Dockerfiles/entrypoints.

## Alternatives Considered
- **Git-ignored .env files:** Acceptable for local dev only. Rejected for production due to security risk and lack of audit trail.
- **Hardcoded constants:** Strictly Forbidden.

## Compliance
- **Rule:** Live Keys are NEVER allowed on a machine configured for Paper Trading.
