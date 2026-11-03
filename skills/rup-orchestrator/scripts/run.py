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
# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = _Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "llm.py").is_file():
        if str(_root) not in _sys.path:
            _sys.path.insert(0, str(_root))
        break
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



def get_agent(slug: str, tools=None) -> Agent:
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
        tools=list(tools or []),
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
# Root holding the discipline skills (siblings of this one): skills/ in the repo,
# ~/.claude/skills/ or <hermes>/skills/<category>/ once installed.
RUP_ROOT = Path(__file__).resolve().parent.parent.parent


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


class SizingError(ValueError):
    """Invalid sizing model (bad JSON shape, unknown type, out-of-range factor)."""


def _validate_counts(items, weights, label):
    if not isinstance(items, list):
        raise SizingError(f"{label} must be a list of {{type, count}}")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise SizingError(f"{label}[{i}] must be an object {{type, count}}")
        if item.get("type") not in weights:
            raise SizingError(f"{label}[{i}].type must be one of {sorted(weights)}, "
                              f"got {item.get('type')!r}")
        count = item.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise SizingError(f"{label}[{i}].count must be a non-negative integer, "
                              f"got {count!r}")


def _validate_factors(factors, valid_keys, label):
    if not isinstance(factors, dict):
        raise SizingError(f"{label} must be an object {{key: 0..5}}")
    for key, value in factors.items():
        if key not in valid_keys:
            raise SizingError(f"{label}: unknown factor {key!r} (valid: {', '.join(valid_keys)})")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 5:
            raise SizingError(f"{label}.{key} must be a number 0..5, got {value!r}")


def ucp_from_model(data):
    """Validate a sizing model (dict) and compute the UCP. Raises SizingError."""
    if not isinstance(data, dict):
        raise SizingError("the sizing model must be a JSON object")
    actors = data.get("actors", DEFAULT_ACTORS)
    usecases = data.get("usecases", DEFAULT_USECASES)
    tf = data.get("technical_factors", {}) or {}
    ef = data.get("environmental_factors", {}) or {}
    _validate_counts(actors, ACTOR_WEIGHTS, "actors")
    _validate_counts(usecases, USECASE_WEIGHTS, "usecases")
    _validate_factors(tf, [k for k, _ in TECHNICAL_FACTORS], "technical_factors")
    _validate_factors(ef, [k for k, _, _ in ENVIRONMENTAL_FACTORS], "environmental_factors")
    try:
        hours = float(data.get("productivity_hours", 20.0))
    except (TypeError, ValueError):
        raise SizingError("productivity_hours must be a number")
    if hours <= 0:
        raise SizingError("productivity_hours must be > 0")
    return compute_ucp(actors=actors, usecases=usecases, technical_factors=tf,
                       environmental_factors=ef, productivity_hours=hours)


def estimate_from_json(path):
    """Compute UCP from a JSON sizing file. Raises SizingError / OSError."""
    import json
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SizingError(f"invalid JSON in {path}: {e}")
    return ucp_from_model(data)


def ucp_tool_run(sizing_json: str) -> str:
    """Body of the agent's UCP tool: JSON in, JSON out, errors as text (never raises)."""
    import json
    try:
        data = json.loads(sizing_json) if isinstance(sizing_json, str) else sizing_json
        return json.dumps(ucp_from_model(data), indent=2)
    except (json.JSONDecodeError, SizingError) as e:
        return f"ERROR: {e}. Expected JSON: {template_sizing()}"


UCP_TOOL_NAME = "use_case_points_calculator"


def build_ucp_tool():
    """CrewAI tool exposing compute_ucp to the governance agent (None without crewai).

    Without it the agent can only *imitate* the arithmetic — the LLM would make
    up UAW/UUCW/TCF/EF values instead of computing them.
    """
    try:
        from crewai.tools import tool
    except ImportError:
        return None

    @tool(UCP_TOOL_NAME)
    def use_case_points_calculator(sizing_json: str) -> str:
        """Compute Use Case Points deterministically. Input: a JSON string with
        "actors" and "usecases" (lists of {"type": "simple|average|complex",
        "count": int}), optional "technical_factors" {T1..T13: 0..5},
        optional "environmental_factors" {F1..F8: 0..5} and optional
        "productivity_hours" (hours per UCP, default 20). Returns JSON with
        UAW, UUCW, UUCP, TCF, EF, UCP and effort_hours."""
        return ucp_tool_run(sizing_json)

    return use_case_points_calculator


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
    ucp_tool = build_ucp_tool()
    pm = get_agent("rup-orchestrator", tools=[ucp_tool] if ucp_tool else None)

    govern = Task(
        description=f"""
PHASE: {phase} (milestone: {PHASE_MILESTONES.get(phase, "n/a")})

BUSINESS DEMAND / CONTEXT:
{briefing}

YOUR JOB — RUP governance:
1. Classify the demand into the RUP phase and the disciplines it touches.
2. Update (or draft) the Software Development Plan (SDP), Business Case and Risk List.
3. Produce the Software Sizing & Effort Estimation: Function Point Analysis
   (IFPUG/NESMA — ILF/EIF, EI/EO/EQ), Use Case Points and parametric estimates
   (COCOMO II, SLOC/KLOC), deriving the effort in hours per iteration.
   For Use Case Points, classify the actors and use cases, rate the TCF/EF
   factors, then CALL the `{UCP_TOOL_NAME}` tool and report its numbers —
   never compute UAW/UUCW/UUCP/TCF/EF/UCP by hand.
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


def dispatch(discipline_key, briefing, phase, output=None, input_file=None):
    """Trigger one RUP discipline skill via subprocess (CLI contract).

    The briefing goes positionally, or via --input when `input_file` is given
    (used by --auto to pass the chained context).
    """
    import subprocess
    run_py = discipline_run_py(discipline_key)
    if not run_py.exists():
        print(f"  ❌ discipline skill not found: {run_py}")
        return 1
    cmd = [_find_python(), str(run_py)]
    cmd += ["--input", str(input_file)] if input_file else [briefing]
    cmd += ["--phase", phase]
    if output:
        cmd += ["--output", str(output)]
    print(f"  ⚙️  dispatching {discipline_key} -> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(RUP_ROOT))
    return r.returncode


# Cap per prior artifact injected into the next discipline's context, so a long
# chain does not blow up the prompt (the full text stays in the output file).
MAX_PRIOR_ARTIFACT_CHARS = 12000


def auto_output_path(output, index, discipline_key, workdir):
    """Where discipline #index writes its artifact in --auto.

    With --output plan.md -> plan.01-environment.md, plan.02-business-modeling.md…
    (one file per discipline — a single shared path would be overwritten and only
    the last discipline would survive). Without --output -> a temporary workdir.
    """
    name = f"{index:02d}-{discipline_key}"
    if output:
        p = Path(output)
        return p.with_name(f"{p.stem}.{name}{p.suffix or '.md'}")
    return Path(workdir) / f"{name}.md"


def build_chained_context(briefing, prior):
    """Briefing + the artifacts produced by the previous disciplines.

    prior: list of (discipline_key, artifact_path) in execution order.
    """
    parts = [briefing.rstrip()]
    available = [(k, Path(p)) for k, p in prior if Path(p).is_file()]
    if available:
        parts.append(
            "\n\n# ARTIFACTS FROM PREVIOUS RUP DISCIPLINES (this iteration)\n"
            "Build on them: keep names, IDs and decisions consistent and trace your "
            "artifacts back to them.")
        for key, path in available:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) > MAX_PRIOR_ARTIFACT_CHARS:
                text = (text[:MAX_PRIOR_ARTIFACT_CHARS]
                        + f"\n[… truncated — full artifact in {path}]")
            parts.append(f"\n## {DISCIPLINES[key]['title']} ({key})\n\n{text}")
    return "\n".join(parts) + "\n"


def run_auto(briefing, phase, output=None):
    """Dispatch every discipline in order, chaining each one's artifact into the next.

    Stops at the first failing discipline (the next ones would only build on a
    missing artifact) and returns its exit code.
    """
    import tempfile
    with tempfile.TemporaryDirectory(prefix="rup-auto-") as workdir:
        prior = []
        for index, key in enumerate(DISCIPLINES, start=1):
            artifact = auto_output_path(output, index, key, workdir)
            context_file = Path(workdir) / f"{index:02d}-{key}.context.md"
            context_file.write_text(build_chained_context(briefing, prior), encoding="utf-8")
            rc = dispatch(key, briefing, phase, output=artifact, input_file=context_file)
            if rc != 0:
                print(f"\n❌ discipline {key} failed (exit {rc}) — stopping --auto; "
                      f"{len(DISCIPLINES) - index} discipline(s) not run.")
                return rc
            prior.append((key, artifact))
    if output:
        print("\n📄 Artifacts written:")
        for _, path in prior:
            print(f"  - {path}")
    return 0


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
        try:
            result = (estimate_from_json(args.sizing_file) if args.sizing_file
                      else compute_ucp())
        except (OSError, SizingError) as e:
            print(f"❌ Error: invalid sizing model: {e}")
            sys.exit(1)
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print_estimate(result)
        if args.output:
            import json
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return

    briefing = args.briefing
    if args.input_file:
        try:
            briefing = Path(args.input_file).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"❌ Error: cannot read --input file: {e}")
            sys.exit(1)
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
            print("🧪 DRY RUN — would dispatch, in sequence (each one receives the "
                  "artifacts of the previous ones):")
            for i, k in enumerate(DISCIPLINES, start=1):
                dest = auto_output_path(args.output, i, k, "<tmp>")
                print(f"  - {k} ({DISCIPLINES[k]['title']}) -> {dest}")
            return
        print("🚀 Dispatching all disciplines in sequence (chained)...\n")
        sys.exit(run_auto(briefing, args.phase, args.output))

    if args.dry_run and Agent is None:
        # --dry-run must not depend on crewai: show the plan from the definitions.
        print("🧪 DRY RUN — crewai is not installed, crew not built. Planned agents:")
        for data in AGENTS.values():
            print(f"  - {data['role']}")
        print("\n➡️  pip install crewai to build and run the crew.")
        return

    require_crewai()
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
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(str(result), encoding="utf-8")
        print(f"\n📄 Result written to {args.output}")


if __name__ == "__main__":
    main()
