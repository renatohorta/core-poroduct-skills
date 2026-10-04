# Software Sizing & Effort Estimation (UCP / FPA / COCOMO II)

> Owned by `rup-orchestrator` (base role: Project Manager). An artifact of the
> *Project Management* discipline.

The RUP **Measurement Plan** is only meaningful when the size of the software is
estimated. This reference documents the three sizing techniques required by the
specification and, for **Use Case Points**, the exact computation implemented in
`scripts/run.py` (`compute_ucp`).

## 1. Use Case Points (UCP) — computed in code

Method (Karner; Schneider & Winters). UCP is derived from the actors and use
cases of the *Use-Case Model* — so it grows naturally across the RUP phases:
indicative in **Inception** (high-level, from the survey) and baselined in
**Elaboration** (detailed Use Cases + Data Model).

Formulas:

```
UAW  = Σ (actor_count × weight)          simple=1, average=2, complex=3
UUCW = Σ (usecase_count × weight)        simple=5, average=10, complex=15
UUCP = UAW + UUCW
TCF  = 0.65 + 0.01 × Σ T1..T13           13 technical factors, each 0..5 (2 = neutral)
EF   = 1.4  − 0.03 × Σ F1..F8            8 environmental factors, each 0..5 (3 = neutral)
UCP  = UUCP × TCF × EF
Effort(h) = UCP × productivity             productivity default: 20 h/UCP
```

Use-case complexity by number of transactions: **simple ≤ 3**, **average 4–7**,
**complex > 7**.

### Technical Complexity Factors (TCF)

| # | Factor | Weight |
|---|--------|--------|
| T1 | Distributed system | 0–5 |
| T2 | Performance / response-time objectives | 0–5 |
| T3 | End-user efficiency | 0–5 |
| T4 | Complex internal processing | 0–5 |
| T5 | Reusable code | 0–5 |
| T6 | Easy to install | 0–5 |
| T7 | Easy to use | 0–5 |
| T8 | Portable | 0–5 |
| T9 | Easy to change | 0–5 |
| T10 | Concurrent | 0–5 |
| T11 | Special security features | 0–5 |
| T12 | Provides direct access for third parties | 0–5 |
| T13 | Special user training facilities required | 0–5 |

### Environmental Factors (EF)

| # | Factor | Weight | Sense |
|---|--------|--------|-------|
| F1 | Familiar with the project model | 0–5 | negative |
| F2 | Application experience | 0–5 | negative |
| F3 | Object-oriented experience | 0–5 | negative |
| F4 | Lead analyst capability | 0–5 | negative |
| F5 | Motivation | 0–5 | negative |
| F6 | Stable requirements | 0–5 | negative |
| F7 | Part-time workers | 0–5 | positive |
| F8 | Difficult programming language | 0–5 | positive |

"Negative" factors are inverted in the sum (`5 − value`); "positive" factors use
the value directly. The neutral value (3) makes the EF sum, and therefore the
`0.03` term, cancel out.

### Example

15 use cases (10 average + 5 complex) and 4 actors (2 average + 2 complex),
neutral factors (empty maps → TCF = 1.0, EF = 1.0), productivity 20 h/UCP:

```
UAW  = (2×2) + (2×3) = 10
UUCW = (10×10) + (5×15) = 175
UUCP = 185
UCP  = 185 × 1.0 × 1.0 = 185
Effort = 185 × 20 = 3700 h
```

## 2. Function Point Analysis (FPA — IFPUG / NESMA) — produced by the LLM

Sizes the *Data Model* and the *Use Cases* in function points:

- **Data functions**: `ILF` (Internal Logical Files), `EIF` (External Interface Files).
- **Transactional functions**: `EI` (External Inputs), `EO` (External Outputs),
  `EQ` (External Inquiries).
- Unadjusted Function Points (UFP) → Value Adjustment Factor (VAF, the 14 GSCs)
  → Adjusted Function Points.

## 3. Parametric estimation (COCOMO II, SLOC/KLOC) — produced by the LLM

- Calibrate team productivity (loc/person-month); estimate **SLOC/KLOC per
  technology**; derive **COCOMO II** effort (with scale and cost drivers) and the
  schedule; align the delivery dates to the RUP phases.

## How the orchestrator uses this

- **Inception (§3.1)**: preliminary *Software Sizing & Estimation* — high-level
  FPA and **indicative UCP** from the Use-Case Model Survey (10–20% of use cases).
- **Elaboration (§3.2)**: **baselined** *Software Sizing & Effort Estimation* —
  detailed UCP + FPA derived from the complete Use Cases and the Data Model.
- The result feeds the **Measurement Plan / Project Measurements Database** and
  the **Iteration Plan** (effort per iteration = hours per phase).

## CLI (no LLM required)

```bash
# compute UCP from a JSON sizing model
python scripts/run.py --estimate --sizing sizing.json
python scripts/run.py --estimate --sizing sizing.json --json --output ucp.json

# print an empty sizing model to fill in
python scripts/run.py --sizing-template > sizing.json
```

Sizing model shape:

```json
{
  "actors": [{"type": "simple", "count": 0},
             {"type": "average", "count": 4},
             {"type": "complex", "count": 2}],
  "usecases": [{"type": "simple", "count": 0},
               {"type": "average", "count": 10},
               {"type": "complex", "count": 5}],
  "technical_factors": {"T1": 2, "T2": 3},
  "environmental_factors": {"F1": 2, "F6": 2},
  "productivity_hours": 20
}
```

Both factor maps are optional: omit them (or pass `{}`) for a neutral
`TCF = EF = 1.0`. When present, fill each factor 0–5 and any factor you leave
out defaults to its neutral mid-point (T = 2, F = 3).

Exit codes: `0` success · `1` usage error.
