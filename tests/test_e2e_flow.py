"""End-to-end: every execution skill driven through its CLI under `python -S` (INIT-03).

One temp project with an authorized `.context/`: epic -> story -> task -> plan ->
build -> review -> 7-done (roll-up), plus the bug path (open -> diagnose -> finish).
"""
import subprocess
from pathlib import Path

from conftest import EXIT_OK, skill_script

EPIC = "## Goal\n\nAdd numbers.\n\n## Scope\n\nCalculator only.\n"
STORY = ("## User story\n\nAs a user I want to add so that I get sums.\n\n"
         "## Acceptance criteria\n\n- Adds two numbers\n- Adds negatives\n\n"
         "## Definition of Done\n\n- Tests pass\n")
TASK = ("## Description\n\nImplement add.\n\n## Target files\n\n- app/calc.py\n\n"
        "## Covers\n\n- ST-001/AC-1\n- ST-001/AC-2\n")
BUG_DOC = "## Symptom\n\nadd(0, 0) returns None.\n\n## Reproduction\n\n1. call add(0, 0)\n"
DIAG = "## Root cause\n\nThe zero case returns early without a value.\n"
CODE = "def add(a, b):\n    return a + b\n"
TESTS = ("from app.calc import add\n\n\n"
         "def test_add_two_numbers_st_001_ac_1():\n    assert add(1, 2) == 3\n\n\n"
         "def test_add_negatives_st_001_ac_2():\n    assert add(-1, -2) == -3\n")
BUG_TESTS = ("from app.calc import add\n\n\n"
             "def test_add_zero_bug_001():\n    assert add(0, 0) == 0\n")
T1, T2 = "tests/test_calc.py::test_add_two_numbers_st_001_ac_1", \
    "tests/test_calc.py::test_add_negatives_st_001_ac_2"
BT = "tests/test_bug.py::test_add_zero_bug_001"
DELIVERY = ("## What was done\n\nImplemented add.\n\n## Files changed\n\n- app/calc.py\n\n"
            f"## Tests\n\n- {T1} — covers ST-001/AC-1\n- {T2} — covers ST-001/AC-2\n\n"
            f"## Red evidence\n\n### {T1}\n\n```\nE   ImportError: cannot import name 'add'\n```\n\n"
            f"### {T2}\n\n```\nE   ImportError: cannot import name 'add'\n```\n")
BUG_DELIVERY = ("## What was done\n\nReturn the sum in the zero case.\n\n## Files changed\n\n- app/calc.py\n\n"
                f"## Tests\n\n- {BT} — covers BUG-001\n\n"
                f"## Red evidence\n\n### {BT}\n\n```\nE   assert None == 0\n```\n")
REVIEW = "## Verdict\n\napproved\n\n## Findings\n\n- none\n"


def test_full_flow_through_the_clis(ctx_env, python_cmd, tmp_path):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    root = ctx.parent
    (root / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "app" / "calc.py").write_text(CODE, encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(TESTS, encoding="utf-8")
    (root / "tests" / "test_bug.py").write_text(BUG_TESTS, encoding="utf-8")
    env = dict(ctx_env)

    def sh(skill, *args, stdin=None):
        r = subprocess.run([python_cmd, "-S", str(skill_script(skill)), *args],
                           capture_output=True, text=True, input=stdin, env=env,
                           cwd=str(tmp_path), encoding="utf-8", errors="replace", timeout=120)
        assert r.returncode == EXIT_OK, f"{skill} {args}\n{r.stdout}\n{r.stderr}"
        return r.stdout

    def new(kind, title, doc, *extra):
        return sh("rup-backlog", "--new", kind, "--title", title, "--doc", "-", *extra,
                  stdin=doc).strip()

    assert new("epic", "Calculator", EPIC) == "EP-001"
    assert new("story", "Add numbers", STORY, "--parent", "EP-001") == "ST-001"
    assert new("task", "Implement add", TASK, "--parent", "ST-001") == "TK-001"
    assert sh("rup-backlog", "--release-new", "--title", "MVP").strip() == "R1"
    assert sh("rup-backlog", "--iteration-new", "--release", "R1", "--phase", "Construction",
              "--goal", "Core").strip() == "R1-I1"
    sh("rup-backlog", "--plan", "EP-001", "--iteration", "R1-I1")

    start = sh("rup-build", "--start", "TK-001")
    assert "tk-001-implement-add" in start
    assert "3-doing" in sh("rup-backlog", "--show", "TK-001")
    out = sh("rup-build", "--finish", "TK-001", "--delivery", "-", stdin=DELIVERY)
    assert "TK-001 -> 4-review" in out
    assert "tk-001-implement-add" in sh("rup-review", "TK-001")
    assert "5-testing" in sh("rup-review", "--record", "TK-001", "--doc", "-", stdin=REVIEW)
    sh("rup-backlog", "--move", "TK-001", "6-staging", "--reason", "deployed to staging")
    sh("rup-backlog", "--move", "TK-001", "7-done", "--reason", "released")

    done = sh("rup-backlog", "--list", "--column", "7-done")
    for card_id in ("TK-001", "ST-001", "EP-001"):
        assert f"| {card_id} |" in done, done
    assert "1/1" in (ctx / "docs" / "06-roadmap.md").read_text(encoding="utf-8")

    # bug path: open -> diagnose (branch set) -> finish with a regression test naming the bug
    assert "BUG-001 created" in sh("rup-debug", "--open", "--title", "Zero sum", "--doc", "-",
                                   stdin=BUG_DOC)
    sh("rup-debug", "--diagnose", "BUG-001", "--doc", "-", stdin=DIAG)
    shown = sh("rup-backlog", "--show", "BUG-001")
    assert "branch: bug-001-zero-sum" in shown and "3-doing" in shown
    assert "BUG-001 -> 4-review" in sh("rup-build", "--finish", "BUG-001", "--delivery", "-",
                                       stdin=BUG_DELIVERY)
    assert "| BUG-001 |" in sh("rup-backlog", "--list", "--column", "4-review")
    assert "bug-001-zero-sum" in sh("rup-review", "BUG-001")
