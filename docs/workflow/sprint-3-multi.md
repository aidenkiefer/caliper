# Sprint 3 Multi-Agent Workflow: Backtesting & Reporting

**Sprint 3 Focus:** Implement backtesting engine, connect strategies, generate reports, verify P&L accuracy

---

## 🎯 Sprint 3 Overview

**Goal:** Build a production-ready backtesting engine that can simulate strategies on historical data, calculate accurate P&L, and generate comprehensive reports.

**Timeline:** Days 7-9  
**Status:** 🟡 Ready to Start

---

## 📋 Sprint 3 Tasks Breakdown

### Task 1: Backtest Engine Core (Backend Agent)
- Implement `services/backtest` service structure
- Choose and integrate backtesting library (Backtrader or vectorbt)
- Create `BacktestEngine` class
- Implement data loading from database
- Implement strategy execution loop

### Task 2: Strategy Integration (Backend Agent)
- Connect `packages/strategies` to backtest engine
- Implement signal-to-order conversion
- Implement fill simulation (market orders, slippage)
- Implement position tracking

### Task 3: P&L Calculation (Backend Agent)
- Implement trade-level P&L
- Implement portfolio-level P&L
- Calculate performance metrics (Sharpe, max drawdown, win rate)
- Verify P&L math correctness

### Task 4: Report Generation (Backend Agent)
- Generate JSON report (machine-readable)
- Generate HTML report (human-readable)
- Include equity curve, trade list, metrics
- Store reports in database/object storage

### Task 5: Testing & Verification (QA Agent)
- Unit tests for backtest engine
- Integration test: Run SMA Crossover strategy
- P&L validation tests (known-good scenarios)
- Report generation tests

### Task 6: Design Review (Architect Agent)
- Review backtest engine architecture
- Validate against `docs/architecture.md`
- Ensure extensibility for future strategies
- Document design decisions

---

## 👥 Agent Assignment

### Backend Agent (Primary)
**Owns:** Tasks 1-4 (Backtest Engine, Strategy Integration, P&L, Reports)

**Files:**
- `services/backtest/**/*.py` (all files)
- `services/backtest/README.md`
- `services/backtest/pyproject.toml`

**Cannot Touch:**
- `services/data/models.py` (Data Agent)
- `packages/strategies/base.py` (already exists, use it)
- `docker-compose.yml` (DevOps Agent)
- `tests/**` (QA Agent)

### QA Agent
**Owns:** Task 5 (Testing & Verification)

**Files:**
- `services/backtest/test_*.py`
- `tests/integration/test_backtest.py`
- `docs/runbooks/backtest-verification.md`

**Cannot Touch:**
- `services/backtest/**/*.py` (implementation, Backend Agent)

### Architect Agent
**Owns:** Task 6 (Design Review)

**Files:**
- `docs/architecture.md` (updates)
- `adr/0005-backtest-engine-design.md` (new ADR if needed)

**Cannot Touch:**
- Any code files

---

## 🛠️ Skills to Invoke

### Backend Agent Must Invoke:
1. **`@using-superpowers`** - Always first
2. **`@python-patterns`** - Python best practices
3. **`@clean-code`** - Code quality standards
4. **`@testing-patterns`** - Test design (for testable interfaces)

### QA Agent Must Invoke:
1. **`@using-superpowers`** - Always first
2. **`@testing-patterns`** - Test implementation
3. **`@python-patterns`** - Python test code

### Architect Agent Must Invoke:
1. **`@using-superpowers`** - Always first
2. **`@software-architecture`** - System design (if available)

---

## 📦 Sprint 3 Output Contracts

### Backend Agent Must Deliver:

1. **Backtest Engine (`services/backtest/engine.py`)**
   ```python
   class BacktestEngine:
       def run(strategy: Strategy, data: List[PriceBar], config: BacktestConfig) -> BacktestResult
   ```

2. **Backtest Result Model (`services/backtest/models.py`)**
   ```python
   class BacktestResult:
       equity_curve: List[EquityPoint]
       trades: List[Trade]
       metrics: PerformanceMetrics
       metadata: BacktestMetadata
   ```

3. **Report Generator (`services/backtest/report.py`)**
   ```python
   class ReportGenerator:
       def generate_json(result: BacktestResult) -> dict
       def generate_html(result: BacktestResult) -> str
   ```

4. **Configuration (`services/backtest/config.py`)**
   ```python
   class BacktestConfig:
       initial_capital: Decimal
       commission_rate: Decimal
       slippage_model: SlippageModel
       start_date: datetime
       end_date: datetime
   ```

5. **Documentation**
   - `services/backtest/README.md` - Usage guide
   - Code docstrings for all public methods

### QA Agent Must Deliver:

1. **Unit Tests**
   - `services/backtest/test_engine.py` - Engine tests
   - `services/backtest/test_pnl.py` - P&L calculation tests
   - `services/backtest/test_report.py` - Report generation tests

2. **Integration Test**
   - `tests/integration/test_backtest_sma_crossover.py` - Full SMA Crossover backtest

3. **Verification Runbook**
   - `docs/runbooks/backtest-verification.md` - How to verify backtest accuracy

### Architect Agent Must Deliver:

1. **Architecture Updates**
   - Updated `docs/architecture.md` with backtest service details
   - Data flow diagram for backtest process

2. **ADR (if needed)**
   - `adr/0005-backtest-engine-design.md` - Design decisions (Backtrader vs vectorbt, etc.)

---

## ✅ Sprint 3 Acceptance Criteria

### Functional Requirements

- [ ] **Backtest Engine Runs**
  - Can load historical data from database
  - Can execute strategy on data
  - Produces BacktestResult with all required fields

- [ ] **Strategy Integration Works**
  - SMA Crossover strategy runs in backtest
  - Signals converted to orders correctly
  - Orders filled with realistic simulation

- [ ] **P&L Calculation Accurate**
  - Trade-level P&L matches manual calculation
  - Portfolio equity curve updates correctly
  - Performance metrics calculated correctly (Sharpe, drawdown, win rate)

- [ ] **Reports Generated**
  - JSON report contains all metrics
  - HTML report renders correctly
  - Reports stored/accessible

### Technical Requirements

- [ ] **Code Quality**
  - Follows `@python-patterns` skill
  - Follows `@clean-code` skill
  - Type hints on all functions
  - Docstrings for all classes/methods

- [ ] **Tests Pass**
  - Unit tests: `poetry run pytest services/backtest/`
  - Integration test: SMA Crossover backtest runs successfully
  - P&L validation: Known-good scenarios pass

- [ ] **Performance**
  - Backtest runs in reasonable time (< 30s for 1 year of daily data)
  - Memory usage acceptable

### Documentation Requirements

- [ ] **README Updated**
  - `services/backtest/README.md` explains usage
  - Example code provided

- [ ] **Runbook Created**
  - `docs/runbooks/backtest-verification.md` explains verification process

- [ ] **Architecture Updated**
  - `docs/architecture.md` includes backtest service details

---

## 🎬 Sprint 3 Orchestrator Prompt

**Paste this into Composer 1:**

```
You are the Sprint Orchestrator for Sprint 3: Backtesting & Reporting.

Read:
- docs/sprint-3-multi.md (this file)
- docs/WORKFLOW.md (multi-agent protocol)
- plans/task_plan.md (Sprint 3 section)
- docs/architecture.md (backtest service design)
- agents/briefs/BACKEND.md
- agents/briefs/QA.md
- agents/briefs/ARCHITECT.md

Goal: Complete Sprint 3 using multi-agent parallel workflow.

Context:
- Sprint 1 & 2 are complete (data ingestion, feature pipeline, strategies)
- We have SMA Crossover strategy ready to backtest
- We have historical AAPL data in database
- Need to build backtesting engine and verify P&L accuracy

Steps:
1. Generate Sprint 3 Plan (breakdown tasks, identify dependencies)
2. Create Agent Prompts (Backend, QA, Architect)
3. Provide Integrator Prompt

Output format:
1) Sprint 3 Plan
2) Backend Agent Prompt
3) QA Agent Prompt
4) Architect Agent Prompt
5) Integrator Prompt
```

---

## 📝 Sprint 3 Agent Prompts

### Backend Agent Prompt

**Copy this to Composer 2:**

```
You are the Backend Agent for Sprint 3: Backtesting & Reporting.

Read:
- agents/briefs/BACKEND.md (your role)
- docs/sprint-3-multi.md (Sprint 3 details)
- docs/architecture.md (backtest service design)
- packages/strategies/base.py (Strategy interface)
- packages/strategies/sma_crossover.py (example strategy)

Your Tasks:
1. Implement Backtest Engine (`services/backtest/engine.py`)
   - Choose: Backtrader or vectorbt (document decision)
   - Create BacktestEngine class
   - Implement run() method that takes Strategy + data + config
   - Load data from database (use Data Agent's models)

2. Implement Strategy Integration
   - Connect Strategy.generate_signals() to backtest
   - Convert signals to orders
   - Implement fill simulation (market orders, slippage)

3. Implement P&L Calculation
   - Trade-level P&L
   - Portfolio equity curve
   - Performance metrics (Sharpe, max drawdown, win rate)

4. Implement Report Generation (`services/backtest/report.py`)
   - JSON report (machine-readable)
   - HTML report (human-readable with charts)
   - Store reports

File Ownership:
- ✅ CAN edit: services/backtest/**/*.py
- ❌ CANNOT edit: services/data/models.py, tests/**, docker-compose.yml

Skills to Invoke:
1. @using-superpowers (always first)
2. @python-patterns
3. @clean-code

Acceptance Criteria:
- [ ] BacktestEngine.run() executes strategy successfully
- [ ] SMA Crossover strategy runs end-to-end
- [ ] P&L calculation verified (manual check)
- [ ] Reports generated (JSON + HTML)
- [ ] Code follows skills
- [ ] README.md updated

Output Format:
1. Implementation summary
2. Files created/modified
3. Skill evidence (checklist completion)
4. Known issues/limitations
```

### QA Agent Prompt

**Copy this to Composer 3:**

```
You are the QA Agent for Sprint 3: Backtesting & Reporting.

Read:
- agents/briefs/QA.md (your role)
- docs/sprint-3-multi.md (Sprint 3 details)
- services/backtest/** (Backend Agent's implementation)

Your Tasks:
1. Write Unit Tests (`services/backtest/test_*.py`)
   - test_engine.py: BacktestEngine tests
   - test_pnl.py: P&L calculation tests
   - test_report.py: Report generation tests

2. Write Integration Test (`tests/integration/test_backtest_sma_crossover.py`)
   - Full SMA Crossover backtest
   - Verify signals generated
   - Verify orders executed
   - Verify P&L calculated

3. Create Verification Runbook (`docs/runbooks/backtest-verification.md`)
   - How to verify backtest accuracy
   - Known-good test scenarios
   - Troubleshooting guide

File Ownership:
- ✅ CAN edit: services/backtest/test_*.py, tests/**, docs/runbooks/**
- ❌ CANNOT edit: services/backtest/**/*.py (implementation)

Skills to Invoke:
1. @using-superpowers (always first)
2. @testing-patterns
3. @python-patterns

Acceptance Criteria:
- [ ] All unit tests pass
- [ ] Integration test passes
- [ ] P&L validation tests pass (known-good scenarios)
- [ ] Runbook created
- [ ] Tests follow @testing-patterns skill

Output Format:
1. Test summary
2. Test files created
3. Test results
4. Runbook location
```

### Architect Agent Prompt

**Copy this to Composer 4:**

```
You are the Architect Agent for Sprint 3: Backtesting & Reporting.

Read:
- agents/briefs/ARCHITECT.md (your role)
- docs/sprint-3-multi.md (Sprint 3 details)
- docs/architecture.md (current architecture)
- services/backtest/** (Backend Agent's implementation)

Your Tasks:
1. Review Backtest Engine Architecture
   - Validate against docs/architecture.md
   - Check extensibility for future strategies
   - Review design decisions

2. Update Architecture Documentation
   - Update docs/architecture.md with backtest service details
   - Add data flow diagram for backtest process

3. Create ADR (if needed)
   - Document Backtrader vs vectorbt decision
   - Document design patterns used
   - Document trade-offs

File Ownership:
- ✅ CAN edit: docs/architecture.md, adr/*.md
- ❌ CANNOT edit: Any code files

Skills to Invoke:
1. @using-superpowers (always first)
2. @software-architecture (if available)

Acceptance Criteria:
- [ ] Architecture reviewed
- [ ] docs/architecture.md updated
- [ ] ADR created (if significant decisions)
- [ ] Design validated

Output Format:
1. Architecture review summary
2. Documentation updates
3. ADR created (if applicable)
```

---

## 🔄 Sprint 3 Integrator Prompt

**Run this in Composer 1 after all agents complete:**

```
You are the Integrator for Sprint 3: Backtesting & Reporting.

Read:
- docs/sprint-3-multi.md (Sprint 3 requirements)
- Backend Agent's output summary
- QA Agent's output summary
- Architect Agent's output summary

Your Tasks:
1. Merge Agent Outputs
   - Resolve any file conflicts
   - Ensure consistency across agents
   - Verify file ownership boundaries respected

2. Run Acceptance Tests
   - Run unit tests: poetry run pytest services/backtest/
   - Run integration test: poetry run pytest tests/integration/test_backtest_sma_crossover.py
   - Verify P&L calculation manually

3. Verify Sprint 3 Completion
   - Check all acceptance criteria met
   - Verify documentation updated
   - Verify tests pass

4. Update Progress
   - Mark Sprint 3 tasks complete in plans/task_plan.md
   - Update plans/progress.md
   - Create SPRINT3_SUMMARY.md

Output Format:
1. Merge summary
2. Test results
3. Acceptance criteria status
4. Documentation updates
5. Sprint 3 completion confirmation
```

---

## 📊 Sprint 3 Dependencies

```
Backend Agent (Engine) ──┐
                         ├──> QA Agent (Tests)
Backend Agent (Reports) ─┘
                         │
                         └──> Architect Agent (Review)
```

**Execution Order:**
1. Backend Agent starts immediately (no dependencies)
2. QA Agent starts after Backend Agent completes (needs implementation)
3. Architect Agent can run in parallel with QA (reads Backend output)

**Parallelization:**
- Backend Agent: Works independently
- QA Agent: Waits for Backend
- Architect Agent: Can start after Backend provides summary

---

## 🧪 Sprint 3 Verification Steps

### Step 1: Manual Backtest Run

```bash
cd services/backtest
poetry run python -c "
from engine import BacktestEngine
from packages.strategies.sma_crossover import SMACrossoverStrategy
from database import get_session_local
from models import PriceBarModel

# Load data
db = get_session_local()()
bars = db.query(PriceBarModel).filter(PriceBarModel.symbol == 'AAPL').all()

# Run backtest
strategy = SMACrossoverStrategy('test', {'short_period': 20, 'long_period': 50})
engine = BacktestEngine()
result = engine.run(strategy, bars, BacktestConfig(initial_capital=100000))

# Verify
print(f'Total Return: {result.metrics.total_return:.2%}')
print(f'Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}')
print(f'Max Drawdown: {result.metrics.max_drawdown:.2%}')
print(f'Trades: {len(result.trades)}')
"
```

### Step 2: P&L Validation

**Known-Good Scenario:**
- Buy 100 shares @ $150
- Sell 100 shares @ $155
- Commission: $1 per trade
- Expected P&L: (155 - 150) * 100 - 2 = $498

**Test:**
```python
# QA Agent should create this test
def test_pnl_calculation():
    trade = Trade(
        entry_price=Decimal('150'),
        exit_price=Decimal('155'),
        quantity=100,
        commission=Decimal('2')
    )
    pnl = calculate_trade_pnl(trade)
    assert pnl == Decimal('498')
```

### Step 3: Report Verification

```bash
# Generate report
poetry run python services/backtest/generate_report.py --backtest-id 1

# Verify files created
ls reports/backtest_1.json
ls reports/backtest_1.html

# Verify JSON structure
cat reports/backtest_1.json | jq '.metrics'
```

---

## 🚨 Sprint 3 Red Flags

**STOP if you see:**

- Backend Agent editing `services/data/models.py` → Data Agent owns that
- QA Agent editing `services/backtest/engine.py` → Backend Agent owns that
- Architect Agent writing code → Architect only does docs
- Skills not invoked → Mandatory before coding
- P&L calculation not verified → Critical for accuracy

**Instead:**

- Backend Agent uses Data Agent's models (import, don't modify)
- QA Agent tests Backend Agent's interfaces (don't modify implementation)
- Architect Agent reviews and documents (no code)
- Always invoke skills first
- Verify P&L with known-good scenarios

---

## 📚 Sprint 3 Reference Files

**Must Read:**
- `docs/sprint-3-multi.md` (this file)
- `docs/WORKFLOW.md` (multi-agent protocol)
- `docs/architecture.md` (backtest service design)
- `packages/strategies/base.py` (Strategy interface)
- `packages/strategies/sma_crossover.py` (example strategy)

**Reference:**
- `docs/data-contracts.md` (PriceBar schema)
- `services/data/models.py` (database models)
- `SPRINT_SKILL_OPTIMIZATIONS.md` (past optimizations)

**Skills:**
- `agents/skills/skills/python-patterns/`
- `agents/skills/skills/clean-code/`
- `agents/skills/skills/testing-patterns/`

---

## ✅ Sprint 3 Success Criteria

**Sprint 3 is complete when:**

- [ ] Backtest engine runs SMA Crossover strategy successfully
- [ ] P&L calculation verified (matches manual calculation)
- [ ] Reports generated (JSON + HTML)
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Architecture reviewed
- [ ] `plans/task_plan.md` marked complete

---

## 🎯 Next Steps After Sprint 3

**Sprint 4:** Dashboard & API
- FastAPI endpoints for backtest results
- Next.js dashboard to view reports
- API integration tests

**Preparation:**
- Backend Agent will use backtest results in API
- Frontend Agent will display reports in dashboard
- QA Agent will test API + dashboard integration

---

**Last Updated:** 2026-01-26  
**Sprint Status:** 🟡 Ready to Start  
**Estimated Duration:** 3 days (with multi-agent parallelization)
