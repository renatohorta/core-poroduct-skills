#!/usr/bin/env python3
"""
cp-test — RUP Test discipline (host-LLM, ADR-0012).

The agent running this skill is the LLM: this script prints the work packet
(roles, missions, required artifacts, briefing, earlier .context/ artifacts) and
records the agent's document into .context/ (mandatory, ADR-0011). Agents follow
Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.

Usage:
  python run.py "briefing" --phase Inception           # 1. print the work packet
  python run.py --record doc.md --phase Inception "briefing"   # 2. validate + write .context/
  python run.py --input briefing.md --phase Elaboration --context-dir path/.context

Test-value audit (ADR-0016) — measure whether the tests can catch a bug:
  python run.py "briefing" --audit [--files a.py b.py] [--workers N] [--budget 2h]
  python run.py --profile-template            # A0: profile.json fields
  python run.py --static-audit [DIR]          # A3: tests with no/trivial asserts, self-mocks
  python run.py --mutants --files a.py        # A4: count/list mutants (read-only)
  python run.py --mutate --files a.py [--lines a.py:10-40] [--workers N] [--budget 2h]
  python run.py --mutation-status             # progress of a (long) run
  python run.py --mutation-report             # A6: report.md + triage.md skeleton
  python run.py --triage-check                # A6: every survivor classified, with reasons
  python run.py --show-mutant a.py:IDX        # diff of one mutant
"""

import argparse
import json
import sys
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import context, discipline, mutation, testaudit  # noqa: E402
from _shared.rup import EXIT_USAGE, setup_console  # noqa: E402

# ═════════════════════════════════════════════════════════════════════════
# The Test discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'test',
 'title': 'Test',
 'agents': [{'slug': 'test-manager',
             'role': 'Test Manager',
             'goal': 'Produce the Test Plan, the Test Evaluation Summary and the Test '
                     'Value Assessment.',
             'backstory': 'Test manager who protects test independence: you scope the test '
                          'effort, allocate resources and milestones, and compile the '
                          'analytic Test Evaluation Summary with coverage, defect rates '
                          'and readiness.',
             'mission': 'Supervise the overall test success, guarantee the independence of '
                        'the quality assessment, and manage test resources and '
                        'consolidated reports.',
             'artifacts': ['Test Plan', 'Test Evaluation Summary', 'Test Value Assessment']},
            {'slug': 'test-analyst',
             'role': 'Test Analyst',
             'goal': 'Produce the Test Ideas List, Test Cases, Test Data and the Workload '
                     'Analysis Model.',
             'backstory': 'Test analyst who hunts for failure hypotheses: you derive test '
                          'cases directly from use cases and requirements, design the data '
                          'sets, and model the workload for performance testing.',
             'mission': 'Identify test ideas, design functional and stress test cases, and '
                        'define the verification data sets.',
             'artifacts': ['Test Ideas List',
                           'Test Cases',
                           'Test Data',
                           'Workload Analysis Model']},
            {'slug': 'test-designer',
             'role': 'Test Designer',
             'goal': 'Produce the Test Strategy, the Test Automation Architecture, the '
                     'Test Environment Configuration and the Test Interface Specification.',
             'backstory': 'Test designer who engineers the test architecture: you choose '
                          'the tooling, define the automation framework, specify the '
                          'environments, and state the testability requirements the '
                          'software must expose.',
             'mission': 'Design the technical architecture of the tests, define the '
                        'automation frameworks and specify the test interfaces.',
             'artifacts': ['Test Strategy',
                           'Test Automation Architecture',
                           'Test Environment Configuration',
                           'Test Interface Specification']},
            {'slug': 'tester',
             'role': 'Tester',
             'goal': 'Produce Test Scripts, Test Suites, the Test Log and the Test '
                     'Results.',
             'backstory': 'Tester who executes and records: you run automated and manual '
                          'test scripts, keep raw telemetry in the Test Log, and report '
                          'objective pass/fail results and regressions.',
             'mission': 'Execute automated and manual tests, document anomalous behavior '
                        'and log formal defect reports.',
             'artifacts': ['Test Scripts', 'Test Suites', 'Test Log', 'Test Results']}]}


TESTS_DIR = Path("tests")                # under .context/
MUTATION_DIR = TESTS_DIR / "mutation"
PROFILE = TESTS_DIR / "profile.json"

SPEC["instructions"] = [
    "Mandatory evidence — never write a number you did not measure. Run the project's "
    "suite (with coverage) yourself and paste, in the Test Log, for every execution: the "
    "exact command, the commit SHA, the duration and the result summary (passed/failed/"
    "skipped, coverage %). If you could not run it, say so; do not estimate.",
    "Coverage only says which lines ran, not whether a test would notice a wrong line. "
    "The Test Value Assessment states how the value of the tests was measured: the static "
    "audit and the mutation score per module (`--audit` protocol), real gaps with the test "
    "to write and its card, dead code with its CR, and the decision on equivalent mutants. "
    "Without an audit, write `not measured` and recommend the `--audit` run.",
    "The Test Evaluation Summary compares coverage × mutation score per module, lists the "
    "worst modules and the survivors per triage class (from the measured evidence below).",
]
SPEC["context_files"] = [str(TESTS_DIR / "baseline.md"), str(TESTS_DIR / "static-audit.md"),
                         str(MUTATION_DIR / "report.md"), str(MUTATION_DIR / "triage.md")]

# ═════════════════════════════════════════════════════════════════════════
# Test-value audit (ADR-0016): protocol A0–A8 and its deterministic tools
# ═════════════════════════════════════════════════════════════════════════

AUDIT_MODES = ("audit", "profile_template", "static_audit", "mutants", "mutate",
               "mutation_status", "mutation_report", "triage_check", "show_mutant")


def _me(*args) -> str:
    return discipline.cmdline([sys.executable, str(Path(__file__).resolve()), *args])


def project_root_of(args, context_dir) -> Path:
    return Path(args.project_root).resolve() if args.project_root \
        else Path(context_dir).resolve().parent


def audit_protocol(args, context_dir) -> None:
    cd = ["--context-dir", str(context_dir)]
    root = project_root_of(args, context_dir)
    files = args.files or ["<module.py> …"]
    extra = (["--workers", str(args.workers)] if args.workers else []) + \
        (["--budget", args.budget] if args.budget else [])
    ctx_tests = Path(context_dir) / TESTS_DIR
    briefing = (discipline.read_briefing(args, required=False) or "").strip()
    print("# Test-value audit — protocol A0–A8\n")
    print(f"- Project: `{root}`\n- Evidence goes to: `{ctx_tests}`\n- Commit: "
          f"`{mutation.head_sha(root)[:12] or 'unknown (no .git)'}`")
    if briefing:
        print(f"- Briefing: {briefing}")
    print("\nYou, the agent, run each step and keep its output. Rules: "
          "`references/audit.md` (protocol, runner pitfalls) and `references/triage.md` "
          "(classes). Long runs are resumable: re-run the same command; "
          f"`{_me('--mutation-status', *cd)}` shows progress.\n")
    steps = [
        ("A0 Profile the project",
         "Find the language, the runner (pytest, vitest, jest, go test…), the suite command, "
         "test dependencies (DB, queues) and how to isolate them per worker (own DB name). "
         f"Write `{ctx_tests / 'profile.json'}` (fields: `{_me('--profile-template')}`). "
         "Not Python? Use the ecosystem tool (Stryker, PIT, go-mutesting, cargo-mutants) with "
         "the same A0–A8 steps and write its results in the same JSONL format."),
        ("A1 Baseline",
         "Clean tree. Run the whole suite with coverage; record the command, commit SHA, "
         f"duration, totals and coverage % in `{ctx_tests / 'baseline.md'}`. A red baseline "
         "stops the audit: fix it first."),
        ("A2 Inventory",
         "Tests per suite/app, `autouse` fixtures, markers, what is mocked and how (requests "
         "monkeypatch, moto, fake queues). This goes into the Test Evaluation Summary."),
        ("A3 Static audit",
         f"`{_me('--static-audit', str(root), *cd)}` → `static-audit.md`. Fill the Verdict "
         "column (fix / legit + reason / delete)."),
        ("A4 Choose the modules",
         "By business risk (Risk List, business rules, security, money, concurrency) and size; "
         f"count the mutants: `{_me('--mutants', '--files', *files, *cd)}`. Write the "
         "choice and why in the Test Value Assessment."),
        ("A5 Mutation",
         f"`{_me('--mutate', '--files', *files, *extra, *cd)}` — isolated copies, own env "
         "per worker, the module's own tests first, timeout, resumable. Never edit the "
         "project while it runs (the run refuses a changed tree)."),
        ("A6 Triage",
         f"`{_me('--mutation-report', *cd)}` → `report.md` + `triage.md`. Classify every "
         "survivor (equivalent / real gap / dead code / out of scope) with its reason, then "
         f"`{_me('--triage-check', *cd)}` until it passes."),
        ("A7 Action",
         "Real gap → a task card with the test to write: "
         "`cp-backlog --new task --source cp-test#mutation:<module>:<line> …`; write the test, "
         f"then `{_me('--mutate', '--rerun-survivors', '--files', *files, *cd)}`: the mutant must "
         "die. Dead code → a simplification CR (cp-ccm), not a test."),
        ("A8 Record",
         "Write the cp-test document (its packet embeds the evidence above): Test Evaluation "
         "Summary with coverage × mutation per module, Test Value Assessment, Test Log with "
         f"command/SHA/duration. Packet: `{_me(briefing or '<briefing>', '--phase', args.phase, *cd)}`"),
    ]
    for title, text in steps:
        print(f"## {title}\n\n{text}\n")


def _out_dir(context_dir) -> Path:
    return Path(context_dir) / MUTATION_DIR


def _write(context_dir, rel: Path, text: str) -> Path:
    context.ensure_writable(context_dir)
    path = Path(context_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_audit_mode(args, context_dir) -> int:
    root = project_root_of(args, context_dir)

    if args.profile_template:
        print(json.dumps(mutation.PROFILE_TEMPLATE, indent=2))
        print("\n" + mutation.TEMPLATE_HELP)
        return 0

    if args.audit:
        audit_protocol(args, context_dir)
        return 0

    if args.static_audit:
        target = Path(args.static_audit if args.static_audit != "." else root).resolve()
        result = testaudit.audit(target)
        text = testaudit.render(result, target, mutation.head_sha(root))
        path = _write(context_dir, TESTS_DIR / "static-audit.md", text)
        print(text)
        context.append_event(context_dir, skill="cp-test",
                             what=f"static test audit: {len(result['findings'])} finding(s)")
        print(f"🗂️  Written to {path}")
        return 0

    if args.show_mutant:
        f, _, idx = args.show_mutant.rpartition(":")
        if not f or not idx.isdigit():
            discipline.fail("--show-mutant needs FILE:IDX (IDX from results/triage `#`)")
        src = (root / f).read_text(encoding="utf-8")
        cand = next((c for c in mutation.candidates(src) if c[0] == int(idx)), None)
        if cand is None:
            discipline.fail(f"{f} has no mutant #{idx}")
        print(f"# {f} #{idx} line {cand[3]}: {cand[4]}\n")
        print(mutation.show(src, cand, f))
        return 0

    if args.mutation_status:
        print(mutation.status_text(_out_dir(context_dir)))
        return 0

    if args.mutation_report:
        context.ensure_writable(context_dir)
        try:
            text = mutation.report(_out_dir(context_dir))
        except mutation.RunError as e:
            discipline.fail(str(e))
        path = _write(context_dir, MUTATION_DIR / "report.md", text)
        triage, added = mutation.triage_skeleton(_out_dir(context_dir), root.name)
        print(text)
        print(f"🗂️  Report: {path}\n🗂️  Triage: {triage} ({added} new survivor row(s) to classify)")
        context.append_event(context_dir, skill="cp-test", what="mutation report generated")
        return 0

    if args.triage_check:
        problems, notes = mutation.triage_check(_out_dir(context_dir))
        for n in notes:
            print(f"ℹ️  {n}")
        if problems:
            print("Triage incomplete:")
            for p in problems:
                print(f"- {p}")
            return EXIT_USAGE
        print("Triage OK: every survivor is classified with its reason and action.")
        return 0

    try:
        lines = mutation.parse_lines(args.lines)
    except ValueError as e:
        discipline.fail(str(e))
    files = list(dict.fromkeys((args.files or []) + list(lines)))
    if not files:
        discipline.fail("give the modules with --files (or --lines FILE:START-END)")

    if args.mutants:
        total = 0
        for f in files:
            path = root / f
            if not path.is_file():
                discipline.fail(f"{f}: not found under {root}")
            cands = [c for c in mutation.candidates(path.read_text(encoding="utf-8"))
                     if mutation.in_ranges(c[3], lines.get(f) if f in lines else None)]
            total += len(cands)
            print(f"{len(cands):6d}  {f}")
            if args.verbose:
                for c in cands:
                    print(f"        #{c[0]} line {c[3]}: {c[4]}")
        print(f"{total:6d}  total")
        return 0

    # --mutate
    context.ensure_writable(context_dir)
    try:
        profile = mutation.load_profile(args.profile or Path(context_dir) / PROFILE)
        budget = mutation.parse_budget(args.budget)
        result = mutation.run(profile, project_root=root, out_dir=_out_dir(context_dir),
                              files=[f for f in files if f not in lines], lines=lines,
                              workers=args.workers, budget_s=budget, fresh=args.fresh,
                              workdir=args.workdir, rerun_survivors=args.rerun_survivors,
                              log=lambda m: print(m, flush=True))
    except (mutation.ProfileError, mutation.RunError, ValueError) as e:
        discipline.fail(str(e))
    context.append_event(context_dir, skill="cp-test",
                         what=f"mutation run: {result['ran']} mutant(s) run, {result['left']} left")
    print()
    print(mutation.status_text(_out_dir(context_dir)))
    print(f"\nNext: {_me('--mutation-report', '--context-dir', str(context_dir))}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="RUP Test — work packet for the host agent (the LLM), recorder, and the "
                    "test-value audit tools (static audit, mutation, triage)")
    discipline.add_common_args(parser)
    a = parser.add_argument_group("test-value audit (ADR-0016)")
    a.add_argument("--audit", action="store_true", help="print the audit protocol A0–A8")
    a.add_argument("--profile-template", action="store_true", help="print a profile.json to fill")
    a.add_argument("--static-audit", nargs="?", const=".", metavar="DIR",
                   help="audit every test under DIR (default: project root)")
    a.add_argument("--mutants", action="store_true", help="count the mutants of --files")
    a.add_argument("--mutate", action="store_true", help="run the mutants of --files/--lines")
    a.add_argument("--mutation-status", action="store_true", help="progress of the mutation run")
    a.add_argument("--mutation-report", action="store_true",
                   help="write report.md and the triage.md skeleton")
    a.add_argument("--triage-check", action="store_true", help="validate triage.md")
    a.add_argument("--show-mutant", metavar="FILE:IDX", help="diff of one mutant")
    a.add_argument("--files", nargs="+", metavar="FILE", help="modules, relative to the project root")
    a.add_argument("--lines", action="append", metavar="FILE:START-END",
                   help="only mutants on these lines (repeatable; e.g. a task's diff)")
    a.add_argument("--workers", type=int, help="parallel copies (default: profile, else cores-1)")
    a.add_argument("--budget", help="stop starting mutants after this time (2h, 30m); resumable")
    a.add_argument("--fresh", action="store_true", help="discard the previous run and start over")
    a.add_argument("--rerun-survivors", action="store_true",
                   help="run the survivors again (after writing the missing tests)")
    a.add_argument("--profile", help="profile JSON (default: .context/tests/profile.json)")
    a.add_argument("--workdir", help="where the worker copies go (default: system temp)")
    a.add_argument("--project-root", help="project root (default: parent of .context/)")
    a.add_argument("--verbose", action="store_true", help="with --mutants: list every mutant")
    args = parser.parse_args(argv)

    if any(getattr(args, m) for m in AUDIT_MODES):
        if args.record:
            discipline.fail("--record cannot be combined with the audit options")
        if args.profile_template:
            return run_audit_mode(args, None)
        return run_audit_mode(args, context.resolve_context_dir(args.context_dir))
    discipline.run(SPEC, args, script=__file__)
    return 0


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
