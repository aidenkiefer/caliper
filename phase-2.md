# Caliper Deep Review & Forward Planning (Cursor Instruction)

## Purpose

You are an expert ML systems architect, quantitative trading systems reviewer, and developer-educator.

Your task is to deeply read, understand, and reason about the entire Caliper codebase. You must build a complete mental model of how the system currently works, what has been implemented, what is planned but missing, and how the project should evolve next.

This is not a shallow code skim. You are expected to explore files, follow references, trace execution paths, and synthesize understanding across documentation, architecture, and implementation.

The project owner:
- Has strong software engineering skills
- Has a moderate ML background
- Has very limited finance / trading knowledge
- Cares deeply about model understanding, visualization, interpretability, and experimentation
- Is more interested in learning and system correctness than trading folklore or hype

Your output must explain the system in clear, plain language suitable for a developer with minimal trading knowledge.

You should use skills found in @agents/skills/skills/*, start by reading @agents/skills/skills/using-superpowers/SKILL.md to understand how/when to use skills, and try to use each of the following skills, if possible:

### Core reasoning & synthesis

1. **codebase-reader**
2. **architecture-analyzer**
3. **ml-system-explainer**
4. **implementation-vs-plan-diff**

### Planning & direction setting

5. **sprint-planner**
6. **design-reviewer**

### Misc

7. **ux-for-technical-users**
8. **question-generator**


---

## Scope of Review

You must read and reason about all relevant parts of the repository, including but not limited to:

- README and any top-level documentation
- All files in plans, docs, or similar planning folders
- services and backend logic
- packages and shared libraries
- any model, strategy, feature engineering, backtesting, or execution code
- configuration, orchestration, and environment setup
- database schemas or migrations
- dashboards or UI-related code

Assume that all completed sprints in the repository represent the current implemented state.

---

## Required Output Sections

Your final output must be a file called deep-review.md, structured into the following sections, in order.

Do not skip sections.

---

### 1. Current ML and Model System (Explained for Non-Traders)

Explain in plain English:

- What ML models currently exist (or are scaffolded)
- What inputs they receive (features, signals, indicators, data sources)
- What outputs they produce (predictions, scores, signals, confidence, etc.)
- What each model is attempting to predict or estimate
- Whether models are trained offline, online, or via walk-forward approaches
- How training, validation, and testing are currently implemented
- How temporal splits are handled
- What safeguards exist against overfitting or data leakage
- Whether models adapt over time or are static

Assume the reader understands software and basic ML concepts, but does not understand trading or markets.

Avoid trading jargon unless it is clearly explained.

---

### 2. End-to-End Trading Decision Pipeline

Explain how the system makes decisions from start to finish.

Walk through the full pipeline step by step:

1. Market data ingestion
2. Feature generation
3. Strategy logic versus ML outputs
4. Signal generation
5. Risk checks and constraints
6. Trade sizing and execution logic
7. Monitoring, logging, and feedback

Clarify:
- Where decisions are deterministic versus probabilistic
- Where ML influences decisions versus rule-based logic
- How disagreements between models or strategies are resolved
- What happens when confidence is low
- What happens when safeguards override model outputs

Explain this as if describing a machine that observes the world and decides whether or not to act.

---

### 3. Implemented vs Planned vs Missing

Based on your full review:

- Identify which components are fully implemented and production-ready
- Identify which components exist only as scaffolding or placeholders
- Identify which planned features are documented but not implemented
- Identify any gaps between what documentation claims and what code actually does
- Identify any critical missing components required for:
  - Reliable experimentation
  - Model iteration
  - Safety and correctness
  - User understanding

Be precise and honest.

---

### 4. Model Transparency and User Control Opportunities

This section is extremely important.

Propose specific ways the system could give users (especially ML-oriented users):

- Visibility into individual model performance
- Access to model parameters, thresholds, and reward functions
- The ability to compare models side-by-side
- The ability to enable or disable models in an ensemble
- Insight into why a model made a prediction
- Clear feedback on when models abstain or fail
- Visualizations that link predictions to outcomes

Focus on interpretability, experimentation, and learning, not just profitability.

---

### 5. Improving Accuracy Without Finance Expertise

Without relying on advanced trading theory, propose improvements grounded in ML and statistics:

- Validation improvements (walk-forward testing, regime splits, stress tests)
- Ensemble improvements (weighting, specialization, voting, confidence aggregation)
- Data quality improvements (feature sanity checks, leakage prevention)
- Safety mechanisms (confidence decay, model vetoes, failure isolation)
- Feedback loops that improve learning without reinforcing noise

Prioritize approaches that are understandable, testable, and explainable.

---

### 6. Questions the Project Owner Should Be Asking

List important questions the project owner should be asking at this stage, including:

- Architectural questions
- ML methodology questions
- Experimentation and evaluation questions
- UX and learning experience questions
- Risk and safety questions

These questions should help guide future design decisions and sprints.

---

### 7. Recommendations for Next Sprints

Finish with concrete, actionable recommendations:

- A prioritized list of next features to implement
- Suggested sprint grouping (near-term vs medium-term)
- Which features are critical for learning and understanding
- Which features are critical for system correctness and safety
- Any refactors that would significantly improve long-term maintainability

Make this practical and aligned with the project’s learning-first goals.

---

## Tone and Constraints

- Use clear, direct language
- Avoid unexplained jargon
- Prefer explanation and reasoning over code snippets
- Treat this as a design review and mentorship exercise
- Optimize for clarity, correctness, and long-term understanding

Your goal is to help the project owner deeply understand their own system and make confident decisions about how to evolve it.
