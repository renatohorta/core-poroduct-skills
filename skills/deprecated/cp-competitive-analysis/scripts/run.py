#!/usr/bin/env python3
"""
cp-competitive-analysis — Competitive Analysis Crew (self-contained)

Creates a CrewAI crew with specialized agents to analyze competitors, compare
products, features, prices, positioning and market strategies, generating
complete competitive intelligence reports.

Usage:
  python run.py "SaaS for clinic management; competitors: Doctoralia, Zenklub"
  python run.py --context "our product X" --output competitive-analysis.md
  python run.py --input context.txt
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # DT-07: the lib is only required for real execution, not --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # DT-01: UTF-8 on stdout/stderr (Windows console is cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "market-analyst": {
        "role": "Market Analyst",
        "goal": "Define the scope of the analysis, map the market, its size, growth and competitive dynamics",
        "backstory": (
            "Experienced market analyst with over 10 years in market research and "
            "competitive intelligence. You are an expert at defining markets, estimating "
            "size and growth, identifying trends and describing the competitive "
            "dynamics of an industry. You separate facts from opinions and always "
            "distinguish verified data from estimates. Your motto: 'A poorly "
            "defined market produces a useless competitive analysis.'"
        ),
    },
    "competitor-analyst": {
        "role": "Competitor Analyst",
        "goal": "Profile each competitor: overview, product, strengths, weaknesses and strategy",
        "backstory": (
            "Detail-oriented and methodical competitor analyst. You build complete profiles "
            "of each competitor: founding, headquarters, team, funding, target market, "
            "product portfolio, strengths, weaknesses and go-to-market approach. "
            "You use frameworks such as Porter's analysis (objectives, strategy, "
            "assumptions, capabilities) to predict competitive behavior. "
            "You are impartial: you do not exaggerate strengths nor minimize weaknesses."
        ),
    },
    "pricing-analyst": {
        "role": "Pricing and Positioning Analyst",
        "goal": "Compare prices, tiers, positioning and build the competitive positioning map",
        "backstory": (
            "Expert in pricing and market positioning. You compare plans and "
            "price tiers (entry, mid-tier, enterprise), identify pricing "
            "strategies (cost leader, premium, value) and position each competitor "
            "on a positioning map (price vs. innovation, narrow vs. broad focus). "
            "You understand that price is only one vector of positioning and that the "
            "perception of value matters as much as the number."
        ),
    },
    "strategist": {
        "role": "Competitive Strategist",
        "goal": "Synthesize SWOT, competitive advantages, strategic recommendations and battle cards",
        "backstory": (
            "Senior competitive strategist with a background in business strategy. "
            "You turn market data, competitor profiles and pricing "
            "analysis into actionable insights: SWOT, competitive advantages, short- and "
            "medium-term recommendations, competitive responses to watch and battle cards "
            "for sales teams. You are pragmatic and action-oriented — every "
            "recommendation must be executable. You issue the final report "
            "completeness verdict (PASS/FAIL)."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    data = AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agent not found: {slug} — using generic fallback")
        return Agent(
            role=name,
            goal=f"Complete the task with excellence as {name}",
            backstory=f"Specialized agent acting as {name}.",
            llm=_crew_llm,
            verbose=True,
            allow_delegation=False,
        )
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        llm=_crew_llm,
        verbose=True,
        allow_delegation=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Crew builder
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(context: str, output_path: str = None):
    """Build a CrewAI crew for competitive analysis."""

    market_analyst = get_agent("market-analyst")
    competitor_analyst = get_agent("competitor-analyst")
    pricing_analyst = get_agent("pricing-analyst")
    strategist = get_agent("strategist")

    # --- Task 1: Scope and Market ---
    market = Task(
        description=f"""
        ANALYSIS CONTEXT:
        {context}

        YOUR JOB — SCOPE AND MARKET DEFINITION:
        1. Clearly define the market/segment being analyzed
        2. Identify the competitors to analyze (those named in the context, or propose
           criteria and a candidate list if none were mentioned)
        3. Estimate the market size and growth rate (CAGR), clearly marking
           what is an estimate
        4. List the main industry trends
        5. Describe the overall competitive dynamics (concentration, barriers, differentiation)

        OUTPUT FORMAT:
        ## Market Overview
        - Market definition: [what]
        - Identified competitors: [list]
        - Size and growth: [estimates, marked as such]
        - Trends: [list]
        - Competitive dynamics: [description]
        """,
        expected_output="Scope definition, competitor list, market size/growth, trends and competitive dynamics",
        agent=market_analyst,
    )

    # --- Task 2: Competitor Profiles ---
    profiles = Task(
        description=f"""
        ANALYSIS CONTEXT:
        {context}

        YOUR JOB — COMPETITOR PROFILES:
        For EACH identified competitor, produce a complete profile:

        1. **Company Overview**: founding, headquarters, employees, funding/revenue, target market
        2. **Product/Service Overview**: main offerings
        3. **Strengths**: 3+ strengths
        4. **Weaknesses**: 3+ weaknesses
        5. **Strategy**: how they compete, go-to-market approach

        Use Porter's framework (future objectives, current strategy, assumptions,
        capabilities) to infer each one's competitive response profile.

        OUTPUT FORMAT (for each competitor):
        ### Competitor: [Name]
        #### Company Overview
        | Attribute | Detail |
        #### Product/Service Overview
        #### Strengths
        #### Weaknesses
        #### Strategy
        """,
        expected_output="Complete profiles of each competitor with overview, product, strengths, weaknesses and strategy",
        agent=competitor_analyst,
    )

    # --- Task 3: Pricing and Positioning ---
    pricing = Task(
        description=f"""
        ANALYSIS CONTEXT:
        {context}

        YOUR JOB — PRICING AND POSITIONING:
        Based on the competitor profiles:

        1. **Feature Matrix**: compare the main features/capabilities between
           [your company] and each competitor (✅ strong, ⚠️ partial, ❌ absent)
        2. **Pricing Comparison**: organize the plans/tiers (entry/free, mid-tier,
           enterprise) of each competitor side by side
        3. **Pricing Insights**: identify each one's strategy (cost leader,
           premium, value) and what it reveals
        4. **Positioning Map**: position each competitor on a map
           (e.g. high/low price vs. high/low innovation, or narrow/broad focus)

        OUTPUT FORMAT:
        ## Feature Comparison
        | Feature | [Your company] | [Comp 1] | [Comp 2] | [Comp 3] |
        ## Pricing Comparison
        | Tier | [Your company] | [Comp 1] | [Comp 2] | [Comp 3] |
        ## Positioning Map
        [textual description of the positioning map]
        ## Pricing Insights
        """,
        expected_output="Feature matrix, pricing comparison, pricing insights and positioning map",
        agent=pricing_analyst,
    )

    # --- Task 4: Strategy and Battle Cards ---
    strategy = Task(
        description=f"""
        ANALYSIS CONTEXT:
        {context}

        YOUR JOB — STRATEGIC SYNTHESIS:
        Based on all the material produced (market, profiles, pricing/positioning):

        1. **Executive Summary**: 3-4 sentences with the main findings and strategic
           implications + 3 key takeaways
        2. **SWOT**: strengths, weaknesses, opportunities and threats of [your company]
        3. **Competitive Advantages**: your advantages vs. each competitor, and where
           each competitor stands out
        4. **Strategic Recommendations**: immediate actions, medium-term strategy,
           and competitive responses to watch
        5. **Battle Cards**: for each competitor — when they appear, their pitch,
           our response, key differentiators, winning themes and objection handling

        Finally, issue the **completeness verdict**: PASS or FAIL.
        If FAIL, list what is missing for the report to be considered complete.

        OUTPUT FORMAT:
        ## Executive Summary
        ## SWOT Summary
        ## Competitive Advantages
        ## Strategic Recommendations
        ## Battle Cards
        ## Quality Gate: PASS/FAIL
        """,
        expected_output="Complete strategic report: executive summary, SWOT, advantages, recommendations, battle cards and PASS/FAIL verdict",
        agent=strategist,
    )

    # --- Crew ---
    crew = Crew(
        agents=[market_analyst, competitor_analyst, pricing_analyst, strategist],
        tasks=[market, profiles, pricing, strategy],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-competitive-analysis: Competitive Analysis Crew (self-contained)",
    )
    parser.add_argument(
        "context",
        nargs="?",
        help="Analysis context: your company/product, competitors, industry, scope",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the context (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the competitive analysis report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only builds the crew and shows the agents, without running",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of a traceback

    # --- Resolve context ---
    context = None
    if args.input_file:
        context = Path(args.input_file).read_text(encoding="utf-8")
    elif args.context:
        context = args.context
    else:
        parser.print_help()
        print("\n❌ Error: provide the analysis context (argument or --input)")
        sys.exit(1)

    output_path = args.output

    print(f"\n📋 Context: {context[:120]}...")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(context, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running competitive analysis crew...\n")
    require_llm()  # DT-08: fails early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Competitive Analysis Report generated!\n")
    print(result_str)

    # --- Save output ---
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")
    else:
        # Save to default location
        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"competitive-analysis_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
