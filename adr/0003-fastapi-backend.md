# 3. Synchronous vs Async API Framework

date: 2026-01-25
status: accepted

## Context
The backend API serves the dashboard metrics and handles trading commands.
- It needs to be responsive.
- It needs to handle long-running tasks (e.g., "Run Backtest") without blocking.
- It is Python-based to integrate with the ML stack (pandas, scikit-learn).

## Decision
We will use **FastAPI (Python)**.

## Consequences
### Positive
- **Async Native:** Native `async/await` support allows handling high concurrency (waiting on DB or Broker API) without blocking threads.
- **Pydantic Integration:** Shared schemas defined in `data-contracts.md` can be directly used as API request/response models.
- **Auto-Docs:** Swagger UI is critical for testing the API separate from the frontend.

### Negative
- **Complexity:** Async Python requires careful handling of blocking libraries (e.g., `requests` vs `httpx`). We must ensure we use async drivers for DB and HTTP.

## Alternatives Considered
- **Flask:** Too synchronous; Websockets/Long-polling are harder to implement.
- **Django:** Too "batteries included" and heavy. We don't need Django ORM or Admin for this micro-service architecture.
