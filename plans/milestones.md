# Project Milestones

## Planning Phase Milestones

### Milestone 1: Planning Foundation ✅ COMPLETE
**Target:** Day 1  
**Status:** ✅ Complete  
**Deliverables:**
- [x] Folder structure created (`/plans`, `/docs`, `/adr`)
- [x] `task_plan.md` created with agent assignments
- [x] `findings.md` created with research insights
- [x] `progress.md` created for tracking
- [x] `milestones.md` created (this file)

### Milestone 2: Parallel Agent Documentation
**Target:** Day 2-3  
**Status:** 🔜 Not Started  
**Deliverables:**
- [ ] `docs/architecture.md` - System architecture and component design
- [ ] `docs/data-contracts.md` - Schema definitions and data lifecycle
- [ ] `docs/api-contracts.md` - API endpoint specifications
- [ ] `docs/security.md` - Security policies and safeguards
- [ ] `docs/dashboard-spec.md` - Dashboard UI/UX specifications
- [ ] Tool definitions section in `architecture.md`

### Milestone 3: Integration & Validation
**Target:** Day 4  
**Status:** 🔜 Not Started  
**Deliverables:**
- [ ] All docs reviewed for internal consistency
- [ ] Conflicts resolved via ADRs in `/adr`
- [ ] Open questions addressed or documented
- [ ] Risk gates validated

### Milestone 4: Cursor Handoff Preparation
**Target:** Day 5  
**Status:** 🔜 Not Started  
**Deliverables:**
- [ ] Cursor Implementation Sprint section added to `task_plan.md`
- [ ] Implementation task breakdown created
- [ ] Final planning review complete
- [ ] Handoff documentation ready

---

## Implementation Phase Milestones (Cursor Execution)

### Days 1–2: Foundations
**Objective:** Set up infrastructure and data ingestion  
**Deliverables:**
- [ ] Monorepo structure scaffolded
- [ ] Docker + docker-compose for local dev
- [ ] Data ingestion service for 1 provider (historical + live)
- [ ] Postgres database with schema
- [ ] Data validation pipelines

### Days 3–5: First Strategy End-to-End (Stocks)
**Objective:** Complete vertical slice - data → model → backtest → report  
**Deliverables:**
- [ ] Baseline feature pipeline (technical indicators)
- [ ] XGBoost classification model (1-5 day horizon)
- [ ] Backtesting with realistic costs
- [ ] Report generation + artifact storage
- [ ] Strategy plugin framework established

### Days 6–8: Second Strategy (Mean Reversion or Volatility)
**Objective:** Validate plugin architecture with second strategy  
**Deliverables:**
- [ ] Second strategy plugin implemented
- [ ] Comparative backtesting (Strategy 1 vs Strategy 2)
- [ ] Dashboard showing strategy comparison
- [ ] Performance metrics pipeline

### Days 9–11: Options Strategy (Defined-Risk)
**Objective:** Add options capabilities  
**Deliverables:**
- [ ] Options data ingestion (or simulation)
- [ ] Debit spread strategy (bull call / bear put)
- [ ] Liquidity filters for options
- [ ] Risk exposure calculations (delta, gamma)
- [ ] Options backtest evaluation

### Days 12–14: Execution + Dashboard + Hardening
**Objective:** Complete system with paper trading and monitoring  
**Deliverables:**
- [ ] Broker adapter (Alpaca/IB) for paper trading
- [ ] Risk management module with kill switches
- [ ] Alert system (Slack/Email)
- [ ] Next.js dashboard deployed to Vercel
- [ ] API backend (FastAPI) deployed
- [ ] Go-live checklist for limited capital

---

## Success Criteria

### Planning Phase Complete When:
1. ✅ All 6 doc files exist in `/docs`
2. ✅ Each doc contains all required sections
3. ✅ Contracts are implementation-ready (no ambiguity)
4. ✅ Risk and security gates clearly defined
5. ✅ Cursor Implementation Sprint section exists in `task_plan.md`

### Implementation Phase Complete When:
1. ✅ Data ingestion working for at least 1 provider
2. ✅ Strategy plugin framework with 2+ strategies
3. ✅ Backtesting with walk-forward evaluation + costs
4. ✅ Paper trading end-to-end with OMS + risk gate
5. ✅ Dashboard deployed on Vercel showing metrics, runs, positions
6. ✅ Kill switch + alerts functioning
7. ✅ Runbooks + risk policy documented

---

## Critical Path

```
Planning Foundation
    ↓
Parallel Agent Documentation
    ↓
Integration & Validation
    ↓
Cursor Handoff
    ↓
Implementation: Foundations
    ↓
Implementation: First Strategy
    ↓
Implementation: Second Strategy
    ↓
Implementation: Options Strategy
    ↓
Implementation: Execution & Hardening
    ↓
Go-Live Checklist & Limited Capital Deployment
```

---

## Notes
- **Planning Phase:** Antigravity Agents (current)
- **Implementation Phase:** Cursor Agents (handoff after planning complete)
- **Risk Level:** 6-7 (moderate) - controlled drawdowns, systematic risk management
- **First Deployment:** Paper trading only, then live with strict safeguards
