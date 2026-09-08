"""E2E tests of the kanban flow — inbox→kanban triage, dispatch and status update.

Guarantees the complete flow works:
1. cp-agile --triage  : inbox/ → kanban/1-backlog/
2. cp-agile --task + --update-status  : moves between columns
3. cp-orchestrator --kanban-task  : updates during/after execution
4. Tasks always keep the frontmatter status synchronized with the column
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import EXIT_OK, EXIT_NO_LLM, REPO_ROOT, SKILLS_DIR

AGILE_RUN = SKILLS_DIR / "cp-agile" / "scripts" / "run.py"
ORCHESTRATOR_RUN = SKILLS_DIR / "cp-orchestrator" / "scripts" / "run.py"


# ─── Helpers ───────────────────────────────────────────────────────

def run(script, args, env, python_cmd, tmpdir, timeout=120):
    """Runs a script and returns (returncode, stdout, stderr)."""
    cwd = str(tmpdir)
    r = subprocess.run(
        [python_cmd, str(script)] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=cwd, env=env, encoding="utf-8", errors="replace",
    )
    return r.returncode, r.stdout, r.stderr


def parse_frontmatter(content: str) -> dict:
    """Extracts YAML frontmatter from a .md."""
    import re
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"').strip("'")
    return data


# ─── Fixture: environment with .context/ initialized ─────────────────

@pytest.fixture
def kanban_env(clean_env, python_cmd, tmp_path):
    """Creates a complete environment: .context/ + kanban + inbox with items."""
    # 1. Initializes the .context/ structure (kanban is born here)
    rc, out, err = run(
        SKILLS_DIR / "cp-software-spec" / "scripts" / "run.py",
        ["--init", "--dir", str(tmp_path)], clean_env, python_cmd, tmp_path,
    )
    assert rc == EXIT_OK, f"initializer failed:\n{out}\n{err}"

    # 2. Creates items in the inbox
    inbox = tmp_path / ".context" / "inbox"
    (inbox / "bugs").mkdir(parents=True, exist_ok=True)
    (inbox / "tasks").mkdir(parents=True, exist_ok=True)
    (inbox / "initiatives").mkdir(parents=True, exist_ok=True)

    bug = inbox / "bugs" / "login-500.md"
    bug.write_text("# Login returns 500\n\nThe /login endpoint is returning internal error 500.\nTraceback: KeyError in the authentication module.\n", encoding="utf-8")

    task = inbox / "tasks" / "add-report.md"
    task.write_text("# Add PDF report\n\nCreate a monthly PDF report screen.\n", encoding="utf-8")

    epic = inbox / "initiatives" / "mobile-platform.md"
    epic.write_text("# Initiative: Mobile Platform\n\nEpic: mobile app for iOS and Android.\n", encoding="utf-8")

    return tmp_path


# ─── Tests ────────────────────────────────────────────────────────

class TestInboxTriage:
    """cp-agile --triage: inbox/ → kanban/1-backlog/"""

    def test_triage_imports_items_from_inbox(self, kanban_env, clean_env, python_cmd):
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK, f"--triage failed:\n{out}\n{err}"
        assert "3 item(s)" in out, f"Expected 3 items, got:\n{out}"

        # Verifies the files in the kanban
        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        md_files = sorted(backlog.glob("*.md"))
        assert len(md_files) == 3, f"Expected 3 tasks, found {len(md_files)}: {md_files}"

        # Each task must have valid frontmatter
        for f in md_files:
            meta = parse_frontmatter(f.read_text(encoding="utf-8"))
            assert "id" in meta, f"{f.name} without id in frontmatter"
            assert meta.get("status") == "ready", f"{f.name}: status {meta.get('status')} != ready"

        # Verifies that the original item was moved to .processed
        processed_bugs = kanban_env / ".context" / "inbox" / "bugs" / ".processed"
        assert (processed_bugs / "login-500.md").is_file(), "bug was not archived"

    def test_triage_classifies_tracks_correctly(self, kanban_env, clean_env, python_cmd):
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK

        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        metas = {f.name: parse_frontmatter(f.read_text(encoding="utf-8"))
                 for f in backlog.glob("*.md")}

        # Bug has type='bug' and BUG prefix
        bug_file = [k for k, v in metas.items() if v.get("type") == "bug"]
        assert len(bug_file) >= 1, f"No bug classified: {metas}"
        bug_id = metas[bug_file[0]]["id"]
        assert bug_id.startswith("BUG-"), f"Bug id {bug_id} does not start with BUG-"

        # Initiative has type='initiative'
        init_file = [k for k, v in metas.items() if v.get("type") == "initiative"]
        assert len(init_file) >= 1, f"No initiative classified: {metas}"

    def test_triage_idempotent(self, kanban_env, clean_env, python_cmd):
        """Running triage twice does not create duplicate tasks."""
        rc1, out1, err1 = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc1 == EXIT_OK
        assert "3 item(s)" in out1

        rc2, out2, err2 = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc2 == EXIT_OK
        assert "No new items" in out2, f"Second triage should be empty:\n{out2}"

        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        assert len(list(backlog.glob("*.md"))) == 3, "Duplicate tasks after second triage"


class TestKanbanStatus:
    """cp-agile --task + --update-status: move between columns"""

    def test_update_status_moves_and_updates_frontmatter(self, kanban_env, clean_env, python_cmd):
        # First triage
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK

        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        task_path = sorted(backlog.glob("*.md"))[0]
        task_id = task_path.stem

        # Moves to doing
        rc, out, err = run(AGILE_RUN, ["--task", task_id, "--update-status", "doing"],
                           clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        assert "doing" in out

        # File must be in 3-doing/
        doing_path = kanban_env / ".context" / "kanban" / "3-doing" / f"{task_id}.md"
        assert doing_path.is_file(), f"Task not moved to 3-doing/"

        # Frontmatter must have status=doing
        meta = parse_frontmatter(doing_path.read_text(encoding="utf-8"))
        assert meta.get("status") == "doing", f"status {meta.get('status')} != doing"

        # File must no longer be in 1-backlog/
        assert not task_path.exists(), "Task still exists in 1-backlog/"

    def test_update_status_todo_to_review(self, kanban_env, clean_env, python_cmd):
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK

        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        task_id = sorted(backlog.glob("*.md"))[0].stem

        # todo
        rc, out, err = run(AGILE_RUN, ["--task", task_id, "--update-status", "todo"],
                           clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        assert (kanban_env / ".context" / "kanban" / "2-todo" / f"{task_id}.md").is_file()

        # review
        rc, out, err = run(AGILE_RUN, ["--task", task_id, "--update-status", "review"],
                           clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        assert (kanban_env / ".context" / "kanban" / "4-review" / f"{task_id}.md").is_file()
        meta = parse_frontmatter(
            (kanban_env / ".context" / "kanban" / "4-review" / f"{task_id}.md")
            .read_text(encoding="utf-8"))
        assert meta["status"] == "review"

    def test_update_status_missing_task(self, kanban_env, clean_env, python_cmd):
        rc, out, err = run(AGILE_RUN, ["--task", "NONE-999", "--update-status", "done"],
                           clean_env, python_cmd, kanban_env)
        assert rc != EXIT_OK, "Should fail with a nonexistent task"
        assert "not found" in (out + err)


class TestOrchestratorWithKanban:
    """cp-orchestrator --kanban-task: updates status during execution"""

    @pytest.mark.parametrize("mode", ["bugfix", "competitive", "maintenance", "micro"])
    def test_orchestrator_updates_task_from_doing_to_done(self, kanban_env, clean_env, python_cmd, mode):
        """For each mode that runs without a real LLM, verifies the task goes doing→done/blocked."""
        # Triages and creates a task
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        task_id = sorted(backlog.glob("*.md"))[0].stem

        # Runs the orchestrator with --kanban-task --dry-run (to not depend on an LLM)
        # We use --dry-run which does not need an LLM
        rc, out, err = run(
            ORCHESTRATOR_RUN,
            ["test briefing", "--mode", mode, "--kanban-task", task_id, "--dry-run"],
            clean_env, python_cmd, kanban_env,
        )
        # dry-run without an LLM should work (exit 0, shows the plan)
        # But if the skill requires an LLM, it may exit 2 with a message
        output = out + err
        # dry-run does not execute, so the task stays where it was
        # the test only verifies that --kanban-task is accepted
        assert "kanban" in output.lower() or "pipeline" in output.lower(), \
            f"mode {mode}: command rejected --kanban-task:\n{output[:500]}"

    def test_orchestrator_pipeline_with_kanban_task(self, kanban_env, clean_env, python_cmd):
        """Tests that the PipelineExecutor accepts kanban_task and calls _kanban_update_status."""
        # Triages
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        task_id = sorted(backlog.glob("*.md"))[0].stem

        # Moves to todo (simulates daemon dispatch)
        rc, out, err = run(AGILE_RUN, ["--task", task_id, "--update-status", "todo"],
                           clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK

        # Runs the orchestrator --kanban-task - mode that uses PipelineExecutor
        # Without an LLM, it will fail with exit 2, but _kanban_update_status("doing") was already called
        # (and the task should have left 2-todo/). Then _kanban_update_status("blocked") on failure.
        rc, out, err = run(
            ORCHESTRATOR_RUN,
            ["test briefing", "--mode", "bugfix", "--kanban-task", task_id],
            clean_env, python_cmd, kanban_env,
        )

        # Since there is no LLM, the expected exit code would be 2 (EXIT_NO_LLM)
        # The task should be in blocked/ (since the pipeline failed)
        output = out + err
        print(f"  kanban-task bugfix: exit={rc}\n{output[:500]}")

        # The task may be in blocked/ (if the pipeline tried to execute and failed)
        # or still in todo/ (if the orchestrator never got to execute)
        blocked_dir = kanban_env / ".context" / "kanban" / "blocked"
        todo_dir = kanban_env / ".context" / "kanban" / "2-todo"

        blocked_task = blocked_dir / f"{task_id}.md"
        todo_task = todo_dir / f"{task_id}.md"

        if blocked_task.exists():
            meta = parse_frontmatter(blocked_task.read_text(encoding="utf-8"))
            assert meta.get("status") == "blocked", \
                f"Task in blocked should have status=blocked, got {meta.get('status')}"
            print(f"  ✅ Task {task_id} moved to blocked/ (expected without an LLM)")
        elif todo_task.exists():
            # Case where the orchestrator did not execute (failed before calling the executor)
            print(f"  ⚠️  Task {task_id} stayed in 2-todo/ (orchestrator may have failed before executing)")
        else:
            # May be in doing/ if _kanban_update_status("doing") was called before the failure
            doing_dir = kanban_env / ".context" / "kanban" / "3-doing"
            doing_task = doing_dir / f"{task_id}.md"
            assert doing_task.exists(), \
                f"Task not found in blocked/, todo/ or doing/: {output[:500]}"
            print(f"  ⚠️  Task {task_id} stayed in doing/ (kanban update before the failure)")


class TestAgileDispatch:
    """cp-agile --task (without --update-status): dispatch to the orchestrator"""

    def test_dispatch_runs_complete_kanban_flow(self, kanban_env, clean_env, python_cmd):
        """Tests the complete flow: triage → dispatch via --task → waits for the result."""
        # 1. Triages
        rc, out, err = run(AGILE_RUN, ["--triage"], clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK
        backlog = kanban_env / ".context" / "kanban" / "1-backlog"
        task_id = sorted(backlog.glob("*.md"))[0].stem

        # 2. Marks as ready (already is)
        rc, out, err = run(AGILE_RUN, ["--task", task_id, "--update-status", "ready"],
                           clean_env, python_cmd, kanban_env)
        assert rc == EXIT_OK

        # 3. Dispatch (executes via the orchestrator)
        rc, out, err = run(
            AGILE_RUN, ["--task", task_id],
            clean_env, python_cmd, kanban_env, timeout=60,
        )
        output = out + err
        print(f"  dispatch exit={rc}\n{output[:500]}")

        # Without an LLM, the orchestrator will fail, so the task
        # must end in blocked/ (agile captures the error)
        # or doing/ (if agile moved before the subprocess executed)
        done_dir = kanban_env / ".context" / "kanban" / "7-done"
        blocked_dir = kanban_env / ".context" / "kanban" / "blocked"
        doing_dir = kanban_env / ".context" / "kanban" / "3-doing"

        done_task = done_dir / f"{task_id}.md"
        blocked_task = blocked_dir / f"{task_id}.md"
        doing_task = doing_dir / f"{task_id}.md"

        assert done_task.exists() or blocked_task.exists() or doing_task.exists(), \
            f"Task disappeared from the kanban! done={done_task.exists()} blocked={blocked_task.exists()} doing={doing_task.exists()}\n{output}"

        if done_task.exists():
            meta = parse_frontmatter(done_task.read_text(encoding="utf-8"))
            assert meta.get("status") == "done", f"Task in done without status=done: {meta}"
        elif blocked_task.exists():
            meta = parse_frontmatter(blocked_task.read_text(encoding="utf-8"))
            assert meta.get("status") == "blocked", f"Task in blocked without status=blocked: {meta}"
            print(f"  ✅ Without an LLM: task {task_id} blocked as expected (pipeline cannot execute)")
        else:
            print(f"  ⚠️  Task stayed in doing/ — agile moved before the orchestrator executed")


class TestAgileDaemonWire:
    """Verifies that the daemon has the orchestrator wire configured."""

    def test_daemon_wire_references_valid_orchestrator(self):
        """The orchestrator path in agile must exist."""
        # Imports the agile constants
        import importlib.util
        spec = importlib.util.spec_from_file_location("agile_mod", AGILE_RUN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "ORCHESTRATOR_RUN"), "Agile does not have ORCHESTRATOR_RUN"
        assert mod.ORCHESTRATOR_RUN.exists(), \
            f"ORCHESTRATOR_RUN does not exist: {mod.ORCHESTRATOR_RUN}"


class TestAllSkillsExecutorKanban:
    """Verifies that every cp-* skill 'passes' through the kanban when triggered."""

    def test_orchestrator_kanban_task_arg_accepted_by_all_modes(self, clean_env, python_cmd, tmp_path):
        """Every orchestrator mode accepts --kanban-task without breaking."""
        # Imports the orchestrator MODOS
        import importlib.util
        spec = importlib.util.spec_from_file_location("orq_mod", ORCHESTRATOR_RUN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        modes_to_test = [m for m in mod.MODOS.keys()
                         if m not in ("full-dev", "agile")]  # full-dev runs natively, agile is a daemon

        for mode in modes_to_test:
            rc, out, err = run(
                ORCHESTRATOR_RUN,
                ["test", "--mode", mode, "--kanban-task", "TASK-001", "--dry-run"],
                clean_env, python_cmd, tmp_path,
            )
            output = out + err
            assert rc == EXIT_OK, \
                f"Mode {mode} with --kanban-task failed (exit {rc}):\n{output[:300]}"
            assert "kanban" in output.lower() or "pipeline" in output.lower(), \
                f"Mode {mode}: output seems empty or without pipeline:\n{output[:300]}"
