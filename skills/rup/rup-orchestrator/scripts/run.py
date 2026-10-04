#!/usr/bin/env python3
"""
RUP-Orchestrator — RUP Orchestrator Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency) for the RUP
Orchestrator discipline. Agents are defined inline, matching the RUP specification
(Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.).

Usage:
  python run.py "business demand" --phase Inception --dry-run
  python run.py "demand" --discipline requirements --auto
  python run.py --estimate --sizing sizing.json --json   # Use Case Points (no LLM)
  python run.py --list
"""

import argparse
import sys
from pathlib import Path
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # the lib is only required for real execution, not --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/rup/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
# ═════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS (self-contained — no dependency on an external dir)
# ═════════════════════════════════════════════════════════════════════════

AGENTS = {
    "rup-orchestrator": {
        "role": 'RUP Orchestrator',
        "goal": 'Govern the RUP lifecycle: produce and maintain the Software Development Plan, Business Case, Risk List, Software Sizing & Effort Estimation (FPA, Use Case Points, COCOMO II), Iteration Plan, Iteration/Status Assessments, Work Orders and the Measurement Plan/Database.',
        "backstory": 'Project Manager who runs the RUP lifecycle: you are the only interface to the user, you translate business goals into Work Orders, size the software and estimate effort with Function Points, Use Case Points and COCOMO II, balance scope, schedule, risk and cost, and judge each iteration against formal acceptance criteria.',
    },
}



def get_agent(slug: str) -> Agent:
    """Get a CrewAI Agent from the embedded definitions."""
    _crew_llm = build_crew_llm()
    data = AGENTS.get(slug)
    if not data:
        print(f"  [!] Agent not found: {slug} — using defaults")
        return Agent(
            role=slug.replace("-", " ").title(),
            goal="Complete the assigned task with excellence",
            backstory="Specialized AI agent",
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
# Discipline registry (the 8 RUP disciplines + their agents)
# ═══════════════════════════════════════════════════════════════════════════

DISCIPLINES = {
    "environment": {"skill": "rup-environment", "title": "Environment", "agents": ["process-engineer"]},
    "business-modeling": {"skill": "rup-business-modeling", "title": "Business Modeling", "agents": ["business-process-analyst", "business-designer"]},
    "requirements": {"skill": "rup-requirements", "title": "Requirements", "agents": ["system-analyst", "requirements-specifier"]},
    "analysis-design": {"skill": "rup-analysis-design", "title": "Analysis & Design", "agents": ["software-architect", "designer", "user-interface-designer", "database-designer", "capsule-designer"]},
    "implementation": {"skill": "rup-implementation", "title": "Implementation", "agents": ["system-integrator", "implementer"]},
    "test": {"skill": "rup-test", "title": "Test", "agents": ["test-manager", "test-analyst", "test-designer", "tester"]},
    "ccm": {"skill": "rup-ccm", "title": "Configuration & Change Management", "agents": ["configuration-manager", "change-control-manager"]},
    "deployment": {"skill": "rup-deployment", "title": "Deployment", "agents": ["deployment-manager", "technical-writer"]},
}

PHASES = ["Inception", "Elaboration", "Construction", "Transition"]
PHASE_MILESTONES = {
    "Inception": "Lifecycle Objective (LCO)",
    "Elaboration": "Lifecycle Architecture (LCA)",
    "Construction": "Initial Operational Capability (IOC)",
    "Transition": "Product Release (PR)",
}
RUP_ROOT = Path(__file__).resolve().parent.parent.parent  # skills/rup/


def discipline_run_py(discipline_key: str) -> Path:
    return RUP_ROOT / DISCIPLINES[discipline_key]["skill"] / "scripts" / "run.py"


DISC_NAMES = "\n".join(
    f"- {k}: {v['title']} — agents: {', '.join(v['agents'])}"
    for k, v in DISCIPLINES.items()
)


# ═══════════════════════════════════════════════════════════════════════════
# Software Sizing & Effort Estimation — Use Case Points (UCP)
#
# Pure-Python, deterministic estimator following the UCP method (Karner /
# Schneider & Winters). Runs without crewai or an LLM, so the orchestrator can
# size the software from a model of actors and use cases. The RUP specification
# also asks for FPA (IFPUG/NESMA) and COCOMO II — those are produced by the LLM
# from the use-case and data models; UCP is computed exactly here.
# ═══════════════════════════════════════════════════════════════════════════

# Unadjusted Actor Weight (UAW): simple=1, average=2, complex=3
ACTOR_WEIGHTS = {"simple": 1, "average": 2, "complex": 3}

# Unadjusted Use Case Weight (UUCW): simple=5, average=10, complex=15
# (complexity by number of transactions: <=3, 4..7, >7)
USECASE_WEIGHTS = {"simple": 5, "average": 10, "complex": 15}

# Technical Complexity Factors (TCF): 13 factors, weight 0..5 (2 = neutral)
TECHNICAL_FACTORS = [
    ("T1", "Distributed system"),
    ("T2", "Performance / response-time objectives"),
    ("T3", "End-user efficiency"),
    ("T4", "Complex internal processing"),
    ("T5", "Reusable code"),
    ("T6", "Easy to install"),
    ("T7", "Easy to use"),
    ("T8", "Portable"),
    ("T9", "Easy to change"),
    ("T10", "Concurrent"),
    ("T11", "Special security features"),
    ("T12", "Provides direct access for third parties"),
    ("T13", "Special user training facilities required"),
]

# Environmental Factors (EF): 8 factors, weight 0..5 (3 = neutral)
ENVIRONMENTAL_FACTORS = [
    ("F1", "Familiar with the project model", "negative"),
    ("F2", "Application experience", "negative"),
    ("F3", "Object-oriented experience", "negative"),
    ("F4", "Lead analyst capability", "negative"),
    ("F5", "Motivation", "negative"),
    ("F6", "Stable requirements", "negative"),
    ("F7", "Part-time workers", "positive"),
    ("F8", "Difficult programming language", "positive"),
]

DEFAULT_ACTORS = [{"type": "simple", "count": 0},
                  {"type": "average", "count": 0},
                  {"type": "complex", "count": 0}]
DEFAULT_USECASES = [{"type": "simple", "count": 0},
                    {"type": "average", "count": 0},
                    {"type": "complex", "count": 0}]


def compute_ucp(actors=None, usecases=None, technical_factors=None,
                environmental_factors=None, productivity_hours=20.0,
                default_tcf=1.0, default_ef=1.0):
    """Compute Unadjusted/Ajusted Use Case Points and the effort in hours.

    actors: list of {"type": "simple|average|complex", "count": n}
    usecases: list of {"type": "simple|average|complex", "count": n}
    technical_factors: {T1..T13: 0..5}   (missing -> 2 = neutral)
    environmental_factors: {F1..F8: 0..5} (missing -> 3 = neutral)
    productivity_hours: hours per Use Case Point (default 20).
    Returns a dict with every intermediate value.
    """
    actors = actors or []
    usecases = usecases or []
    tf = technical_factors or {}
    ef = environmental_factors or {}

    uaw = sum(ACTOR_WEIGHTS[a["type"]] * a["count"] for a in actors)
    uucw = sum(USECASE_WEIGHTS[u["type"]] * u["count"] for u in usecases)
    uucp = uaw + uucw

    # TCF = 0.65 + 0.01 * sum(T1..T13). An EMPTY factor map is neutral: TCF = 1.0.
    # When factors are provided, each is rated 0..5 (missing ones default to 2).
    if tf:
        tf_sum = sum(int(tf.get(k, 2)) for k, _ in TECHNICAL_FACTORS)
        tcf = round(0.65 + 0.01 * tf_sum, 4)
    else:
        tf_sum = None
        tcf = 1.0

    # EF = 1.4 - 0.03 * sum(F1..F8). An EMPTY factor map is neutral: EF = 1.0.
    # F1..F6 (negative) are inverted (5 - value); F7..F8 (positive) use the value.
    if ef:
        ef_sum = 0
        for key, _, sense in ENVIRONMENTAL_FACTORS:
            v = int(ef.get(key, 3))
            ef_sum += (5 - v) if sense == "negative" else v
        ef_val = round(1.4 - 0.03 * ef_sum, 4)
    else:
        ef_sum = None
        ef_val = 1.0

    ucp = round(uucp * tcf * ef_val, 2)
    effort_hours = round(ucp * productivity_hours, 1)

    return {
        "method": "Use Case Points (UCP)",
        "actors": actors,
        "usecases": usecases,
        "uaw": uaw,
        "uucw": uucw,
        "uucp": uucp,
        "technical_factor_sum": tf_sum,
        "tcf": tcf,
        "environmental_factor_sum": ef_sum,
        "ef": ef_val,
        "ucp": ucp,
        "productivity_hours_per_ucp": productivity_hours,
        "effort_hours": effort_hours,
    }


def estimate_from_json(path):
    """Compute UCP from a JSON sizing model produced by the orchestrator/LLM."""
    import json
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return compute_ucp(
        actors=data.get("actors", DEFAULT_ACTORS),
        usecases=data.get("usecases", DEFAULT_USECASES),
        technical_factors=data.get("technical_factors", {}),
        environmental_factors=data.get("environmental_factors", {}),
        productivity_hours=float(data.get("productivity_hours", 20.0)),
    )


def template_sizing():
    """Return an empty sizing model (JSON) to fill in and pass to --estimate.

    Factors start empty = neutral (TCF = EF = 1.0). Fill each 0..5 to adjust.
    """
    import json
    return json.dumps({
        "note": "Fill the actor/use-case counts. Factor maps are optional: empty = "
                "neutral (TCF=EF=1.0); fill each 0..5 to adjust. "
                "T1..T13 = " + ", ".join(k for k, _ in TECHNICAL_FACTORS) + "; "
                "F1..F8 = " + ", ".join(k for k, _, _ in ENVIRONMENTAL_FACTORS) + ".",
        "actors": DEFAULT_ACTORS,
        "usecases": DEFAULT_USECASES,
        "technical_factors": {},
        "environmental_factors": {},
        "productivity_hours": 20,
    }, indent=2)


def print_estimate(result):
    """Human-readable UCP report."""
    print("\n🧮 Software Sizing & Effort Estimation — Use Case Points (UCP)")
    print("─" * 62)
    print("  Actors:")
    for a in result["actors"]:
        print(f"    - {a['type']:8s} x{a['count']:<3d} "
              f"(weight {ACTOR_WEIGHTS[a['type']]})")
    print("  Use cases:")
    for u in result["usecases"]:
        print(f"    - {u['type']:8s} x{u['count']:<3d} "
              f"(weight {USECASE_WEIGHTS[u['type']]})")
    print("─" * 62)
    print(f"  UAW (Unadjusted Actor Weight)       : {result['uaw']}")
    print(f"  UUCW (Unadjusted Use Case Weight)   : {result['uucw']}")
    print(f"  UUCP (Unadjusted Use Case Points)   : {result['uucp']}")
    tf_sum = result["technical_factor_sum"]
    ef_sum = result["environmental_factor_sum"]
    print(f"  TCF (Technical Complexity Factor)   : {result['tcf']}"
          + (f"  (sum {tf_sum})" if tf_sum is not None else "  (neutral)"))
    print(f"  EF  (Environmental Factor)          : {result['ef']}"
          + (f"  (sum {ef_sum})" if ef_sum is not None else "  (neutral)"))
    print(f"  UCP (Use Case Points)               : {result['ucp']}")
    print(f"  Effort @ {result['productivity_hours_per_ucp']} h/UCP : "
          f"{result['effort_hours']} h")


# ═══════════════════════════════════════════════════════════════════════════
# Crew builder (governance)
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, phase: str = "Elaboration"):
    """Build the RUP governance crew (the Project Manager agent)."""
    pm = get_agent("rup-orchestrator")

    govern = Task(
        description=f"""
PHASE: {phase} (milestone: {PHASE_MILESTONES.get(phase, "n/a")})

BUSINESS DEMAND / CONTEXT:
{briefing}

YOUR JOB — RUP governance:
1. Classify the demand into the RUP phase and the disciplines it touches.
2. Update (or draft) the Software Development Plan (SDP), Business Case and Risk List.
3. Produce the Software Sizing & Effort Estimation: Function Point Analysis
   (IFPUG/NESMA — ILF/EIF, EI/EO/EQ), Use Case Points (UAW/UUCW/UUCP/TCF/EF, via
   the `compute_ucp` helper) and parametric estimates (COCOMO II, SLOC/KLOC),
   deriving the effort in hours per iteration.
4. Formulate the Iteration Plan and the Work Orders for each discipline involved.
5. State the acceptance criteria and the measurement plan for the iteration.

DISCIPLINES AVAILABLE:
{DISC_NAMES}
""",
        expected_output="RUP governance output: phase classification, SDP/Business Case/Risk List "
                        "updates, Software Sizing & Effort Estimation (UCP/FPA/COCOMO II), "
                        "Iteration Plan, and one Work Order per discipline involved.",
        agent=pm,
    )

    return Crew(agents=[pm], tasks=[govern], process=Process.sequential, verbose=True)


# ═══════════════════════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════════════════════

def _find_python():
    """Python able to run the discipline skills (with crewai), or the current one."""
    import os
    explicit = os.environ.get("RUP_SKILLS_PYTHON")
    if explicit and Path(explicit).exists():
        return explicit
    return sys.executable


def dispatch(discipline_key, briefing, phase, output):
    """Trigger one RUP discipline skill via subprocess (CLI contract)."""
    import subprocess
    run_py = discipline_run_py(discipline_key)
    if not run_py.exists():
        print(f"  ❌ discipline skill not found: {run_py}")
        return 2
    cmd = [_find_python(), str(run_py), briefing, "--phase", phase]
    if output:
        cmd += ["--output", output]
    print(f"  ⚙️  dispatching {discipline_key} -> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(RUP_ROOT))
    return r.returncode


def list_disciplines():
    print("RUP disciplines:")
    for k, v in DISCIPLINES.items():
        print(f"  - {k:20s} {v['title']}  ({len(v['agents'])} agents)")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP-Orchestrator — governs the RUP lifecycle and dispatches the disciplines",
    )
    parser.add_argument("briefing", nargs="?",
                        help="Business demand / product direction")
    parser.add_argument("--input", dest="input_file",
                        help="File with the briefing (alternative to the positional)")
    parser.add_argument("--phase", choices=PHASES, default="Elaboration",
                        help="RUP phase (default: Elaboration)")
    parser.add_argument("--discipline", choices=list(DISCIPLINES.keys()),
                        help="Dispatch only this discipline (instead of governance)")
    parser.add_argument("--auto", action="store_true",
                        help="Dispatch each discipline crew in sequence")
    parser.add_argument("--list", action="store_true", help="List the disciplines and exit")
    parser.add_argument("--estimate", action="store_true",
                        help="Compute Software Sizing & Effort Estimation (Use Case Points); no LLM needed")
    parser.add_argument("--sizing", dest="sizing_file",
                        help="JSON sizing model for --estimate (actors, use cases, TCF/EF factors)")
    parser.add_argument("--sizing-template", action="store_true",
                        help="Print an empty JSON sizing model to fill in and exit")
    parser.add_argument("--json", action="store_true",
                        help="With --estimate: emit the UCP result as JSON")
    parser.add_argument("--output", "-o", help="File to write the result to")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show the plan without calling an LLM")
    args = parser.parse_args()

    # Commands that need no crewai and no LLM (deterministic helpers).
    if args.sizing_template:
        print(template_sizing())
        return
    if args.list:
        list_disciplines()
        return
    if args.estimate:
        if args.sizing_file:
            result = estimate_from_json(args.sizing_file)
        else:
            result = compute_ucp()
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print_estimate(result)
        if args.output:
            import json
            Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return

    require_crewai()

    briefing = args.briefing
    if args.input_file:
        briefing = Path(args.input_file).read_text(encoding="utf-8", errors="replace")
    if not briefing:
        parser.print_help()
        print("\n❌ Error: provide the briefing (positional or --input)")
        sys.exit(1)

    print("\n🏛️  RUP-Orchestrator")
    print(f"📐 Phase: {args.phase} -> {PHASE_MILESTONES[args.phase]}")
    print()

    if args.discipline:
        if args.dry_run:
            print(f"🧪 DRY RUN — would dispatch discipline: {args.discipline}")
            return
        sys.exit(dispatch(args.discipline, briefing, args.phase, args.output))

    if args.auto:
        if args.dry_run:
            print("🧪 DRY RUN — would dispatch, in sequence:")
            for k in DISCIPLINES:
                print(f"  - {k} ({DISCIPLINES[k]['title']})")
            return
        print("🚀 Dispatching all disciplines in sequence...\n")
        rc = 0
        for k in DISCIPLINES:
            rc = dispatch(k, briefing, args.phase, args.output) or rc
        sys.exit(rc)

    crew = build_crew(briefing, args.phase)
    if args.dry_run:
        print("🧪 DRY RUN — governance crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running governance crew...\n")
    require_llm()
    result = crew.kickoff()
    print(f"\n✅ Final result:\n{result}")
    if args.output:
        Path(args.output).write_text(str(result), encoding="utf-8")
        print(f"\n📄 Result written to {args.output}")


if __name__ == "__main__":
    main()
