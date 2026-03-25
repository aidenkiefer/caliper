# Render API Server Deployment Issue

## Summary

Render **builds** for the backend API (Docker) now **succeed**: dependencies install via `pip install -r requirements.txt` (including building `msgpack` and installing numpy, scipy, shap, etc.). **Runtime** fails when the container starts: uvicorn is invoked as `uvicorn main:app` with `WORKDIR /app/services/api`, so Python loads `main.py` as a top-level script and relative imports in `main.py` (e.g. `from .routers import ...`) raise **ImportError: attempted relative import with no known parent package**.

---

## Goal

- Deploy the **FastAPI backend** to Render as a **Web Service** using the repo’s **Dockerfile**.
- The API serves the dashboard (and other clients) and expects Postgres + Redis in production (Render add-ons or external URLs).

---

## Current Error Summary (Runtime)

| Item | Detail |
|------|--------|
| **Failure step** | Container start: `CMD ["uvicorn", "main:app", ...]` with `WORKDIR /app/services/api` |
| **Error type** | `ImportError: attempted relative import with no known parent package` |
| **Location** | `File "/app/services/api/main.py", line 21`: `from .routers import (...)` |
| **Root cause** | `main.py` is run as `__main__` (via `uvicorn main:app`), so it is not part of the `services.api` package; relative imports then fail. |
| **Exit code** | 1 |

---

## Full Runtime Traceback (excerpt)

```text
  File "/usr/local/bin/uvicorn", line 8, in <module>
    sys.exit(main())
  ...
  File "/usr/local/lib/python3.11/site-packages/uvicorn/config.py", line 458, in load
    self.loaded_app = import_from_string(self.app)
  File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 21, in import_from_string
    module = importlib.import_module(module_str)
  ...
  File "/app/services/api/main.py", line 21, in <module>
    from .routers import (
ImportError: attempted relative import with no known parent package

==> Exited with status 1
```

---

## Build Status (for context)

- **Build:** Succeeds. `pip install -r requirements.txt` completes (msgpack wheel built, all packages installed). Image is pushed and deploy starts.
- **Deploy:** Fails when the start command runs (see above).

---

## Fix Applied

1. **Run the app as a package from repo root**
   - Set **WORKDIR** to `/app` (repo root), not `/app/services/api`.
   - Invoke uvicorn with the **module path**: `services.api.main:app` instead of `main:app`.

2. **Dockerfile changes**
   - `WORKDIR /app` (so `services.api` is on `sys.path` as a package).
   - `CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

With this, Python imports `services.api.main` as a submodule of `services.api`, so relative imports in `main.py` (e.g. `from .routers import ...`) resolve correctly.

---

## Docker & Build Context

### Dockerfile (root)

- **Path:** `Dockerfile` (repo root)
- **Base:** `python:3.11-slim`
- **Install:** `pip install -r requirements.txt` (no Poetry in image)
- **Flow:** Copy `requirements.txt` → pip install → copy `pyproject.toml` / `poetry.lock` and service pyproject.toml → copy full repo → `WORKDIR /app` → `CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`

### Docker Compose (local only)

- **Path:** `docker-compose.yml` (repo root)
- **Services:** `postgres` (TimescaleDB), `redis`, `api` (builds from same `Dockerfile`). Ensure the api service uses `WORKDIR /app` and `uvicorn services.api.main:app` so behavior matches Render.

### Key files

| File | Purpose |
|------|--------|
| `Dockerfile` | Image build for the API (used by Render and `docker-compose build api`) |
| `docker-compose.yml` | Local stack (postgres, redis, api); reference for env and ports |
| `requirements.txt` | Pip dependencies for Docker build |
| `pyproject.toml` / `poetry.lock` | Root project; lock can be used to regenerate `requirements.txt` |
| `services/api/main.py` | FastAPI app entrypoint (uses relative imports) |
| `configs/environments/.env.example` | Example env vars for API (DB, Redis, Alpaca, etc.) |

---

## Suggested next steps for Claude Code

1. **Confirm Dockerfile** uses `WORKDIR /app` and `CMD ["uvicorn", "services.api.main:app", ...]` (see “Fix Applied” above).
2. **Align docker-compose** so the api service runs with the same WORKDIR and uvicorn module path (so local runs match Render).
3. **Re-deploy on Render** and verify the service starts and `/v1/health` responds.
4. **Set Render env vars** for the API (e.g. `DATABASE_URL`, `REDIS_URL`, `ALPACA_*`) per `configs/environments/.env.example`.

---

## Previous issue (build-time, resolved)

Earlier, builds failed during **poetry install** with `BrokenPipeError` / `ChunkedEncodingError` while installing numpy. The switch to **pip install -r requirements.txt** in the Dockerfile resolved that; the current problem was runtime-only (relative imports).

---

## References

- **API app:** `services/api/main.py`
- **Root deps:** `pyproject.toml`, `poetry.lock`, `requirements.txt`
- **Local stack:** `docker-compose.yml`
- **Env example:** `configs/environments/.env.example`
- **Deploy runbook:** `docs/runbooks/vercel-deployment.md` (dashboard); API deployment is Docker on Render.
