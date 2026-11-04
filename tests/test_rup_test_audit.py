"""cp-test test-value audit (ADR-0016): static audit, mutants, runner, report, triage."""
import ast
import json
import sys
from pathlib import Path

import pytest

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE, full_document, load_skill
from test_context_persistence import run_skill

from _shared import cards, mutation, testaudit, testcheck

SKILL = "cp-test"

# ─── a tiny project: one module, a test script run as `python -S tests/check.py` ──

CALC = ("def discount(total, vip):\n"
        "    if vip and total > 100:\n"
        "        return total * 0.9\n"
        "    return total\n")
# Kills the comparison/negation mutants but not the boundary (100 -> 101).
CHECK = ("import sys\nsys.path.insert(0, '.')\nfrom app.calc import discount\n"
         "assert discount(200, True) == 180\nassert discount(200, False) == 200\n")
BOUNDARY = "assert discount(101, True) != 101\nassert discount(100, True) == 100\n"


def make_project(root: Path, check=CHECK) -> Path:
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "app" / "calc.py").write_text(CALC, encoding="utf-8")
    (root / "tests" / "check.py").write_text(check, encoding="utf-8")
    return root


def profile(**extra):
    p = {"test_command": [sys.executable, "-S", "tests/check.py"], "workers": 2,
         "timeout_factor": 1, "timeout_extra_s": 5}
    p.update(extra)
    return _load(p)


def _load(data):
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(data, fh)
    try:
        return mutation.load_profile(fh.name)
    finally:
        Path(fh.name).unlink()


def run_mutation(root, out, **kw):
    kw.setdefault("files", ["app/calc.py"])
    return mutation.run(kw.pop("prof", None) or profile(), project_root=root, out_dir=out,
                        workdir=root.parent / "work", log=lambda m: None, **kw)


@pytest.fixture
def project(tmp_path):
    return make_project(tmp_path / "proj"), tmp_path / "out"


# ─── mutant generator ────────────────────────────────────────────────────

def descs(src):
    return [c[4] for c in mutation.candidates(src)]


def test_candidates_cover_each_kind_and_every_mutant_compiles():
    src = ("def f(a, b, xs):\n"
           "    if a > 1 and not b:\n"
           "        a += 2\n"
           "        g(a)\n"
           "        return a - 1\n"
           "    return a in xs or True\n")
    cands = mutation.candidates(src)
    kinds = {c[1] for c in cands}
    assert {"cmp", "bool", "unnot", "aug", "bin", "bool_const", "int", "negif",
            "retnone", "delcall"} <= kinds
    for c in cands:
        mutated = mutation.apply(src, c)
        ast.parse(mutated)
        assert mutated != ast.unparse(ast.parse(src)), c


def test_apply_changes_exactly_the_described_operator():
    src = "def f(a):\n    return a > 1\n"
    cand = next(c for c in mutation.candidates(src) if c[1] == "cmp")
    assert cand[4] == "Gt -> LtE"
    assert "a <= 1" in mutation.apply(src, cand)


def test_log_and_print_calls_and_annotations_are_not_mutated():
    src = ("import logging\nlogger = logging.getLogger()\n"
           "def f(x: 'Literal[7]') -> int:\n"
           "    logger.info('x')\n    print(x)\n    y: int = 5\n    return y\n")
    d = descs(src)
    assert not any(x.startswith("remove call") for x in d)
    assert "5 -> 6" in d and "7 -> 8" not in d


def test_parse_lines_and_ranges_filter_mutants():
    lines = mutation.parse_lines(["a.py:2-3", "a.py:9", "b.py"])
    assert lines == {"a.py": [(2, 3), (9, 9)], "b.py": None}
    assert mutation.in_ranges(3, lines["a.py"]) and not mutation.in_ranges(5, lines["a.py"])
    assert mutation.in_ranges(99, lines["b.py"])
    with pytest.raises(ValueError):
        mutation.parse_lines(["a.py:9-2"])


def test_show_gives_a_readable_diff_of_one_mutant():
    cand = next(c for c in mutation.candidates(CALC) if c[4] == "100 -> 101")
    diff = mutation.show(CALC, cand, "app/calc.py")
    assert "-    if vip and total > 100:" in diff and "+    if vip and total > 101:" in diff


# ─── runner ──────────────────────────────────────────────────────────────

def test_run_classifies_mutants_and_leaves_the_project_untouched(project):
    root, out = project
    result = run_mutation(root, out)
    assert result["ran"] == result["total"] > 0
    results = mutation.load_results(out / "results.jsonl")
    by_desc = {r["desc"]: r["status"] for r in results.values()}
    assert by_desc["Gt -> LtE"] == "killed"
    assert by_desc["100 -> 101"] == "survived"  # the boundary nobody tests
    assert (root / "app" / "calc.py").read_text(encoding="utf-8") == CALC


def test_run_resumes_without_rerunning_finished_mutants(project):
    root, out = project
    first = run_mutation(root, out)
    lines = (out / "results.jsonl").read_text(encoding="utf-8").splitlines()
    again = run_mutation(root, out)
    assert again["ran"] == 0 and first["ran"] == len(lines)
    assert (out / "results.jsonl").read_text(encoding="utf-8").splitlines() == lines


def test_run_refuses_when_code_under_test_changed_until_fresh(project):
    root, out = project
    run_mutation(root, out)
    (root / "app" / "calc.py").write_text(CALC + "\nX = 1\n", encoding="utf-8")
    with pytest.raises(mutation.RunError, match="changed"):
        run_mutation(root, out)
    assert run_mutation(root, out, fresh=True)["ran"] > 0


def test_new_test_plus_rerun_survivors_kills_the_gap(project):
    root, out = project
    run_mutation(root, out)
    (root / "tests" / "check.py").write_text(CHECK + BOUNDARY, encoding="utf-8")  # test-only edit
    run_mutation(root, out, rerun_survivors=True)
    by_desc = {r["desc"]: r["status"] for r in mutation.load_results(out / "results.jsonl").values()}
    assert by_desc["100 -> 101"] == "killed"


def test_failing_baseline_aborts_before_any_mutant(project):
    root, out = project
    (root / "tests" / "check.py").write_text(CHECK + "assert False\n", encoding="utf-8")
    with pytest.raises(mutation.RunError, match="baseline failed"):
        run_mutation(root, out)
    assert not (out / "results.jsonl").exists()


def test_other_exit_codes_are_errors_not_kills(project):
    root, out = project
    (root / "tests" / "check.py").write_text(
        CHECK.replace("assert discount(200, True) == 180",
                      "if discount(200, True) != 180: sys.exit(3)"), encoding="utf-8")
    run_mutation(root, out)
    statuses = {r["status"] for r in mutation.load_results(out / "results.jsonl").values()}
    assert "error3" in statuses
    report = mutation.report(out)
    assert "Errors (collection/usage" in report


def test_infinite_loop_mutant_times_out_and_counts_as_detected(tmp_path):
    root = tmp_path / "proj"
    (root / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "app" / "loop.py").write_text(
        "def countdown(n):\n    while n > 0:\n        n -= 1\n    return n\n", encoding="utf-8")
    (root / "tests" / "check.py").write_text(
        "import sys\nsys.path.insert(0, '.')\nfrom app.loop import countdown\n"
        "assert countdown(3) == 0\n", encoding="utf-8")
    out = tmp_path / "out"
    mutation.run(profile(timeout_extra_s=2), project_root=root, out_dir=out,
                 files=["app/loop.py"], lines={"app/loop.py": [(3, 3)]},
                 workdir=tmp_path / "work", log=lambda m: None)
    results = mutation.load_results(out / "results.jsonl").values()
    rec = next(r for r in results if r["kind"] == "aug")
    assert rec["desc"] == "Sub= -> Add=" and rec["status"] == "timeout"
    assert mutation.detected(rec["status"])


def test_budget_leaves_mutants_for_the_next_run(project):
    root, out = project
    result = run_mutation(root, out, budget_s=1e-9)
    assert result["ran"] == 0 and result["left"] == result["total"]
    assert run_mutation(root, out)["ran"] == result["total"]


def test_lines_restrict_the_run_to_the_changed_lines(project):
    root, out = project
    result = run_mutation(root, out, files=[], lines={"app/calc.py": [(2, 2)]})
    assert {r["line"] for r in mutation.load_results(out / "results.jsonl").values()} == {2}
    assert result["ran"] == result["total"]


def test_head_sha_reads_git_files_without_running_git(tmp_path):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="utf-8")
    assert mutation.head_sha(tmp_path) == "a" * 40
    (git / "refs" / "heads" / "main").unlink()
    (git / "packed-refs").write_text(f"{'b' * 40} refs/heads/main\n", encoding="utf-8")
    assert mutation.head_sha(tmp_path) == "b" * 40
    (git / "HEAD").write_text("c" * 40 + "\n", encoding="utf-8")
    assert mutation.head_sha(tmp_path) == "c" * 40
    assert mutation.head_sha(tmp_path / "nowhere") == ""


def test_profile_needs_a_test_command(tmp_path):
    p = tmp_path / "profile.json"
    p.write_text(json.dumps({"workers": 2}), encoding="utf-8")
    with pytest.raises(mutation.ProfileError, match="test_command"):
        mutation.load_profile(p)
    with pytest.raises(mutation.ProfileError, match="no profile"):
        mutation.load_profile(tmp_path / "missing.json")


def test_command_expands_python_and_tests_placeholders():
    prof = _load({"test_command": ["{python}", "-m", "pytest", "{tests}", "-q"]})
    assert mutation.command(prof, "/py", ["t1", "t2"]) == ["/py", "-m", "pytest", "t1", "t2", "-q"]
    prof = _load({"test_command": ["{python}", "-m", "pytest"]})
    assert mutation.command(prof, "/py", ["t1"]) == ["/py", "-m", "pytest", "t1"]


# ─── report and triage ───────────────────────────────────────────────────

def test_report_scores_modules_and_triage_skeleton_lists_only_survivors(project):
    root, out = project
    run_mutation(root, out)
    results = mutation.load_results(out / "results.jsonl")
    row = mutation.summarize(results)["app/calc.py"]
    assert row["score"] == round(100 * (row["killed"] + row["timeout"])
                                 / (row["killed"] + row["timeout"] + row["survived"]))
    assert f"| `app/calc.py` | {row['mutants']} |" in mutation.report(out)
    path, added = mutation.triage_skeleton(out, "proj")
    survivors = [r for r in results.values() if r["status"] == "survived"]
    assert added == len(survivors) == len(mutation.triage_rows(path.read_text(encoding="utf-8")))
    assert mutation.triage_skeleton(out, "proj")[1] == 0  # rows are not duplicated


def fill(out, fn):
    path = out / "triage.md"
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = mutation._cells(line) if line.startswith("|") else []
        if len(cells) >= 7 and cells[1].isdigit():
            cls, reason, action = fn(cells)
            line = "| " + " | ".join(cells[:4] + [cls, reason, action]) + " |"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_triage_check_enforces_the_rules(project):
    root, out = project
    run_mutation(root, out)
    mutation.triage_skeleton(out)
    problems, _ = mutation.triage_check(out)
    assert problems and all("class ''" in p for p in problems)

    fill(out, lambda c: ("equivalent", "", "—"))
    assert any("needs the reason" in p for p in mutation.triage_check(out)[0])
    fill(out, lambda c: ("real gap", "vip total 101 is not discounted and no test fails", "write it"))
    assert any("TK-/BUG-" in p for p in mutation.triage_check(out)[0])
    fill(out, lambda c: ("dead code", "no caller reads this value (grep shows none)", "—"))
    assert any("CR" in p for p in mutation.triage_check(out)[0])

    fill(out, lambda c: ("real gap", "vip total 101 is not discounted and no test fails", "TK-007"))
    problems, notes = mutation.triage_check(out)
    assert problems == []
    assert any("still open" in n for n in notes)


def test_triage_check_flags_a_new_survivor_without_a_row(project):
    root, out = project
    run_mutation(root, out)
    mutation.triage_skeleton(out)
    fill(out, lambda c: ("out of scope", "only changes formatting of the result", "—"))
    assert mutation.triage_check(out)[0] == []
    rec = {"file": "app/calc.py", "idx": 999, "line": 4, "kind": "retnone",
           "desc": "return None", "status": "survived"}
    with (out / "results.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    assert any("#999" in p and "not triaged" in p for p in mutation.triage_check(out)[0])


# ─── static audit ────────────────────────────────────────────────────────

AUDITED = '''
from unittest import mock
import pytest
from app.service import compute, report


def _check(x):
    assert x == 3


def test_good():
    assert compute(1) == 3


def test_helper_counts_as_assertion():
    _check(compute(1))


def test_trivial():
    compute(1)
    assert True


def test_no_assert():
    compute(1)


def test_constant_only():
    assert 1 == 1


def test_mocks_its_own_unit():
    with mock.patch("app.service.compute", return_value=3):
        assert report() == "3"


def test_mocks_a_dependency_is_fine():
    with mock.patch("app.service.requests"):
        assert report() == "3"


class TestThing:
    @mock.patch("app.service.compute")
    def test_decorated_self_mock(self, m):
        assert report() == "3"

    def test_raises(self):
        with pytest.raises(ValueError):
            compute(-1)
'''
SERVICE = "import requests\n\ndef compute(x):\n    return x + 2\n\ndef report():\n    return str(compute(1))\n"


def test_static_audit_flags_tests_that_cannot_catch_a_bug(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "service.py").write_text(SERVICE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_service.py").write_text(AUDITED, encoding="utf-8")
    result = testaudit.audit(tmp_path)
    found = {(k, t) for k, _, _, t, _ in result["findings"]}
    assert result["tests"] == 9
    assert ("TRIVIAL_ASSERT", "test_trivial") in found
    assert ("NO_ASSERT", "test_no_assert") in found
    assert ("TRIVIAL_ASSERT", "test_constant_only") in found
    assert ("NO_PROJECT_CALL", "test_constant_only") in found
    assert ("SELF_MOCK", "test_mocks_its_own_unit") in found
    assert ("SELF_MOCK", "TestThing::test_decorated_self_mock") in found
    clean = {"test_good", "test_helper_counts_as_assertion", "test_mocks_a_dependency_is_fine",
             "TestThing::test_raises"}
    assert not {t for _, t in found} & clean
    md = testaudit.render(result, tmp_path)
    assert "| SELF_MOCK | `tests/test_service.py:" in md and "Verdict" in md


# ─── CLI and packet ──────────────────────────────────────────────────────

def test_packet_requires_value_assessment_and_measured_evidence(ctx_env, python_cmd, tmp_path):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    (ctx / "tests").mkdir(parents=True, exist_ok=True)
    (ctx / "tests" / "static-audit.md").write_text("# Static test audit — MARKER-42\n",
                                                   encoding="utf-8")
    r = run_skill(SKILL, ["briefing", "--phase", "Construction"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "Test Value Assessment" in r.stdout
    assert "never write a number you did not measure" in r.stdout
    assert "Measured evidence" in r.stdout and "MARKER-42" in r.stdout

    spec = load_skill(SKILL).SPEC
    doc = tmp_path / "doc.md"
    doc.write_text(full_document(spec).replace("## Test Value Assessment", "## Other"),
                   encoding="utf-8")
    r = run_skill(SKILL, ["--record", str(doc), "--phase", "Construction"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE and "Test Value Assessment" in r.stdout


def test_audit_protocol_lists_steps_with_commands_and_writes_nothing(ctx_env, python_cmd):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    before = sorted(p for p in ctx.rglob("*"))
    r = run_skill(SKILL, ["are the tests good?", "--audit", "--files", "app/calc.py"],
                  ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    for step in ("A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"):
        assert f"## {step} " in r.stdout
    assert "--mutate --files app/calc.py" in r.stdout and "--triage-check" in r.stdout
    assert sorted(p for p in ctx.rglob("*")) == before


def test_cli_end_to_end_mutate_report_triage(ctx_env, python_cmd):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    root = make_project(ctx.parent)
    (ctx / "tests").mkdir(exist_ok=True)
    (ctx / "tests" / "profile.json").write_text(json.dumps(
        {"test_command": [sys.executable, "-S", "tests/check.py"], "workers": 1}),
        encoding="utf-8")
    args = ["--workdir", str(ctx.parent.parent / "work")]
    r = run_skill(SKILL, ["--mutate", "--files", "app/calc.py", *args], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "score" in r.stdout
    r = run_skill(SKILL, ["--mutation-report"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK and (ctx / "tests" / "mutation" / "report.md").is_file()
    r = run_skill(SKILL, ["--triage-check"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE and "Triage incomplete" in r.stdout
    r = run_skill(SKILL, ["--static-audit"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK and (ctx / "tests" / "static-audit.md").is_file()
    log = (ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8")
    assert "mutation run" in log and "static test audit" in log
    assert (root / "app" / "calc.py").read_text(encoding="utf-8") == CALC


def test_writing_audit_commands_need_authorization(clean_env, python_cmd, tmp_path):
    env = dict(clean_env)
    env["RUP_CONTEXT_DIR"] = str(tmp_path / ".context")
    make_project(tmp_path)
    for args in (["--static-audit"], ["--mutate", "--files", "app/calc.py"]):
        r = run_skill(SKILL, args, env, python_cmd)
        assert r.returncode == EXIT_NEEDS_CONSENT, (args, r.stdout + r.stderr)
    assert not (tmp_path / ".context" / "tests").exists()


# ─── integration with cp-build / cp-review / cp-debug ────────────────────

EPIC = "## Goal\n\nG.\n\n## Scope\n\nS.\n"
STORY = ("## User story\n\nAs a user I want X so that Y.\n\n"
         "## Acceptance criteria\n\n- It works\n\n## Definition of Done\n\n- Tests pass\n")
TASK = "## Description\n\nDo it.\n\n## Target files\n\n- app/calc.py\n\n## Covers\n\n- ST-001/AC-1\n"
REF = "tests/test_calc.py::test_discount_st_001_ac_1"
DELIVERY = ("## What was done\n\nDiscount.\n\n## Files changed\n\n- app/calc.py\n\n"
            f"## Tests\n\n- {REF} — covers ST-001/AC-1\n\n"
            f"## Red evidence\n\n### {REF}\n\n```\nE   ImportError\n```\n")
MUTATION = "\n## Mutation\n\napp/calc.py:1-4 — 9 mutants, 9 killed (100%).\n"


@pytest.fixture
def task(ctx_env):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    root = make_project(ctx.parent)
    (root / "tests" / "test_calc.py").write_text(
        "from app.calc import discount\n\n\ndef test_discount_st_001_ac_1():\n"
        "    assert discount(200, True) == 180\n", encoding="utf-8")
    cards.create(ctx, "epic", "E", EPIC)
    cards.create(ctx, "story", "S", STORY, parent="EP-001")
    cards.create(ctx, "task", "T", TASK, parent="ST-001")
    return ctx


def test_build_packet_asks_to_mutate_the_changed_lines(task, ctx_env, python_cmd):
    r = run_skill("cp-build", ["--start", "TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "--mutate --lines" in r.stdout and "app/calc.py:<start>-<end>" in r.stdout
    assert "## Mutation" in r.stdout


def test_finish_warns_without_mutation_and_review_shows_it(task, ctx_env, python_cmd):
    run_skill("cp-build", ["--start", "TK-001"], ctx_env, python_cmd)
    r = run_skill("cp-build", ["--finish", "TK-001", "--delivery", "-"], ctx_env, python_cmd,
                  stdin=DELIVERY)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "no `## Mutation` section" in r.stdout
    r = run_skill("cp-review", ["TK-001"], ctx_env, python_cmd)
    assert "Mutation of the changed lines" in r.stdout and "Not run" in r.stdout
    assert "Adversarial review" in r.stdout

    card = cards.get(task, "TK-001")
    cards.set_section(card, "Delivery", testcheck.embed_delivery(DELIVERY + MUTATION))
    r = run_skill("cp-review", ["TK-001"], ctx_env, python_cmd)
    assert "9 mutants, 9 killed (100%)" in r.stdout and "Not run" not in r.stdout


def test_finish_with_mutation_section_has_no_warning(task, ctx_env, python_cmd):
    run_skill("cp-build", ["--start", "TK-001"], ctx_env, python_cmd)
    r = run_skill("cp-build", ["--finish", "TK-001", "--delivery", "-"], ctx_env, python_cmd,
                  stdin=DELIVERY + MUTATION)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "Mutation" not in r.stdout


def test_debug_protocol_requires_the_fix_to_kill_its_mutants(ctx_env, python_cmd):
    r = run_skill("cp-debug", ["--open", "--title", "Wrong discount", "--doc", "-"], ctx_env,
                  python_cmd, stdin="## Symptom\n\nWrong.\n\n## Reproduction\n\n1. Call it.\n")
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "--mutate --lines" in r.stdout and "must be killed" in r.stdout


def test_orchestrator_routes_test_value_demands_to_the_audit():
    spec = load_skill("cp-orchestrator").governance_spec("Construction", "/tmp/ctx")
    text = " ".join(spec["instructions"])
    assert "--audit" in text and "mutation score" in text


# ─── gaps found by running the audit on these modules (dogfooding) ───────

def test_tests_for_uses_the_longest_prefix_and_priority_defaults(tmp_path):
    prof = _load({"test_command": ["x"], "test_map": {"src": ["t/all"], "src/orders": ["t/orders"]},
                  "priority": {"src/orders/pay.py": ["t/orders/test_pay_rules.py"]}})
    assert mutation.tests_for(prof, "src/orders/x.py") == ["t/orders"]
    assert mutation.tests_for(prof, "src/users/x.py") == ["t/all"]
    assert mutation.tests_for(prof, "lib/x.py") == []          # whole suite
    assert mutation.priority_tests(prof, tmp_path, "src/orders/pay.py", []) == \
        ["t/orders/test_pay_rules.py"]
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "test_calc.py").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "test_calc.py").write_text("", encoding="utf-8")
    assert mutation.priority_tests(prof, tmp_path, "app/calc.py", [".venv"]) == ["t/test_calc.py"]


def test_parse_budget_units():
    assert mutation.parse_budget("2h") == 7200
    assert mutation.parse_budget("30m") == 1800
    assert mutation.parse_budget("90s") == 90 and mutation.parse_budget("45") == 45
    assert mutation.parse_budget("") is None
    with pytest.raises(ValueError):
        mutation.parse_budget("two hours")


def test_each_worker_gets_its_own_env_and_a_relative_python(project):
    root, out = project
    # The suite refuses to run without a per-worker DB name: isolation is applied.
    (root / "tests" / "check.py").write_text(
        "import os, sys\nassert os.environ['DB_NAME'] in ('db_0', 'db_1'), os.environ.get('DB_NAME')\n"
        + CHECK, encoding="utf-8")
    venv_py = root / "py"
    venv_py.symlink_to(sys.executable)
    prof = profile(env={"DB_NAME": "db_{worker}"}, python="py",
                   test_command=["{python}", "-S", "tests/check.py"])
    assert run_mutation(root, out, prof=prof)["ran"] > 0
    assert mutation.command(prof, str(venv_py), [])[0] == str(venv_py)


def test_static_audit_patch_object_self_mock_and_suffix_test_files(tmp_path):
    (tmp_path / "service.py").write_text(SERVICE, encoding="utf-8")
    (tmp_path / "service_test.py").write_text(
        "from unittest import mock\nimport service\n\n"
        "def test_obj():\n    with mock.patch.object(service, 'compute', return_value=3):\n"
        "        assert service.report() == '3'\n\n"
        "def test_obj_dependency():\n    with mock.patch.object(service, 'requests'):\n"
        "        assert service.report() == '3'\n", encoding="utf-8")
    (tmp_path / "helpers.py").write_text("def test_like():\n    pass\n", encoding="utf-8")
    result = testaudit.audit(tmp_path)
    assert result["files"] == 1 and result["tests"] == 2
    assert [(k, t) for k, _, _, t, _ in result["findings"]] == [("SELF_MOCK", "test_obj")]
