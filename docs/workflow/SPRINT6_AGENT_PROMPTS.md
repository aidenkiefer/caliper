# Sprint 6 Agent Prompts with Skill Gates

**Generated:** 2026-01-26  
**Sprint:** ML Safety & Interpretability Core  
**Status:** Ready for Execution

---

## 📋 Sprint 6 Task Coverage Verification

| Task | Agent | Status |
|------|-------|--------|
| Drift Detection Service | ML | ✅ Assigned |
| Confidence Gating | ML | ✅ Assigned |
| SHAP Explainability | ML | ✅ Assigned |
| Baseline Strategies | ML | ✅ Assigned |
| HITL Controls | ML | ✅ Assigned |
| Help Page & Glossary | Frontend | ✅ Assigned |
| Tooltips | Frontend | ✅ Assigned |
| Explainability UI | Frontend | ✅ Assigned |
| HITL UI | Frontend | ✅ Assigned |
| Baseline Comparison UI | Frontend | ✅ Assigned |
| Architecture Review | Architect | ✅ Assigned |
| ADRs | Architect | ✅ Assigned |
| ML Service Tests | QA | ✅ Assigned |
| Vercel Deployment | DevOps | ✅ Assigned |
| Integration & Docs | Integrator | ✅ Assigned |

---

## 🎯 Sprint 6 Dependencies & Parallelization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SPRINT 6 PARALLEL EXECUTION PLAN                          │
└─────────────────────────────────────────────────────────────────────────────┘

START IMMEDIATELY (No Dependencies):
├── ML Agent Stream A (Drift Detection - Tasks A1-A7)
├── ML Agent Stream B (Confidence Gating - Tasks B1-B6)
├── ML Agent Stream C (SHAP Explainability - Tasks C1-C6)
├── ML Agent Stream E (Baselines & Regret - Tasks E1-E6)
├── Frontend Agent Stream F (Help Page & Tooltips - Tasks F1-F6)
├── DevOps Agent Stream I (Vercel Deployment - Tasks I1-I5)
└── Architect Agent Stream J (Reviews as work progresses)

AFTER STREAMS B & C COMPLETE:
├── ML Agent Stream D (HITL Controls - Tasks D1-D4)

AFTER ML APIs READY:
├── Frontend Agent Stream G (Explainability UI - Tasks G1-G4)
└── Frontend Agent Stream H (HITL & Baselines UI - Tasks H1-H4)

AFTER ALL SERVICES COMPLETE:
└── QA Agent Stream K (Testing - Tasks K1-K7)

FINAL:
└── Integrator Stream L (Verification & Documentation - Tasks L1-L9)
```

**Execution Order:**
1. **Phase 1:** ML (A+B+C+E), DevOps, Frontend (F), Architect start in parallel
2. **Phase 2:** ML completes Stream D (HITL) after B+C
3. **Phase 3:** Frontend completes Streams G+H after ML APIs ready
4. **Phase 4:** QA tests all services
5. **Phase 5:** Integrator verifies and documents

---

## 👤 ML Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the ML Agent for Sprint 6: ML Safety & Interpretability Core.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY CODING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills
You MUST invoke these skills before coding:

1. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: Async patterns, type hints, Pydantic models
   - Checklist:
     - [ ] Type hints on all functions
     - [ ] Pydantic models for DriftMetrics, Explanation, Recommendation
     - [ ] Async where appropriate
     - [ ] Dependency injection patterns

2. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: REST API design for ML endpoints
   - Checklist:
     - [ ] GET /v1/drift/metrics/{model_id}
     - [ ] GET /v1/drift/health/{model_id}
     - [ ] GET /v1/explanations/{trade_id}
     - [ ] GET/POST /v1/recommendations
     - [ ] Consistent response format

3. @clean-code
   - Read: agents/skills/skills/clean-code/SKILL.md
   - Purpose: Maintainable ML code
   - Checklist:
     - [ ] Small, focused functions
     - [ ] Clear naming (calculate_psi, not calc)
     - [ ] Docstrings on public methods
     - [ ] No magic numbers (use constants)

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before coding, read these documents in order:
1. plans/more-features.md (CRITICAL - full ML safety specs)
2. docs/workflow/sprint-6-multi.md (Sprint 6 task details)
3. docs/architecture.md (Current architecture)
4. agents/briefs/BACKEND.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

## Stream A: Drift Detection

A1. Create services/ml/drift skeleton:
    - __init__.py, pyproject.toml
    - README.md with usage guide

A2. Implement feature drift tracking:
    ```python
    class DriftDetector:
        def calculate_psi(self, reference: np.ndarray, current: np.ndarray) -> float:
            """Population Stability Index for feature drift."""
            ...
        
        def calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
            """KL divergence between distributions."""
            ...
        
        def calculate_mean_shift(self, reference: np.ndarray, current: np.ndarray) -> float:
            """Shift in mean measured in standard deviations."""
            ...
    ```

A3. Implement prediction confidence drift:
    - Track mean confidence over sliding window
    - Compare to baseline confidence from training
    - Alert when drift exceeds threshold

A4. Implement error drift tracking:
    - Track prediction errors when ground truth available
    - Compare error distribution to baseline
    - Use for delayed feedback scenarios

A5. Implement threshold-based alerts:
    ```python
    class DriftAlert:
        def check_thresholds(self, metrics: DriftMetrics) -> List[Alert]:
            # PSI > 0.1 = WARNING, > 0.25 = CRITICAL
            # KL > 0.1 = WARNING, > 0.2 = CRITICAL
            ...
    ```

A6. Implement model health score:
    ```python
    class HealthScore:
        def calculate(self, drift_metrics: DriftMetrics) -> float:
            """
            Returns 0-100 score.
            Components:
            - Feature drift (30%)
            - Confidence drift (30%)
            - Error drift (20%)
            - Staleness (20%)
            """
            ...
    ```

A7. Create drift metrics API:
    - GET /v1/drift/metrics/{model_id} - Returns all drift metrics
    - GET /v1/drift/health/{model_id} - Returns health score
    - Store metrics in database for historical queries

## Stream B: Confidence Gating

B1. Extend model output schema:
    ```python
    class ModelOutput(BaseModel):
        signal: Literal["BUY", "SELL", "ABSTAIN"]
        confidence: float  # 0.0 to 1.0
        uncertainty: float  # entropy measure
        features_used: List[str]
    ```

B2. Implement configurable confidence thresholds:
    ```python
    class ConfidenceConfig(BaseModel):
        strategy_id: str
        abstain_threshold: float = 0.55
        low_confidence_threshold: float = 0.65
        high_confidence_threshold: float = 0.85
    ```

B3. Implement uncertainty measures:
    - Entropy calculation from prediction probabilities
    - Standard deviation of ensemble predictions
    - Distance from decision boundary (if applicable)

B4. Implement ensemble disagreement:
    - Track variance across ensemble members
    - Flag when ensemble is highly divided
    - Use as additional abstention signal

B5. Update backtest engine for abstentions:
    - Track abstention rate per strategy
    - Calculate metrics excluding abstained periods
    - Report "opportunity cost" of abstentions

B6. Create confidence gating API:
    - GET /v1/confidence/config/{strategy_id}
    - PUT /v1/confidence/config/{strategy_id}

## Stream C: Explainability (SHAP)

C1. Create services/ml/explainability skeleton:
    - __init__.py, pyproject.toml
    - README.md with usage guide

C2. Implement SHAP for tree-based models:
    ```python
    import shap
    
    class ShapExplainer:
        def __init__(self, model):
            self.explainer = shap.TreeExplainer(model)
        
        def explain(self, X: pd.DataFrame) -> ShapExplanation:
            shap_values = self.explainer.shap_values(X)
            return ShapExplanation(
                base_value=self.explainer.expected_value,
                shap_values=shap_values,
                feature_names=X.columns.tolist()
            )
    ```

C3. Implement permutation importance fallback:
    - For models without native SHAP support
    - sklearn.inspection.permutation_importance

C4. Define explanation payload:
    ```python
    class TradeExplanation(BaseModel):
        trade_id: str
        timestamp: datetime
        signal: str
        confidence: float
        top_features: List[FeatureContribution]
        model_id: str
        
    class FeatureContribution(BaseModel):
        feature_name: str
        value: float  # actual feature value
        contribution: float  # SHAP value
        direction: Literal["positive", "negative"]
    ```

C5. Store explanations with trades:
    - Link explanation to trade_id
    - Store in database for historical queries
    - Enable explanation retrieval via API

C6. Create explanation API:
    - GET /v1/explanations/{trade_id}
    - GET /v1/explanations?strategy_id=X&limit=10

## Stream D: Human-in-the-Loop (after B & C)

D1. Add approval flag to execution pipeline:
    ```python
    class ExecutionConfig(BaseModel):
        require_approval: bool = False
        auto_approve_confidence: float = 0.85  # auto-approve high confidence
    ```

D2. Implement recommendation queue:
    ```python
    class RecommendationQueue:
        def add(self, recommendation: Recommendation) -> str:
            """Add to queue, return recommendation_id"""
            ...
        
        def approve(self, recommendation_id: str, user_id: str) -> None:
            """Human approves recommendation"""
            ...
        
        def reject(self, recommendation_id: str, user_id: str, reason: str) -> None:
            """Human rejects recommendation"""
            ...
        
        def get_pending(self) -> List[Recommendation]:
            """Get all pending recommendations"""
            ...
    ```

D3. Log human vs model decisions:
    - Track when human agrees/disagrees with model
    - Calculate agreement rate
    - Analyze disagreement patterns

D4. Create HITL API:
    - GET /v1/recommendations (pending queue)
    - POST /v1/recommendations/{id}/approve
    - POST /v1/recommendations/{id}/reject
    - GET /v1/recommendations/stats (agreement metrics)

## Stream E: Baselines & Regret

E1. Implement hold cash baseline:
    ```python
    class HoldCashBaseline(BaselineStrategy):
        def run(self, period: DateRange) -> BacktestResult:
            # Simply hold cash, return 0% (or risk-free rate)
            ...
    ```

E2. Implement buy & hold baseline:
    ```python
    class BuyAndHoldBaseline(BaselineStrategy):
        def __init__(self, symbol: str = "SPY"):
            self.symbol = symbol
        
        def run(self, period: DateRange) -> BacktestResult:
            # Buy at start, hold until end
            ...
    ```

E3. Implement random baseline:
    ```python
    class RandomControlledBaseline(BaselineStrategy):
        def run(self, period: DateRange, seed: int = 42) -> BacktestResult:
            # Random trades with same risk controls as main strategy
            # Demonstrates value-add of actual strategy
            ...
    ```

E4. Implement regret calculation:
    ```python
    class RegretCalculator:
        def calculate(
            self, 
            strategy_result: BacktestResult,
            baseline_results: Dict[str, BacktestResult]
        ) -> RegretMetrics:
            """
            Regret = Strategy Return - Best Baseline Return
            """
            ...
    ```

E5. Track regret over time:
    - Rolling 30-day regret
    - Cumulative regret
    - Store for historical analysis

E6. Create regret API:
    - GET /v1/baselines/comparison?strategy_id=X
    - Returns strategy vs all baselines

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ services/ml/**
✅ services/api/routers/drift.py (new)
✅ services/api/routers/explanations.py (new)
✅ services/api/routers/recommendations.py (new)
✅ services/backtest/abstention.py (update)
✅ packages/common/ml_schemas.py (new)

You MUST NOT touch:
❌ apps/dashboard/** (Frontend Agent)
❌ vercel.json (DevOps Agent)
❌ tests/** (QA Agent)
❌ docs/architecture.md (Architect Agent)
❌ adr/** (Architect Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Before marking complete, verify:

Drift Detection:
- [ ] PSI and KL divergence calculated correctly
- [ ] Threshold alerts trigger at correct levels
- [ ] Health score returns 0-100
- [ ] Metrics queryable via API per model

Confidence Gating:
- [ ] ABSTAIN signal supported in output
- [ ] Configurable thresholds per strategy
- [ ] Backtest handles abstentions correctly

Explainability:
- [ ] SHAP explanations for tree models
- [ ] Top features identified with direction
- [ ] Explanations stored with trades

HITL:
- [ ] Approval queue functional
- [ ] Human approve/reject logged
- [ ] Agreement stats available

Baselines:
- [ ] 3 baseline strategies implemented
- [ ] Regret calculated vs baselines
- [ ] API returns comparison data

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. List of files created/modified
2. Summary of drift detection thresholds implemented
3. Summary of confidence thresholds
4. Example API calls:
   - Get drift metrics
   - Get explanation
   - Approve recommendation
   - Get baseline comparison
5. Any assumptions or decisions made
6. Known limitations or TODOs

═══════════════════════════════════════════════════════════════
```

---

## 👤 Frontend Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Frontend Agent for Sprint 6: ML Safety & Interpretability Core.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY CODING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills
You MUST invoke these skills before coding:

1. @nextjs-best-practices
   - Read: agents/skills/skills/nextjs-best-practices/SKILL.md
   - Purpose: App Router, Server Components, data fetching
   - Checklist:
     - [ ] Use App Router conventions
     - [ ] Server Components where appropriate
     - [ ] Proper loading/error states

2. @react-patterns
   - Read: agents/skills/skills/react-patterns/SKILL.md
   - Purpose: Component patterns, hooks, state management
   - Checklist:
     - [ ] Small, focused components
     - [ ] Custom hooks for shared logic
     - [ ] Proper TypeScript typing

3. @tailwind-patterns
   - Read: agents/skills/skills/tailwind-patterns/SKILL.md
   - Purpose: Consistent styling
   - Checklist:
     - [ ] Follow existing design system
     - [ ] Dark mode compatible
     - [ ] Responsive design

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before coding, read these documents in order:
1. docs/dashboard-spec.md (CRITICAL - Help page & tooltip specs)
2. docs/workflow/sprint-6-multi.md (Sprint 6 task details)
3. apps/dashboard/README.md (Dashboard structure)
4. agents/briefs/FRONTEND.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

## Stream F: Help Page & Tooltips (Start Immediately)

F1. Create glossary data file:
    ```typescript
    // apps/dashboard/lib/glossary.ts
    
    export interface GlossaryTerm {
      term: string;
      definition: string;
      category: 'performance' | 'risk' | 'position' | 'strategy';
      example?: string;
    }
    
    export const glossaryTerms: GlossaryTerm[] = [
      {
        term: "P&L",
        definition: "Profit and Loss - the money made or lost on trades",
        category: "performance",
        example: "+$450 means you made $450"
      },
      {
        term: "Sharpe Ratio",
        definition: "Risk-adjusted return metric. Higher = better risk-adjusted performance. >1 is good, >2 is excellent",
        category: "performance"
      },
      {
        term: "Max Drawdown",
        definition: "Largest peak-to-trough decline in portfolio value. Measures worst-case loss",
        category: "risk",
        example: "-15% means at worst you were down 15% from peak"
      },
      {
        term: "Win Rate",
        definition: "Percentage of trades that were profitable",
        category: "performance"
      },
      {
        term: "Profit Factor",
        definition: "Gross profit / gross loss. >1 means profitable overall",
        category: "performance"
      },
      {
        term: "Drawdown",
        definition: "Current decline from the portfolio's peak value",
        category: "risk"
      },
      {
        term: "Long",
        definition: "Buying an asset expecting price to rise",
        category: "position"
      },
      {
        term: "Short",
        definition: "Selling borrowed asset expecting price to fall",
        category: "position"
      },
      {
        term: "Entry Price",
        definition: "The price at which a position was opened",
        category: "position"
      },
      {
        term: "Mark Price",
        definition: "Current market price of the asset",
        category: "position"
      },
      {
        term: "Unrealized P&L",
        definition: "Profit or loss on open positions that haven't been closed yet",
        category: "position"
      },
      {
        term: "Stop Loss",
        definition: "A price level that triggers automatic sell to limit losses",
        category: "risk"
      },
      {
        term: "Take Profit",
        definition: "A price level that triggers automatic sell to lock in gains",
        category: "risk"
      },
      {
        term: "Backtest",
        definition: "Testing a trading strategy on historical data to see how it would have performed",
        category: "strategy"
      },
      {
        term: "Paper Trading",
        definition: "Simulated trading with fake money to test strategies without risk",
        category: "strategy"
      },
      {
        term: "Live Trading",
        definition: "Trading with real money in live markets",
        category: "strategy"
      },
      {
        term: "Signal",
        definition: "A recommendation from the model to BUY, SELL, or HOLD",
        category: "strategy"
      },
      {
        term: "ABSTAIN",
        definition: "When the model chooses not to trade due to low confidence",
        category: "strategy"
      },
      {
        term: "Confidence",
        definition: "How certain the model is about its prediction (0-100%)",
        category: "strategy"
      },
      {
        term: "Model Drift",
        definition: "When a model's performance degrades because market conditions have changed",
        category: "strategy"
      },
      {
        term: "SHAP",
        definition: "A method to explain which features most influenced a model's prediction",
        category: "strategy"
      }
    ];
    
    export function getTermsByCategory(category: string): GlossaryTerm[] {
      return glossaryTerms.filter(t => t.category === category);
    }
    
    export function searchTerms(query: string): GlossaryTerm[] {
      const lower = query.toLowerCase();
      return glossaryTerms.filter(t => 
        t.term.toLowerCase().includes(lower) ||
        t.definition.toLowerCase().includes(lower)
      );
    }
    ```

F2. Create tooltip wrapper component:
    ```typescript
    // apps/dashboard/components/ui/tooltip-wrapper.tsx
    
    import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
    import { HelpCircle } from "lucide-react";
    import { glossaryTerms } from "@/lib/glossary";
    import Link from "next/link";
    
    interface TooltipWrapperProps {
      term: string;
      children?: React.ReactNode;
      showIcon?: boolean;
    }
    
    export function TooltipWrapper({ term, children, showIcon = true }: TooltipWrapperProps) {
      const glossaryEntry = glossaryTerms.find(
        t => t.term.toLowerCase() === term.toLowerCase()
      );
      
      if (!glossaryEntry) {
        return <>{children || term}</>;
      }
      
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex items-center gap-1 cursor-help">
                {children || term}
                {showIcon && (
                  <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                )}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">{glossaryEntry.definition}</p>
              {glossaryEntry.example && (
                <p className="text-xs text-muted-foreground mt-1">
                  Example: {glossaryEntry.example}
                </p>
              )}
              <Link 
                href="/help" 
                className="text-xs text-primary hover:underline mt-2 block"
              >
                Learn more →
              </Link>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }
    ```

F3. Add tooltips to StatsCard:
    - Update StatsCard component to use TooltipWrapper
    - Add tooltips to: P&L, Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor

F4. Add tooltips to table headers:
    - Strategies table headers
    - Positions table headers
    - Runs table headers

F5. Build Help page:
    ```typescript
    // apps/dashboard/app/(dashboard)/help/page.tsx
    
    'use client';
    
    import { useState } from 'react';
    import { Input } from '@/components/ui/input';
    import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
    import { glossaryTerms, getTermsByCategory, searchTerms, GlossaryTerm } from '@/lib/glossary';
    import { Search } from 'lucide-react';
    
    const categories = [
      { id: 'performance', label: 'Performance Metrics', icon: '📊' },
      { id: 'risk', label: 'Risk Metrics', icon: '⚠️' },
      { id: 'position', label: 'Position Terms', icon: '📈' },
      { id: 'strategy', label: 'Strategy Terms', icon: '🤖' },
    ];
    
    export default function HelpPage() {
      const [searchQuery, setSearchQuery] = useState('');
      
      const displayTerms = searchQuery 
        ? searchTerms(searchQuery)
        : glossaryTerms;
      
      return (
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Help & Glossary</h1>
            <p className="text-muted-foreground mt-2">
              Learn about trading terminology and platform features
            </p>
          </div>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search terms..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          {/* Results */}
          {searchQuery ? (
            <Card>
              <CardHeader>
                <CardTitle>Search Results ({displayTerms.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <TermList terms={displayTerms} />
              </CardContent>
            </Card>
          ) : (
            /* Category Sections */
            <div className="grid gap-6">
              {categories.map(category => (
                <Card key={category.id}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <span>{category.icon}</span>
                      {category.label}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TermList terms={getTermsByCategory(category.id)} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      );
    }
    
    function TermList({ terms }: { terms: GlossaryTerm[] }) {
      return (
        <div className="space-y-4">
          {terms.map(term => (
            <div key={term.term} className="border-b pb-4 last:border-0">
              <dt className="font-semibold text-foreground">{term.term}</dt>
              <dd className="text-muted-foreground mt-1">{term.definition}</dd>
              {term.example && (
                <dd className="text-sm text-muted-foreground mt-1 italic">
                  Example: {term.example}
                </dd>
              )}
            </div>
          ))}
        </div>
      );
    }
    ```

F6. Add Help link to sidebar:
    - Add `?` icon or "Help" link to sidebar navigation
    - Link to /help page

## Stream G: Explainability UI (After ML API C6 ready)

G1. Create trade explanation component:
    ```typescript
    // apps/dashboard/components/explanation-card.tsx
    
    import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
    import { Badge } from '@/components/ui/badge';
    import { TooltipWrapper } from '@/components/ui/tooltip-wrapper';
    
    interface FeatureContribution {
      feature_name: string;
      value: number;
      contribution: number;
      direction: 'positive' | 'negative';
    }
    
    interface ExplanationCardProps {
      tradeId: string;
      signal: 'BUY' | 'SELL' | 'ABSTAIN';
      confidence: number;
      topFeatures: FeatureContribution[];
    }
    
    export function ExplanationCard({ 
      tradeId, 
      signal, 
      confidence, 
      topFeatures 
    }: ExplanationCardProps) {
      const signalColor = {
        BUY: 'bg-emerald-500',
        SELL: 'bg-red-500',
        ABSTAIN: 'bg-yellow-500'
      };
      
      return (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">
              <TooltipWrapper term="SHAP">Trade Explanation</TooltipWrapper>
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge className={signalColor[signal]}>{signal}</Badge>
              <TooltipWrapper term="Confidence">
                <span className="text-sm text-muted-foreground">
                  {(confidence * 100).toFixed(1)}% confident
                </span>
              </TooltipWrapper>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Key factors influencing this recommendation:
            </p>
            <div className="space-y-3">
              {topFeatures.map((feature, idx) => (
                <FeatureRow key={idx} feature={feature} />
              ))}
            </div>
          </CardContent>
        </Card>
      );
    }
    
    function FeatureRow({ feature }: { feature: FeatureContribution }) {
      const isPositive = feature.direction === 'positive';
      return (
        <div className="flex items-center justify-between">
          <span className="text-sm">{feature.feature_name}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Value: {feature.value.toFixed(2)}
            </span>
            <span className={`text-sm font-medium ${
              isPositive ? 'text-emerald-500' : 'text-red-500'
            }`}>
              {isPositive ? '↑' : '↓'} {Math.abs(feature.contribution).toFixed(3)}
            </span>
          </div>
        </div>
      );
    }
    ```

G2. Add explanation view to strategy detail page:
    - Show explanation for recent recommendations
    - Link from recommendation to full explanation

G3. Create feature importance chart:
    - Bar chart showing SHAP values
    - Color-coded positive/negative
    - Use Recharts BarChart

G4. Add confidence indicator:
    - Visual confidence meter
    - Color gradient (red → yellow → green)
    - Show alongside recommendations

## Stream H: HITL & Baselines UI (After ML APIs D4 & E6 ready)

H1. Create approval queue UI:
    ```typescript
    // apps/dashboard/components/approval-queue.tsx
    
    import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
    import { Button } from '@/components/ui/button';
    import { Badge } from '@/components/ui/badge';
    import { Check, X, Clock } from 'lucide-react';
    
    interface Recommendation {
      id: string;
      strategy: string;
      signal: 'BUY' | 'SELL';
      symbol: string;
      confidence: number;
      timestamp: string;
    }
    
    interface ApprovalQueueProps {
      recommendations: Recommendation[];
      onApprove: (id: string) => void;
      onReject: (id: string) => void;
    }
    
    export function ApprovalQueue({ 
      recommendations, 
      onApprove, 
      onReject 
    }: ApprovalQueueProps) {
      return (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Pending Approvals
            </CardTitle>
            <Badge variant="outline">{recommendations.length} pending</Badge>
          </CardHeader>
          <CardContent>
            {recommendations.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                No pending recommendations
              </p>
            ) : (
              <div className="space-y-4">
                {recommendations.map(rec => (
                  <div 
                    key={rec.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant={rec.signal === 'BUY' ? 'default' : 'destructive'}>
                          {rec.signal}
                        </Badge>
                        <span className="font-medium">{rec.symbol}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {rec.strategy} • {(rec.confidence * 100).toFixed(0)}% confidence
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => onReject(rec.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                      <Button 
                        size="sm"
                        onClick={() => onApprove(rec.id)}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      );
    }
    ```

H2. Create manual override controls:
    - Override button on active recommendations
    - Reason input for overrides
    - Confirmation modal

H3. Create baseline comparison widget:
    - Show strategy vs baselines (cash, buy & hold, random)
    - Use bar chart or line chart
    - Color-code winning/losing vs baseline

H4. Add "vs baseline" toggle to charts:
    - Toggle on equity curve chart
    - Overlay baseline performance
    - Show regret metric

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ apps/dashboard/lib/glossary.ts (new)
✅ apps/dashboard/components/ui/tooltip-wrapper.tsx (new)
✅ apps/dashboard/components/stats-card.tsx (update)
✅ apps/dashboard/app/(dashboard)/help/page.tsx (new)
✅ apps/dashboard/components/explanation-card.tsx (new)
✅ apps/dashboard/components/feature-importance-chart.tsx (new)
✅ apps/dashboard/components/approval-queue.tsx (new)
✅ apps/dashboard/components/baseline-comparison.tsx (new)
✅ apps/dashboard/components/layout/* (update sidebar)

You MUST NOT touch:
❌ services/**/*.py (ML/Backend Agent)
❌ vercel.json (DevOps Agent)
❌ tests/**/*.py (QA Agent)
❌ docs/architecture.md (Architect Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Stream F (Help & Tooltips):
- [ ] glossary.ts has all terms from dashboard-spec.md
- [ ] TooltipWrapper component works with glossary
- [ ] StatsCard shows tooltips on hover
- [ ] Table headers have tooltips
- [ ] Help page renders with search functionality
- [ ] Sidebar has link to Help page

Stream G (Explainability UI):
- [ ] ExplanationCard shows signal, confidence, features
- [ ] Feature importance chart renders correctly
- [ ] Strategy detail page shows explanations

Stream H (HITL & Baselines UI):
- [ ] Approval queue shows pending recommendations
- [ ] Approve/reject buttons work
- [ ] Baseline comparison chart renders
- [ ] "vs baseline" toggle works on equity chart

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. List of files created/modified
2. Screenshots or descriptions of new UI components
3. Glossary terms count
4. Any design decisions made
5. Known limitations or TODOs

═══════════════════════════════════════════════════════════════
```

---

## 👤 Architect Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Architect Agent for Sprint 6: ML Safety & Interpretability Core.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: Validate ML API design
   - Checklist:
     - [ ] Drift/explanation endpoints follow conventions
     - [ ] Error responses consistent
     - [ ] Authentication documented

2. @software-architecture
   - Read: agents/skills/skills/software-architecture/SKILL.md
   - Purpose: ML safety system design
   - Checklist:
     - [ ] Drift detection flow clear
     - [ ] Explainability integration documented
     - [ ] HITL control flow defined

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

1. docs/workflow/sprint-6-multi.md (Sprint 6 details)
2. plans/more-features.md (ML safety feature specs)
3. docs/architecture.md (Current architecture)
4. agents/briefs/ARCHITECT.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

J1. Review drift detection architecture:
    - Verify drift metrics flow from models to storage to API
    - Ensure alert thresholds are configurable
    - Check health score calculation is reasonable

J2. Review explainability integration:
    - Verify SHAP integration with model inference
    - Check explanation storage and retrieval
    - Ensure explanations link to trades

J3. Review HITL control flow:
    - Verify approval queue integrates with execution
    - Check human decision logging
    - Ensure override mechanism is safe

J4. Update docs/architecture.md with ML Safety sections:
    Add these sections:
    
    ### 8. ML Safety & Interpretability
    
    #### 8.1 Drift Detection Flow
    ```mermaid
    flowchart TD
        subgraph Inference
            A[Model Prediction] --> B[Feature Values]
            A --> C[Confidence Score]
        end
        
        subgraph Drift Monitor
            B --> D[Calculate PSI]
            B --> E[Calculate KL Div]
            C --> F[Confidence Drift]
        end
        
        D --> G[Drift Metrics Store]
        E --> G
        F --> G
        
        G --> H{Threshold Check}
        H -->|Exceeded| I[Alert]
        H -->|OK| J[Log Only]
        
        G --> K[Health Score Calc]
        K --> L[Model Health: 0-100]
    ```
    
    #### 8.2 Explainability Pipeline
    ```mermaid
    sequenceDiagram
        participant Model
        participant Explainer
        participant Store
        participant API
        participant Dashboard
        
        Model->>Explainer: Prediction + Features
        Explainer->>Explainer: SHAP TreeExplainer
        Explainer->>Store: Explanation Payload
        Dashboard->>API: GET /explanations/{trade_id}
        API->>Store: Query
        Store->>API: Explanation
        API->>Dashboard: Top Features + Contributions
    ```
    
    #### 8.3 Human-in-the-Loop Flow
    ```mermaid
    stateDiagram-v2
        [*] --> Generated: Model generates recommendation
        Generated --> Pending: HITL enabled
        Generated --> Executed: HITL disabled (auto-execute)
        Pending --> Approved: Human approves
        Pending --> Rejected: Human rejects
        Approved --> Executed: Execute trade
        Rejected --> Logged: Log disagreement
        Executed --> [*]
        Logged --> [*]
    ```
    
    #### 8.4 Confidence Gating
    ```mermaid
    flowchart TD
        A[Model Output] --> B{Confidence}
        B -->|< 55%| C[ABSTAIN]
        B -->|55-65%| D[LOW_CONFIDENCE]
        B -->|65-85%| E[NORMAL]
        B -->|> 85%| F[HIGH_CONFIDENCE]
        
        C --> G[Skip Trade]
        D --> H[Require Approval]
        E --> I[Execute or Queue]
        F --> J[Auto-Execute]
    ```

J5. Create ADR-0008 for ML Explainability:
    - Decision: Use SHAP for tree-based models
    - Alternatives: LIME, attention weights, feature ablation
    - Trade-offs: Performance vs interpretability
    - Decision: Store explanations with trades

J6. Create ADR-0009 for Drift Detection:
    - Decision: PSI and KL divergence for feature drift
    - Decision: Threshold-based alerting (0.1 warning, 0.25 critical)
    - Decision: Composite health score (0-100)
    - Trade-offs: Sensitivity vs false alarms

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ docs/architecture.md (update ML safety sections)
✅ adr/0008-ml-explainability.md (new)
✅ adr/0009-drift-detection.md (new)

You MUST NOT touch:
❌ services/**/*.py (ML/Backend Agent)
❌ apps/dashboard/** (Frontend Agent)
❌ tests/** (QA Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

- [ ] docs/architecture.md has ML Safety section with all diagrams
- [ ] Drift detection flow documented
- [ ] Explainability pipeline documented
- [ ] HITL control flow documented
- [ ] ADR-0008 created with SHAP decision
- [ ] ADR-0009 created with drift detection decisions
- [ ] All diagrams use Mermaid (consistent with existing)

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. Summary of architecture updates
2. Key diagrams added
3. ADR decisions summary
4. Any concerns or recommendations for ML Agent
5. Suggested improvements for future sprints

═══════════════════════════════════════════════════════════════
```

---

## 👤 QA Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the QA Agent for Sprint 6: ML Safety & Interpretability Core.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY TESTING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @testing-patterns
   - Read: agents/skills/skills/testing-patterns/SKILL.md
   - Purpose: TDD, test structure, mocking
   - Checklist:
     - [ ] Arrange-Act-Assert pattern
     - [ ] Factory functions for ML test data
     - [ ] Mocks for expensive ML operations

2. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: pytest fixtures, async testing
   - Checklist:
     - [ ] Fixtures for drift metrics
     - [ ] Fixtures for SHAP explainer
     - [ ] TestClient for API testing

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

1. docs/workflow/sprint-6-multi.md (Sprint 6 details and acceptance criteria)
2. plans/more-features.md (ML safety feature specs)
3. agents/briefs/QA.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

K1. Write drift detection unit tests (20 tests):

    ```python
    # tests/unit/test_drift_detection.py
    
    class TestPSICalculation:
        def test_psi_identical_distributions_returns_zero(self):
            """PSI of identical distributions should be 0."""
            ...
        
        def test_psi_slightly_different_returns_small_value(self):
            """Slightly different distributions have PSI < 0.1."""
            ...
        
        def test_psi_significantly_different_returns_high_value(self):
            """Very different distributions have PSI > 0.25."""
            ...
    
    class TestKLDivergence:
        def test_kl_identical_distributions(self):
            ...
        
        def test_kl_divergence_asymmetry(self):
            """KL(P||Q) != KL(Q||P)"""
            ...
    
    class TestHealthScore:
        def test_healthy_model_scores_above_80(self):
            ...
        
        def test_drifted_model_scores_below_50(self):
            ...
        
        def test_health_score_in_valid_range(self):
            """Score always between 0 and 100."""
            ...
    
    class TestDriftAlerts:
        def test_warning_alert_at_psi_0_1(self):
            ...
        
        def test_critical_alert_at_psi_0_25(self):
            ...
    ```

K2. Write confidence gating unit tests (15 tests):

    ```python
    # tests/unit/test_confidence_gating.py
    
    class TestConfidenceThresholds:
        def test_abstain_below_threshold(self):
            """Confidence < 0.55 should ABSTAIN."""
            ...
        
        def test_low_confidence_band(self):
            """Confidence 0.55-0.65 is LOW_CONFIDENCE."""
            ...
        
        def test_normal_confidence_band(self):
            """Confidence 0.65-0.85 is NORMAL."""
            ...
        
        def test_high_confidence_band(self):
            """Confidence > 0.85 is HIGH_CONFIDENCE."""
            ...
    
    class TestUncertaintyMeasures:
        def test_entropy_calculation(self):
            ...
        
        def test_ensemble_disagreement(self):
            ...
    
    class TestBacktestAbstention:
        def test_abstention_tracked_in_backtest(self):
            ...
        
        def test_metrics_exclude_abstained_periods(self):
            ...
    ```

K3. Write explainability unit tests (15 tests):

    ```python
    # tests/unit/test_explainability.py
    
    class TestShapExplainer:
        def test_shap_returns_feature_contributions(self):
            ...
        
        def test_shap_contributions_sum_to_prediction(self):
            """SHAP values should sum to prediction - base value."""
            ...
        
        def test_top_features_sorted_by_importance(self):
            ...
    
    class TestPermutationImportance:
        def test_permutation_fallback_works(self):
            ...
    
    class TestExplanationPayload:
        def test_explanation_has_required_fields(self):
            ...
        
        def test_explanation_stored_with_trade(self):
            ...
        
        def test_explanation_retrieved_by_trade_id(self):
            ...
    ```

K4. Write baseline strategy unit tests (10 tests):

    ```python
    # tests/unit/test_baselines.py
    
    class TestHoldCashBaseline:
        def test_hold_cash_returns_zero(self):
            """Hold cash strategy returns 0% (ignoring risk-free rate)."""
            ...
    
    class TestBuyAndHoldBaseline:
        def test_buy_and_hold_matches_market(self):
            ...
    
    class TestRandomBaseline:
        def test_random_baseline_respects_risk_controls(self):
            ...
        
        def test_random_baseline_reproducible_with_seed(self):
            ...
    
    class TestRegretCalculation:
        def test_positive_regret_when_worse_than_baseline(self):
            ...
        
        def test_negative_regret_when_better_than_baseline(self):
            ...
    ```

K5. Write HITL integration tests (10 tests):

    ```python
    # tests/integration/test_hitl_workflow.py
    
    class TestApprovalQueue:
        def test_recommendation_added_to_queue(self):
            ...
        
        def test_approve_recommendation(self):
            ...
        
        def test_reject_recommendation(self):
            ...
        
        def test_pending_recommendations_returned(self):
            ...
    
    class TestHumanLogging:
        def test_approval_logged_correctly(self):
            ...
        
        def test_rejection_logged_with_reason(self):
            ...
        
        def test_agreement_stats_calculated(self):
            ...
    ```

K6. Write Help page E2E tests (5 tests):

    ```python
    # tests/e2e/test_help_page.py
    
    # Note: Use Playwright or similar E2E framework
    
    class TestHelpPage:
        def test_help_page_loads(self):
            ...
        
        def test_search_filters_terms(self):
            ...
        
        def test_categories_display_correctly(self):
            ...
        
        def test_tooltip_wrapper_shows_definition(self):
            ...
    ```

K7. Create ML safety verification runbook:

    ```markdown
    # ML Safety Verification Runbook
    
    ## Drift Detection Verification
    
    1. Check drift metrics endpoint:
       curl http://localhost:8000/v1/drift/metrics/model-1
       
       Expected: PSI, KL divergence, mean shift values
    
    2. Check health score:
       curl http://localhost:8000/v1/drift/health/model-1
       
       Expected: Score 0-100, component breakdown
    
    3. Trigger alert (if drift simulation available):
       - Inject drifted data
       - Verify alert generated
    
    ## Confidence Gating Verification
    
    1. Test ABSTAIN decision:
       - Submit prediction with confidence < 0.55
       - Verify signal = ABSTAIN
    
    2. Test threshold configuration:
       curl -X PUT http://localhost:8000/v1/confidence/config/strategy-1 \
         -d '{"abstain_threshold": 0.60}'
    
    ## Explainability Verification
    
    1. Get trade explanation:
       curl http://localhost:8000/v1/explanations/trade-123
       
       Expected: Top features, contributions, confidence
    
    2. Verify explanation links to trade
    
    ## HITL Verification
    
    1. Check pending queue:
       curl http://localhost:8000/v1/recommendations
    
    2. Approve recommendation:
       curl -X POST http://localhost:8000/v1/recommendations/rec-1/approve
    
    3. Verify trade executed after approval
    
    ## Baseline Verification
    
    1. Get baseline comparison:
       curl http://localhost:8000/v1/baselines/comparison?strategy_id=strategy-1
       
       Expected: Strategy return vs cash, buy & hold, random
    ```

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ tests/unit/test_drift_detection.py
✅ tests/unit/test_confidence_gating.py
✅ tests/unit/test_explainability.py
✅ tests/unit/test_baselines.py
✅ tests/integration/test_hitl_workflow.py
✅ tests/e2e/test_help_page.py
✅ tests/fixtures/ml_data.py
✅ docs/runbooks/ml-safety-verification.md

You MUST NOT touch:
❌ services/**/*.py (ML/Backend Agent)
❌ apps/dashboard/** (Frontend Agent)
❌ docs/architecture.md (Architect Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

- [ ] 60+ unit tests written and passing
- [ ] 10+ integration tests written and passing
- [ ] All drift thresholds tested
- [ ] Confidence gating boundaries tested
- [ ] SHAP explanation format validated
- [ ] HITL approval workflow tested
- [ ] Help page renders correctly
- [ ] Verification runbook created

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. Test summary: X unit tests, Y integration tests
2. Coverage of ML safety features (checklist)
3. Sample test output
4. Verification runbook location
5. Any edge cases not covered

═══════════════════════════════════════════════════════════════
```

---

## 👤 DevOps Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the DevOps Agent for Sprint 6: ML Safety & Interpretability Core.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @vercel-deployment
   - Read: agents/skills/skills/vercel-deployment/SKILL.md
   - Purpose: Vercel configuration, env vars, routing
   - Checklist:
     - [ ] vercel.json configured
     - [ ] Environment variables set
     - [ ] API rewrites to FastAPI
     - [ ] Production/preview environments

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

1. docs/dashboard-spec.md (Vercel deployment requirements)
2. docs/workflow/sprint-6-multi.md (Sprint 6 details)
3. apps/dashboard/README.md (Dashboard structure)
4. agents/briefs/DEVOPS.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

I1. Create vercel.json:
    ```json
    // apps/dashboard/vercel.json
    {
      "$schema": "https://openapi.vercel.sh/vercel.json",
      "framework": "nextjs",
      "buildCommand": "npm run build",
      "devCommand": "npm run dev",
      "installCommand": "npm install",
      "outputDirectory": ".next",
      "regions": ["iad1"],
      "rewrites": [
        {
          "source": "/api/:path*",
          "destination": "https://your-fastapi-backend.com/v1/:path*"
        }
      ],
      "headers": [
        {
          "source": "/(.*)",
          "headers": [
            {
              "key": "X-Content-Type-Options",
              "value": "nosniff"
            },
            {
              "key": "X-Frame-Options",
              "value": "DENY"
            },
            {
              "key": "X-XSS-Protection",
              "value": "1; mode=block"
            }
          ]
        }
      ]
    }
    ```

I2. Configure environment variables:
    Update apps/dashboard/.env.example:
    ```env
    # API Configuration
    NEXT_PUBLIC_API_URL=http://localhost:8000
    
    # Authentication (NextAuth)
    NEXTAUTH_URL=http://localhost:3000
    NEXTAUTH_SECRET=your-secret-key-here
    
    # For Vercel Production
    # NEXT_PUBLIC_API_URL=https://your-api-domain.com
    # NEXTAUTH_URL=https://your-dashboard-domain.vercel.app
    ```
    
    Document required Vercel environment variables:
    - `NEXT_PUBLIC_API_URL` - FastAPI backend URL
    - `NEXTAUTH_URL` - Dashboard URL (auto-set by Vercel)
    - `NEXTAUTH_SECRET` - Random secret for sessions

I3. Set up API rewrites:
    - Configure rewrites in vercel.json (see I1)
    - Update next.config.js if needed:
    ```javascript
    /** @type {import('next').NextConfig} */
    const nextConfig = {
      async rewrites() {
        return [
          {
            source: '/api/:path*',
            destination: `${process.env.NEXT_PUBLIC_API_URL}/v1/:path*`,
          },
        ];
      },
    };
    
    module.exports = nextConfig;
    ```

I4. Configure production and preview environments:
    Document in runbook:
    - Production: main branch auto-deploy
    - Preview: PR branches get preview URLs
    - Environment variable scoping (production vs preview)

I5. Create deployment runbook:
    ```markdown
    # Vercel Deployment Runbook
    
    ## Prerequisites
    
    - Vercel account
    - GitHub repo connected to Vercel
    - Environment variables configured
    
    ## Initial Setup
    
    1. Connect Repository:
       - Go to Vercel dashboard
       - Import Git Repository
       - Select the quant repo
       - Set root directory to `apps/dashboard`
    
    2. Configure Environment Variables:
       In Vercel project settings:
       - NEXT_PUBLIC_API_URL = https://your-api.com
       - NEXTAUTH_SECRET = [generate with: openssl rand -base64 32]
    
    3. Deploy:
       - Push to main branch
       - Vercel auto-deploys
    
    ## Deployment Workflow
    
    ### Production Deployment
    1. Merge PR to main
    2. Vercel automatically deploys
    3. Monitor build logs in Vercel dashboard
    4. Verify at production URL
    
    ### Preview Deployment
    1. Create PR
    2. Vercel creates preview URL
    3. Test changes at preview URL
    4. Merge when ready
    
    ## Troubleshooting
    
    ### Build Fails
    - Check build logs in Vercel
    - Common issues:
      - Missing dependencies: Update package.json
      - TypeScript errors: Fix type issues
      - Environment variables: Verify all are set
    
    ### API Connection Issues
    - Verify NEXT_PUBLIC_API_URL is correct
    - Check API CORS settings include Vercel domains
    - Verify rewrites in vercel.json
    
    ### Environment Variables Not Working
    - NEXT_PUBLIC_ prefix required for client-side vars
    - Redeploy after changing env vars
    - Check variable scope (production vs preview)
    
    ## Rollback
    
    1. Go to Vercel dashboard > Deployments
    2. Find previous working deployment
    3. Click "..." menu > "Promote to Production"
    
    ## Monitoring
    
    - Vercel Analytics: Built-in performance monitoring
    - Logs: Real-time function logs in dashboard
    - Alerts: Configure in Vercel settings
    ```

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ apps/dashboard/vercel.json (new)
✅ apps/dashboard/.env.example (update)
✅ apps/dashboard/next.config.js (update rewrites if needed)
✅ docs/runbooks/vercel-deployment.md (new)

You MUST NOT touch:
❌ services/**/*.py (ML/Backend Agent)
❌ apps/dashboard/components/** (Frontend Agent)
❌ apps/dashboard/app/** (Frontend Agent)
❌ tests/** (QA Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

- [ ] vercel.json configured with rewrites and headers
- [ ] .env.example has all required variables documented
- [ ] API rewrites proxy to FastAPI correctly
- [ ] Production and preview environments documented
- [ ] Deployment runbook is comprehensive
- [ ] No secrets in committed files

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. List of files created/modified
2. Environment variables documented
3. Rewrite configuration summary
4. Deployment runbook location
5. Security headers added

═══════════════════════════════════════════════════════════════
```

---

## 👤 Integrator Agent Prompt

**Copy this entire section to a new Composer tab after all agents complete:**

---

```
You are the Integrator Agent for Sprint 6: ML Safety & Interpretability Core.

Your role is to:
1. Verify all agents completed their work correctly
2. Write the Sprint 6 Summary documenting tasks, files, and skills used
3. Update ALL project documentation to reflect Sprint 6 completion

═══════════════════════════════════════════════════════════════
📋 PHASE 1: VERIFICATION (Tasks L1-L2)
═══════════════════════════════════════════════════════════════

## 1. File Structure Verification

Check that these files exist:

ML Services:
- [ ] services/ml/drift/__init__.py
- [ ] services/ml/drift/detector.py
- [ ] services/ml/drift/metrics.py
- [ ] services/ml/drift/health_score.py
- [ ] services/ml/confidence/__init__.py
- [ ] services/ml/confidence/gating.py
- [ ] services/ml/explainability/__init__.py
- [ ] services/ml/explainability/shap_explainer.py
- [ ] services/ml/baselines/hold_cash.py
- [ ] services/ml/baselines/buy_and_hold.py
- [ ] services/ml/baselines/regret_calculator.py
- [ ] services/ml/hitl/__init__.py
- [ ] services/ml/hitl/approval_queue.py

API Routes:
- [ ] services/api/routers/drift.py
- [ ] services/api/routers/explanations.py
- [ ] services/api/routers/recommendations.py

Frontend:
- [ ] apps/dashboard/lib/glossary.ts
- [ ] apps/dashboard/components/ui/tooltip-wrapper.tsx
- [ ] apps/dashboard/app/(dashboard)/help/page.tsx
- [ ] apps/dashboard/components/explanation-card.tsx
- [ ] apps/dashboard/components/approval-queue.tsx
- [ ] apps/dashboard/components/baseline-comparison.tsx

Documentation:
- [ ] docs/architecture.md (updated with ML Safety section)
- [ ] adr/0008-ml-explainability.md
- [ ] adr/0009-drift-detection.md

Tests:
- [ ] tests/unit/test_drift_detection.py
- [ ] tests/unit/test_confidence_gating.py
- [ ] tests/unit/test_explainability.py
- [ ] tests/unit/test_baselines.py
- [ ] tests/integration/test_hitl_workflow.py
- [ ] docs/runbooks/ml-safety-verification.md

Vercel:
- [ ] apps/dashboard/vercel.json
- [ ] docs/runbooks/vercel-deployment.md

## 2. Test Execution

Run all tests:
```bash
poetry run pytest tests/unit/test_drift_detection.py tests/unit/test_confidence_gating.py tests/unit/test_explainability.py tests/unit/test_baselines.py -v
poetry run pytest tests/integration/test_hitl_workflow.py -v
```

Expected: All tests pass

═══════════════════════════════════════════════════════════════
📝 PHASE 2: SPRINT SUMMARY (Task L3)
═══════════════════════════════════════════════════════════════

Create `plans/SPRINT6_SUMMARY.md` with this structure:

```markdown
# Sprint 6 Summary: ML Safety & Interpretability Core

**Status:** ✅ COMPLETE  
**Completion Date:** [DATE]  
**Sprint Duration:** Days 15-18

---

## 🎯 Sprint 6 Goal

Transform the platform from a functional ML trading system into a trustworthy ML platform with explicit uncertainty handling, interpretable recommendations, and human oversight capabilities.

---

## ✅ Agent Tasks Completed

### ML Agent

**Files Created:**
[List all services/ml/** files]

| Task | Description | Status |
|------|-------------|--------|
| A1-A7 | Drift Detection | ✅ |
| B1-B6 | Confidence Gating | ✅ |
| C1-C6 | SHAP Explainability | ✅ |
| D1-D4 | Human-in-the-Loop | ✅ |
| E1-E6 | Baselines & Regret | ✅ |

### Frontend Agent

**Files Created:**
[List all dashboard files]

| Task | Description | Status |
|------|-------------|--------|
| F1-F6 | Help Page & Tooltips | ✅ |
| G1-G4 | Explainability UI | ✅ |
| H1-H4 | HITL & Baselines UI | ✅ |

### Architect Agent

**Files Created/Modified:**
[List architecture docs and ADRs]

| Task | Description | Status |
|------|-------------|--------|
| J1-J6 | Architecture Review & ADRs | ✅ |

### QA Agent

**Files Created:**
[List test files]

| Task | Description | Status |
|------|-------------|--------|
| K1-K7 | ML Safety Tests | ✅ |

### DevOps Agent

**Files Created/Modified:**
[List Vercel config files]

| Task | Description | Status |
|------|-------------|--------|
| I1-I5 | Vercel Deployment | ✅ |

---

## 🛠️ Skills Used

### ML Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@python-patterns` | [How it was applied] |
| `@api-patterns` | [How it was applied] |
| `@clean-code` | [How it was applied] |

### Frontend Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@nextjs-best-practices` | [How it was applied] |
| `@react-patterns` | [How it was applied] |
| `@tailwind-patterns` | [How it was applied] |

[Continue for each agent...]

---

## 📊 Test Results

- **Unit Tests:** X passed
- **Integration Tests:** Y passed
- **E2E Tests:** Z passed
- **Total:** X+Y+Z tests

---

## ⚠️ Known Issues

1. [Any issues discovered]
2. [Limitations]

---

## 🚀 Next Steps

Sprint 7: MLOps & Advanced Analysis
- Feature Registry & Lineage Tracking
- Experiment Registry & Research Traceability
- Dynamic Capital Allocation
- Failure Mode & Stress Simulation
- Counterfactual & What-If Analysis
```

═══════════════════════════════════════════════════════════════
📚 PHASE 3: DOCUMENTATION UPDATES (Tasks L4-L8)
═══════════════════════════════════════════════════════════════

## L4. Update plans/task_plan.md

Mark Sprint 6 tasks as complete:
- [ ] Change all Sprint 6 items from `[ ]` to `[x]`
- [ ] Add "✅ COMPLETE" to Sprint 6 header

## L5. Update plans/progress.md

- [ ] Update "Current Phase" to "Implementation - Sprint 6 ✅ COMPLETE"
- [ ] Update "Last Updated" date
- [ ] Add Sprint 6 completed items list
- [ ] Update "Next Actions" to reference Sprint 7

## L6. Update plans/milestones.md

- [ ] Mark "Days 15-18: ML Safety & Interpretability" as ✅ COMPLETE
- [ ] Check off all Sprint 6 deliverables

## L7. Update README.md

- [ ] Update "Current Phase" to Sprint 6 Complete
- [ ] Add Sprint 6 to completed sprints list
- [ ] Add ML safety features to feature list
- [ ] Add Vercel deployment info

## L8. Update docs/FEATURES.md

- [ ] Add ML Safety features to implemented list:
  - Drift detection (PSI, KL divergence, health score)
  - Confidence gating (ABSTAIN, thresholds)
  - SHAP explainability
  - Human-in-the-loop controls
  - Baseline comparisons
  - Educational tooltips & help page
  - Vercel deployment

═══════════════════════════════════════════════════════════════
✅ PHASE 4: FINAL VERIFICATION (Task L9)
═══════════════════════════════════════════════════════════════

After all updates, verify:

- [ ] plans/SPRINT6_SUMMARY.md exists and is complete
- [ ] plans/task_plan.md shows Sprint 6 complete
- [ ] plans/progress.md reflects current state
- [ ] plans/milestones.md shows Sprint 6 deliverables checked
- [ ] README.md shows Sprint 6 complete, Sprint 7 next
- [ ] docs/FEATURES.md includes ML safety features
- [ ] All file paths in documentation are correct
- [ ] No references to Sprint 6 as "in progress" or "not started"
- [ ] Dashboard deployed to Vercel (verify URL if available)

═══════════════════════════════════════════════════════════════

📤 FINAL OUTPUT

Provide a summary:

1. **Verification Results:** All files present, tests passing
2. **Sprint Summary:** Location of SPRINT6_SUMMARY.md
3. **Docs Updated:** List of files updated
4. **Skills Documentation:** Confirm skills are documented per agent
5. **Vercel Deployment:** Status of dashboard deployment
6. **Project Status:** Sprint 6 COMPLETE, ready for Sprint 7
7. **Any Issues:** Problems found during integration

═══════════════════════════════════════════════════════════════
```

---

## 📋 Execution Summary

| Phase | Agents | Tasks | Start Condition |
|-------|--------|-------|-----------------|
| 1 | ML (A+B+C+E), DevOps, Frontend (F), Architect | A1-A7, B1-B6, C1-C6, E1-E6, F1-F6, I1-I5, J1-J6 | Immediately |
| 2 | ML (D) | D1-D4 | After B+C complete |
| 3 | Frontend (G+H) | G1-G4, H1-H4 | After ML APIs ready |
| 4 | QA | K1-K7 | After ML services complete |
| 5 | Integrator | L1-L9 | After all agents complete |

**Estimated Total Tests:** 75+ (20 drift, 15 confidence, 15 explainability, 10 baselines, 10 HITL, 5 E2E)

**Key Deliverables:**
- Drift detection with PSI, KL divergence, health score
- Confidence gating with ABSTAIN capability
- SHAP explainability for tree-based models
- Human-in-the-loop approval workflow
- Baseline strategies and regret metrics
- Help page with searchable glossary
- Educational tooltips throughout dashboard
- Vercel deployment configuration
- **SPRINT6_SUMMARY.md** with tasks, files, and skills per agent
- **All project docs updated** to reflect Sprint 6 completion
