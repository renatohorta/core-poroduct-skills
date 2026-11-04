"""
router.py — The front door of the cp-* skills: route a plain request to the right skill.

The user talks to the agent in their own words ("quero uma tela de login",
"o checkout quebrou", "revisa o TK-012"); they should never have to know which
cp-* skill to call. `cp-orchestrator --route "<request>"` prints a routing
packet: the project state read from `.context/`, a suggested next step, the
table of routes with the exact command of each, and the standard chains. The
agent (the LLM, ADR-0012) classifies the request and runs the commands itself.

Classification is the agent's job, not this module's: no keyword matching here.
This module only reads `.context/` (never writes) and renders the packet.

Pure standard library.
"""
from dataclasses import dataclass, field
from pathlib import Path

from _shared import context as ctx
from _shared.rup import DISCIPLINES, ORCHESTRATOR_SKILL, PHASES

REQUIREMENTS_SKILL = "cp-requirements"
DISCOVER_SKILL = "cp-discover"
OPEN_COLUMNS = ("1-backlog", "2-todo", "3-doing", "4-review", "5-testing", "blocked")


@dataclass
class State:
    context_dir: Path
    authorized: bool
    discovery: str = ""                              # phase where it is recorded, "" = none
    governance: list = field(default_factory=list)   # phases with governance recorded
    requirements: list = field(default_factory=list)
    columns: dict = field(default_factory=dict)      # column -> [card ids]
    open_bugs: list = field(default_factory=list)
    card_error: str = ""


def _recorded(context_dir, skill):
    return [p for p in PHASES if ctx.artifact_path(context_dir, p, skill).is_file()]


def read_state(context_dir) -> State:
    """What `.context/` says about the project. Read-only, never fails."""
    context_dir = Path(context_dir)
    st = State(context_dir, ctx.has_consent(context_dir))
    discovery = _recorded(context_dir, DISCOVER_SKILL)
    st.discovery = discovery[0] if discovery else ""
    st.governance = _recorded(context_dir, ORCHESTRATOR_SKILL)
    st.requirements = _recorded(context_dir, REQUIREMENTS_SKILL)
    try:
        from _shared import cards
        loaded = cards.load_all(context_dir)
    except (SystemExit, Exception) as e:  # a broken card must not break routing
        st.card_error = str(e) or type(e).__name__
        loaded = {}
    for card in loaded.values():
        st.columns.setdefault(card.status, []).append(card.id)
        if card.type == "bug" and card.status in OPEN_COLUMNS:
            st.open_bugs.append(card.id)
    for ids in st.columns.values():
        ids.sort()
    st.open_bugs.sort()
    return st


def _cards(st, column):
    return st.columns.get(column, [])


def _tasks(ids):
    return [i for i in ids if i.startswith(("TK-", "BUG-"))]


def suggest(st: State):
    """(route key, why) — the next step the state points to. The request wins over it."""
    if not st.authorized:
        return "context", ".context/ is not authorized yet: ask the user, then init it"
    review = _cards(st, "4-review")
    if review:
        return "review", f"delivered and waiting for review: {', '.join(review)}"
    doing = _tasks(_cards(st, "3-doing"))
    if doing:
        return "build", f"in progress: {', '.join(doing)} (finish it before starting another)"
    bugs = [b for b in st.open_bugs if b in _cards(st, "1-backlog") + _cards(st, "2-todo")]
    if bugs:
        return "debug", f"open bugs: {', '.join(bugs)}"
    if not st.discovery:
        return "discover", "no discovery recorded: start by understanding the problem"
    if not st.requirements:
        return "requirements", "discovery recorded, no requirements yet"
    if not any(st.columns.values()):
        return "backlog", "requirements recorded, no cards yet: derive the backlog"
    todo = _tasks(_cards(st, "2-todo"))
    if todo:
        return "build", f"ready to build: {', '.join(todo)}"
    if _tasks(_cards(st, "1-backlog")):
        return "backlog", "tasks only in 1-backlog: plan the iteration (move them to 2-todo)"
    return "status", "nothing pending: ask the user what is next"


def routes(cmd):
    """[(key, when the user..., what the route does, command)]. `cmd(skill, *args)` builds a line."""
    return [
        ("context", "is starting on a project; any skill exits 5 (not authorized)",
         "Ask the user to authorize `.context/`, then init it",
         cmd("cp-context", "--init", "--authorized-by", "<user name>")),
        ("discover", "has a new idea, product, feature or epic that is still fuzzy",
         "Discovery conversation (one question per message), confirmed playback, record",
         cmd(DISCOVER_SKILL, "<request>")),
        ("requirements", "wants a vision, use cases, SRS, FURPS, glossary",
         "Requirements discipline packet (builds on the discovery)",
         cmd(ORCHESTRATOR_SKILL, "<request>", "--discipline", "requirements",
             "--phase", "Inception")),
        ("discipline", "wants architecture, design, business model, test plan, CM/CR, "
                       "deployment/release docs, process tailoring",
         "That discipline's packet (key: " + ", ".join(DISCIPLINES) + ")",
         cmd(ORCHESTRATOR_SKILL, "<request>", "--discipline", "<key>", "--phase", "<phase>")),
        ("governance", "wants a plan, phase, iteration, risks, business case, work orders",
         "Governance packet (SDP, Business Case, Risk List, Iteration Plan, Work Orders)",
         cmd(ORCHESTRATOR_SKILL, "<request>", "--phase", "<phase>")),
        ("iteration", "wants the whole RUP iteration documented end to end",
         "Protocol: governance + 8 disciplines, in order",
         cmd(ORCHESTRATOR_SKILL, "<request>", "--auto", "--phase", "<phase>")),
        ("estimate", "asks how big / how long (sizing, effort, UCP)",
         "Fill the sizing model, then compute UCP (never compute it yourself)",
         cmd(ORCHESTRATOR_SKILL, "--estimate", "--sizing", "sizing.json", "--phase", "<phase>")),
        ("backlog", "wants epics/stories/tasks, to break work down, plan an iteration, "
                    "the roadmap, or to move/list cards",
         "Derive cards from the requirements, create/move/plan cards",
         cmd("cp-backlog", "--derive", "--phase", "<phase of the requirements>") + "` · `" + cmd("cp-backlog", "--list")),
        ("build", "wants a task implemented (TK-NNN) or 'build the next thing'",
         "Start (TDD packet), implement test-first, finish with a delivery",
         cmd("cp-build", "--start", "<TK-NNN>")),
        ("debug", "reports a bug, a regression, an error, unexpected behavior",
         "Open a BUG card, reproduce, failing test, root cause, fix via cp-build",
         cmd("cp-debug", "--open", "--title", "<symptom>", "--doc", "-")),
        ("review", "wants a delivered card reviewed (a card in 4-review)",
         "Checklist packet, then record approved / changes requested",
         cmd("cp-review", "<ID>")),
        ("test-audit", "asks whether the tests are any good, coverage vs real value, mutation",
         "Test-value audit protocol A0–A8 (static audit, mutation, triage)",
         cmd("cp-test", "<request>", "--audit")),
        ("status", "asks where the project is, what is pending, what to do next",
         "Recorded artifacts + board",
         cmd(ORCHESTRATOR_SKILL, "--status", "--phase", "<phase>") + "` · `"
         + cmd("cp-backlog", "--list")),
    ]


CHAINS = [
    ("New product / feature / epic",
     "discover → requirements (Inception) → backlog --derive --phase Inception → "
     "[user confirms the cards] "
     "→ build each task → review each delivery"),
    ("Bug", "debug --open → reproduce + failing test → debug --diagnose → build --start BUG-NNN "
            "→ build --finish → review"),
    ("Small, clear change to an existing feature",
     "backlog --new task (under its story) → build → review — no discovery needed"),
    ("“Are our tests worth anything?”",
     "test-audit (profile → baseline → static audit → mutation → triage) → backlog cards "
     "for the real gaps → build them"),
    ("Formal RUP documentation of a phase", "iteration (--auto) → each step in order"),
]

GATES = [
    "authorizing `.context/` (exit 5) — never run `cp-context --init` without the user's yes;",
    "the discovery conversation — the user answers and confirms the playback;",
    "confirming the cards derived from the requirements before building them;",
    "a real ambiguity between two routes — ask ONE short question, with your suggestion;",
    "anything destructive or outward-facing (push, deploy, deleting work).",
]


def render(request, st: State, cmd, phase_hint="Inception") -> str:
    key, why = suggest(st)
    lines = [
        "# Routing packet — cp-orchestrator (the front door)",
        "",
        "You, the agent, are the router. The user talks to you in plain words and must "
        "**never** have to name or call a cp-* skill.",
        "",
        "## The request",
        "",
        (request or "(no request: the user wants to know what is next)").strip(),
        "",
        f"## Project state — `{st.context_dir}`",
        "",
        f"- `.context/` authorized: {'yes' if st.authorized else 'NO (route: context)'}",
        f"- Discovery: {('recorded (' + st.discovery + ')') if st.discovery else 'not recorded'}",
        f"- Requirements: {', '.join(st.requirements) if st.requirements else 'not recorded'}",
        f"- Governance: {', '.join(st.governance) if st.governance else 'not recorded'}",
    ]
    if st.card_error:
        lines.append(f"- Cards: could not be read ({st.card_error}) — fix with cp-backlog")
    elif any(st.columns.values()):
        board = "; ".join(f"{c}: {', '.join(ids)}" for c, ids in st.columns.items() if ids)
        lines.append(f"- Board: {board}")
    else:
        lines.append("- Board: no cards")
    if st.open_bugs:
        lines.append(f"- Open bugs: {', '.join(st.open_bugs)}")
    lines += [
        "",
        f"**State suggests**: `{key}` — {why}. The user's request wins over the "
        "suggestion; use the suggestion when the request is vague (\"what now?\", "
        "\"continue\").",
        "",
        "## How to route",
        "",
        "1. Classify the request into ONE route below, or a chain (next section). Choose "
        f"the phase from the state (default {phase_hint} for new work, Construction for "
        "build/debug/review).",
        "2. Tell the user in one line what you will do (\"Vou começar pela discovery…\"), "
        "then **run the route's command yourself** and follow the packet it prints.",
        "3. When a step is recorded, continue with the next step of the chain on your own. "
        "Re-run this `--route` command when unsure where you are.",
        "4. Stop and talk to the user only at the gates:",
    ]
    lines += [f"   - {g}" for g in GATES]
    lines += [
        "5. Never tell the user \"call cp-xxx\": if a skill is needed, you call it.",
        "",
        "## Routes",
        "",
        "| Route | When the user… | What it does | Command |",
        "|---|---|---|---|",
    ]
    for k, when, what, command in routes(cmd):
        mark = " ⭐" if k == key else ""
        lines.append(f"| `{k}`{mark} | {when} | {what} | `{command}` |")
    lines += ["", "## Chains (run the steps in order, without asking the user to)", ""]
    lines += [f"- **{name}**: {steps}" for name, steps in CHAINS]
    return "\n".join(lines).rstrip() + "\n"
