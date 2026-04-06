# Caliper user guide

This guide is for **human operators and developers** who want to install Caliper, run the stack locally, and use the **equities** and **optional Polymarket** tracks safely. It complements the agent-focused **[docs/workflow/workflow.md](workflow/workflow.md)** and the doc map **[docs/INDEX.md](INDEX.md)**.

---

## 1. Principles and safety

- **Paper or dust capital first.** Use Alpaca **paper** keys and **`TRADING_MODE=PAPER`** for equities. For Polymarket, use **`--dry-run`** and small size until you trust telemetry and limits.
- **Two execution worlds.** **Equities** flow through **RiskManager → OMS → Alpaca**. **Polymarket** uses **`services/polymarket/`** with its **own** safety limits — it does **not** use the equity risk service for CLOB orders.
- **Secrets.** Never commit API keys or wallet private keys. Use **`.env`** files ignored by git and restrict file permissions (e.g. `chmod 600 .env.polymarket`).
- **Docs for depth:** **[docs/risk-policy.md](risk-policy.md)** (equity), **[docs/runbooks/polymarket-operations.md](runbooks/polymarket-operations.md)** (Polymarket), **[docs/security.md](security.md)** (auth and secrets).

---

## 2. Prerequisites

| Requirement | Notes |
|---------------|--------|
| **Python 3.11+** | Used with Poetry for all `services/*` |
| **Node.js 18+** | For `apps/dashboard` |
| **Docker + Docker Compose** | Postgres (TimescaleDB), Redis, optional API container |
| **Poetry** | Python dependency and virtualenv management |
| **Alpaca account** | Paper trading keys for equities features (optional if you only use Polymarket or read-only API) |
| **Polymarket** | Only if you run the bot — Polygon wallet, MATIC for gas, USDC on Polygon — see **[docs/POLYMARKET-QUICKSTART.md](POLYMARKET-QUICKSTART.md)** |

---

## 3. One-time installation

### 3.1 Clone and infrastructure

```bash
git clone <your-fork-or-origin-url>
cd quant
docker-compose up -d
```

This starts **Postgres**, **Redis**, and (per `docker-compose.yml`) the **API** service. Default DB is aligned with **`configs/environments/.env.example`** (`quant_trading` database, `quant_user` / `quant_password` on `localhost:5432`).

### 3.2 Python environment

```bash
poetry install
poetry shell
```

### 3.3 Database schema (Alembic)

From the repo root (with Poetry env active):

```bash
cd services/data
poetry run alembic upgrade head
cd ../..
```

This applies **equity** and **`pm.*`** migrations (Polymarket, features, simulation, probability, regime/allocation, paper trades — revisions through **`007_*`** as of v2.6.0).

### 3.4 Environment variables

```bash
cp configs/environments/.env.example configs/environments/.env
```

Edit **`configs/environments/.env`**:

- **`DATABASE_URL`** — Postgres URL (matches Docker Compose if local).
- **`ALPACA_*`** and **`TRADING_MODE=PAPER`** — for equities execution and data where wired.
- **`DB_URL`** — Several FastAPI routers (**features**, **regime**, **allocation**, **ranking**, **fleet**) read **`os.environ["DB_URL"]`**. If you run the API **outside** Docker, set this to the **same** connection string as **`DATABASE_URL`**, for example:

  ```bash
  export DB_URL="postgresql://quant_user:quant_password@localhost:5432/quant_trading"
  ```

  Docker Compose may only inject **`DATABASE_URL`**; if **`GET /v1/features/...`**, **`/v1/regime/...`**, etc. return **503** “database not configured”, add **`DB_URL`** to the API service environment.

### 3.5 Dashboard (Node)

```bash
npm install
cd apps/dashboard
npm install
```

Set **`NEXT_PUBLIC_API_URL`** to **`http://localhost:8000/v1`** (default in `apps/dashboard/src/lib/api.ts`; see **`apps/dashboard/README.md`**) so the UI calls the local API’s versioned prefix.

---

## 4. Running the platform

### 4.1 API (FastAPI)

**Option A — Docker (Makefile):**

```bash
make api-dev
```

**Option B — Local uvicorn:**

```bash
cd services/api
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **OpenAPI UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

**Contract reference:** **[docs/api-contracts.md](api-contracts.md)** — includes **Polymarket**, **simulation/evaluation**, **probability**, **regime/allocation**, **ranking/fleet**, and notes on **stub vs live** behavior.

### 4.2 Dashboard (Next.js)

```bash
make dashboard-dev
# or: cd apps/dashboard && npm run dev
```

- **App:** [http://localhost:3000](http://localhost:3000)  
- **Spec / UX:** **[docs/dashboard-spec.md](dashboard-spec.md)**  
- **Key routes:** **`/start`** (first-time checklist), **`/platform`** (capability map + status badges), **`/platform/features`** (`pm.features` when API **`DB_URL`** is set), **`/platform/polymarket`** (sessions), **`/platform/regime-allocation`**, **`/platform/probability`**, **`/platform/simulation`**, **`/platform/ranking-fleet`**, **`/platform/equities`** (shortcuts to core equity pages). Stub/mock behavior matches **[docs/api-contracts.md](api-contracts.md)**.  
- **Sprint 16 panels** (ranker, fleet, regime timeline) live under **`apps/dashboard/src/components/sprint-16/`**. Until the backend wires **`/v1/ranking/*`** and **`/v1/fleet/*`** to live services, those endpoints return **mock JSON** (dashboard still demonstrates layout and polling).

### 4.3 Full stack via Compose

```bash
make up
```

Use **`make logs`** / **`make logs-api`** to follow processes; **`make down`** to stop.

---

## 5. Using the equities track

1. **Configure Alpaca paper keys** in **`configs/environments/.env`** and keep **`TRADING_MODE=PAPER`**.
2. **Read risk limits** in **[docs/risk-policy.md](risk-policy.md)** before enabling any live path.
3. **Backtests** use **`services/backtest/`** and strategies under **`packages/strategies/`** (e.g. SMA Crossover). Strategy configs live in **`configs/strategies/*.yaml`**.
4. **API** exposes health, strategies, runs, positions, orders, ML-related endpoints — see **[docs/api-contracts.md](api-contracts.md)** and **[docs/runbooks/api-verification.md](runbooks/api-verification.md)**.
5. **Model Observatory** (Sprints 7–9) is in the dashboard; feature list in **[docs/FEATURES.md](FEATURES.md)**.

---

## 6. Using the Polymarket track (optional)

Polymarket is **optional** and **capital-separate** from Alpaca.

1. Follow the short checklist in **[docs/POLYMARKET-QUICKSTART.md](POLYMARKET-QUICKSTART.md)** (wallet, `.env.polymarket`, migrations, dry-run).
2. **Dry-run** (no orders):

   ```bash
   cd services/polymarket
   poetry run polymarket-session --dry-run
   ```

3. **Live session** only after you accept loss caps and operational risk — see **[docs/runbooks/polymarket-operations.md](runbooks/polymarket-operations.md)**.
4. **Session analytics** in the main API: **`GET /v1/polymarket/sessions`** and related routes (shapes in **`packages/common/polymarket_schemas.py`**).

**Research stack (v2.2–v2.6):** Feature snapshots (**`/v1/features/...`**), offline simulation/evaluation (**`/v1/simulation/*`**, **`/v1/evaluation/*`** — many handlers still stubbed), probability model (**`/v1/probability/*`** — partial mocks), **regime/allocation** (**`/v1/regime/*`**, **`/v1/allocation/*`** — **live `pm.*` reads** when **`DB_URL`** is set), **ranking/fleet** (**`/v1/ranking/*`**, **`/v1/fleet/*`** — **mock responses** until wired). Details: **[docs/api-contracts.md](api-contracts.md)**.

---

## 7. Where data lives

- **Canonical schema narrative:** **[docs/data-contracts.md](data-contracts.md)**  
- **Equity + app tables:** migrations under **`services/data/alembic/versions/`**  
- **Polymarket and research:** Postgres schema **`pm`** (sessions, orders, features, simulation runs, probability tables, regime/allocation, paper trades)

---

## 8. Milestones and “what shipped”

- **Version log and backlog:** **[docs/plans/PROGRESS.md](plans/PROGRESS.md)**  
- **Sprint summaries:** **[docs/plans/summaries/](plans/summaries/)** — e.g. Polymarket (**SPRINT-10**), simulation (**SPRINT-13**), probability (**SPRINT-14**), **regime/allocation ([SPRINT-15-REGIME-ALLOCATION.md](plans/summaries/SPRINT-15-REGIME-ALLOCATION.md))**, **ranking/fleet ([SPRINT-16-CROSS-SECTIONAL-FLEET.md](plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md))**  
- **Feature checklist:** **[docs/FEATURES.md](FEATURES.md)**

---

## 9. Troubleshooting

| Symptom | Things to check |
|---------|------------------|
| API **503** on features / regime / ranking / fleet | Is **`DB_URL`** set for the API process? Same URL as Postgres? |
| **404** on regime/allocation “current” | Normal if no row has been written yet; writers run in detector/allocation/fleet pipelines, not magically on install. |
| Dashboard cannot reach API | **`NEXT_PUBLIC_API_URL`**, CORS **`CORS_ORIGINS`** in API env, firewall |
| Migration errors | Postgres version, TimescaleDB extension, `poetry run alembic current` / `history` in **`services/data`** |
| Polymarket dry-run fails | Gamma/CLOB/Binance connectivity, env vars in **`.env.polymarket`**, see quickstart |

---

## 10. Related runbooks

| Topic | Doc |
|--------|-----|
| API checks | [docs/runbooks/api-verification.md](runbooks/api-verification.md) |
| Backtests | [docs/runbooks/backtest-verification.md](runbooks/backtest-verification.md) |
| Execution & risk | [docs/runbooks/execution-verification.md](runbooks/execution-verification.md) |
| ML safety | [docs/runbooks/ml-safety-verification.md](runbooks/ml-safety-verification.md) |
| Polymarket ops | [docs/runbooks/polymarket-operations.md](runbooks/polymarket-operations.md) |

---

**Maintained as a human onboarding path.** For agent ticket work, start from **[docs/INDEX.md](INDEX.md)** and the specific ticket’s **Allowed Files**.
