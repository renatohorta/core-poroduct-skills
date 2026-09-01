---
name: cp-competitive-analysis
description: "Competitive Analysis — creates a CrewAI crew with a Market Analyst, Competitor Analyst, Pricing/Positioning Analyst and Strategist to compare products, features, prices, positioning and market strategies, generating complete competitive intelligence reports. Use when the user says 'analyze competitors', 'competitive analysis', 'compare competitors', 'market benchmarking', 'competitive analysis', 'battle card', 'competitor SWOT', or needs competitive intelligence for strategic decisions."
---

# cp-competitive-analysis — Competitive Analysis

Creates a CrewAI crew with specialized agents to run the complete competitive analysis cycle:

1. **Market Analyst** — Defines the scope, maps the market, size, growth and competitive dynamics
2. **Competitor Analyst** — Profiles each competitor: overview, product, strengths, weaknesses, strategy
3. **Pricing/Positioning Analyst** — Compares prices, tiers, positioning and the positioning map
4. **Strategist** — SWOT, competitive advantages, strategic recommendations and battle cards

## Agents

| Agent | Function |
|-------|----------|
| Market Analyst | Defines market, size, growth, trends and competitive dynamics |
| Competitor Analyst | Profiles competitors: overview, product, strengths, weaknesses, strategy |
| Pricing/Positioning Analyst | Compares prices, tiers, positioning and the positioning map |
| Strategist | SWOT, competitive advantages, recommendations and battle cards |

## Input

Analysis context — your company/product, competitors to analyze (or criteria to identify them), industry/segment, geographic scope and focus aspects. Can be:
- Direct text in the argument: `"our company is a SaaS for clinic management; analyze competitors like Doctoralia and Zenklub"`
- File: `--input context.txt`

## Output

Complete competitive intelligence report containing:
- Executive summary with key takeaways
- Market overview (definition, size, growth, landscape)
- Profiles of each competitor (overview, product, strengths, weaknesses, strategy)
- Feature comparison matrix
- Pricing comparison (tiers/plans)
- Positioning map
- SWOT summary
- Competitive advantages (yours vs. competitors')
- Strategic recommendations (immediate, medium-term, responses to watch)
- Battle cards per competitor (pitch, response, differentiators, objections)

## Quality Gate

The Strategist issues a PASS/FAIL verdict on the report's completeness. If FAIL, the report needs corrections before being considered complete.

## Usage

```bash
# Direct context
python .hermes/skills/cp-competitive-analysis/scripts/run.py "SaaS for clinic management; competitors: Doctoralia, Zenklub"

# File context
python .hermes/skills/cp-competitive-analysis/scripts/run.py --input context.txt

# Save output to a specific file
python .hermes/skills/cp-competitive-analysis/scripts/run.py "our product X" --output docs/competitive-analysis.md

# Only see the crew structure
python .hermes/skills/cp-competitive-analysis/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-competitive-analysis/scripts/run.py \
  "We are a SaaS for managing aesthetic clinics in Brazil. \
   We want to analyze competitors like Doctoralia, Zenklub and Clínica Ágil, \
   focusing on features, pricing and positioning. Goal: go-to-market strategy."
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.

## Manual path (alternative to the script)

When the target is a specific competitor and the team has internal documentation of its own product, the manual path usually yields better results than the crew — the agent already has product context and can compare with precision. Validated flow:

1. **Navigate the competitor's official site** (browser_navigate) — home, `/pricing`, `/about`, product pages. Extract real text via `browser_console` with `document.body.innerText` (the accessible snapshot sometimes omits JS-rendered content).
2. **Delegate the broad research to a subagent** (`delegate_task` with toolsets `["web","browser"]`) to collect capabilities, plans, positioning and competitors in parallel — avoids polluting the main agent's context with dozens of navigations.
3. **Read the internal documentation** of your own product (`.hermes/docs/`) for the feature-by-feature comparison, pricing, SWOT and battle card.
4. **Save the spec** in `doc/competitive-analysis/<competitor>-vs-<product>.md` (Crewbotics project convention — `doc/` folder at the root, not `.hermes/docs/`).

## Pitfall: animated price counters

Modern pricing pages (e.g. manus.im) render the US$ values as **animated counters** — each digit is a separate element that changes with animation. This makes `document.body.innerText` and text selectors return loose digits (`"0","1","2",...`) or nothing, and the real price is not extractable by scraping. What works:
- **Credits/quantities** (e.g. "4,000 credits/month") are usually static text and extractable.
- **Prices in currency** may not be extractable — **mark them as "unconfirmed"** in the report and ask the user for the value (who may have the page open in their browser) instead of inventing it.

## References

- `references/manus-im.md` — Manus (manus.im) research data collected on 15/08/2026: capabilities, plans, positioning, competitors and reliability notes.
