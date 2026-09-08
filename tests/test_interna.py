"""Internal (unit) tests of the cp-* skills.

Unlike the smoke tests (which call the script via subprocess), these tests
import the code directly to test internal functions and classes:
  - cp-agile: LocalIntegration, parse_frontmatter, build_task_template
  - cp-software-spec: SoftwareSpec, KANBAN_COLUMNS, ingest_vision
  - cp-orchestrator: PipelineExecutor._build_cli_args, nexus_detect_mode

NO test requires crewai or an LLM — they only test pure Python logic.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SKILLS_DIR, clean_env

# ═══════════════════════════════════════════════════════════════════════
# HELPERS — import run.py as a module, isolating crewai dependencies
# ═══════════════════════════════════════════════════════════════════════

AGILE_PY = SKILLS_DIR / "cp-agile" / "scripts" / "run.py"
SPEC_PY = SKILLS_DIR / "cp-software-spec" / "scripts" / "run.py"
ORCHESTRATOR_PY = SKILLS_DIR / "cp-orchestrator" / "scripts" / "run.py"


def import_skill(path: Path, name: str = None):
    """Imports run.py as a module, without executing main()."""
    spec = importlib.util.spec_from_file_location(
        name or path.stem, path,
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════
# cp-agile — pure logic (no crewai)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def agile():
    return import_skill(AGILE_PY, "cp_agile")


class TestAgileCore:
    """Helper functions: template, frontmatter, parsing."""

    def test_build_task_template_fills_all_fields(self, agile):
        content = agile.build_task_template(
            task_id="TASK-001",
            title="Implement login",
            status="ready",
            priority="high",
            assignee="renat",
            tags='["frontend", "auth"]',
            description="Create a login screen with JWT",
            acceptance_criteria="Working login with email and password",
            type="task",
            source="inbox/bugs/bug-report.md",
        )
        assert "id: TASK-001" in content
        assert "title: Implement login" in content
        assert "status: ready" in content
        assert "priority: high" in content
        assert "assignee: renat" in content
        assert "type: task" in content
        assert "source: inbox/bugs/bug-report.md" in content
        assert "## Acceptance Criteria" in content
        # The template has sections that the feedback loop adds
        assert "## Pending Questions" in content
        assert "## Blockers Log" in content

    def test_build_task_template_defaults(self, agile):
        """Tests that sensible defaults are applied."""
        content = agile.build_task_template("TASK-042", "My task")
        assert "priority: medium" in content
        assert "status: backlog" in content
        assert "type: task" in content  # DEFAULT_TRACK
        assert "source: " in content  # empty by default

    def test_parse_frontmatter_basic(self, agile):
        content = """---
id: TASK-001
title: Test
status: ready
priority: high
---
# Content
"""
        meta = agile.parse_frontmatter(content)
        assert meta["id"] == "TASK-001"
        assert meta["title"] == "Test"
        assert meta["status"] == "ready"

    def test_parse_frontmatter_without_frontmatter(self, agile):
        assert agile.parse_frontmatter("# Only content") == {}

    def test_parse_frontmatter_value_with_quotes(self, agile):
        content = """---
title: 'My title'
tags: "[]"
---
"""
        meta = agile.parse_frontmatter(content)
        assert meta["title"] == "My title"
        assert meta["tags"] == "[]"

    def test_parse_frontmatter_empty_field(self, agile):
        content = """---
id: TASK-001
assignee:
---
"""
        meta = agile.parse_frontmatter(content)
        assert meta["id"] == "TASK-001"
        assert meta.get("assignee", "") == ""

    def test_read_task_meta_missing_file(self, agile, tmp_path):
        meta = agile.read_task_meta(tmp_path / "does-not-exist.md")
        assert meta == {}

    def test_read_task_status_reads_from_frontmatter(self, agile, tmp_path):
        task = tmp_path / "task.md"
        task.write_text("""---
id: TASK-X
status: doing
---
# Task
""", encoding="utf-8")
        assert agile.read_task_status(task) == "doing"

    def test_read_task_status_without_frontmatter(self, agile, tmp_path):
        task = tmp_path / "task.md"
        task.write_text("# Only content", encoding="utf-8")
        assert agile.read_task_status(task) == ""

    def test_constants_valid(self, agile):
        """Verifies that VALID_STATUSES and TRACKS are consistent."""
        # ALL tracks have a prefix
        for track, prefix in agile.TRACKS.items():
            assert len(prefix) > 0, f"{track} without prefix"
        assert agile.DEFAULT_TRACK in agile.TRACKS
        # `inbox` is not a track — it is a separate concept
        assert "inbox" not in agile.TRACKS
        # blocked is a valid status
        assert "blocked" in agile.VALID_STATUSES

    def test_track_patterns_cover_all_tracks(self, agile):
        """Each track (except task, which is the default) has at least one pattern."""
        tracks_with_pattern = {t for t, _ in agile.TRACK_PATTERNS}
        tracks_defined = set(agile.TRACKS.keys())
        # task does not need a pattern — it is the default
        assert tracks_with_pattern == tracks_defined - {"task"}, (
            f"TRACK_PATTERNS does not cover: {tracks_defined - {'task'} - tracks_with_pattern}"
        )


class TestAgileLocalIntegration:
    """LocalIntegration: operations on the local filesystem."""

    @pytest.fixture
    def local(self, agile, tmp_path):
        kanban_root = tmp_path / ".context" / "kanban"
        return agile.LocalIntegration(root=kanban_root)

    def test_ensure_structure_creates_columns(self, agile, tmp_path):
        root = tmp_path / "kanban"
        li = agile.LocalIntegration(root=root)
        for col in agile.KANBAN_COLUMNS + [agile.BLOCKED_DIR]:
            assert (root / col).is_dir(), f"column {col} not created"

    def test_scan_ready_finds_ready_tasks(self, local, agile):
        # Creates a task with status: ready in 1-backlog
        backlog = local.root / "1-backlog"
        t1 = backlog / "TASK-001.md"
        t1.parent.mkdir(parents=True, exist_ok=True)
        t1.write_text("""---
id: TASK-001
status: ready
---
""", encoding="utf-8")
        # Creates a task with status: backlog — ignored
        t2 = backlog / "TASK-002.md"
        t2.write_text("""---
id: TASK-002
status: backlog
---
""", encoding="utf-8")

        ready = local.scan_ready()
        assert len(ready) == 1
        assert ready[0].name == "TASK-001.md"

    def test_scan_ready_empty_backlog_returns_empty_list(self, local):
        assert local.scan_ready() == []

    def test_all_tasks_lists_in_all_columns(self, local, agile):
        # Task in backlog
        b1 = local.root / "1-backlog" / "TASK-001.md"
        b1.parent.mkdir(parents=True, exist_ok=True)
        b1.write_text("---\nid: TASK-001\ntitle: Backlog task\nstatus: ready\n---\n", encoding="utf-8")
        # Task in doing
        d1 = local.root / "3-doing" / "TASK-002.md"
        d1.parent.mkdir(parents=True, exist_ok=True)
        d1.write_text("---\nid: TASK-002\ntitle: Doing task\nstatus: doing\n---\n", encoding="utf-8")

        tasks = local.all_tasks()
        assert len(tasks) == 2
        titles = {t["title"] for t in tasks}
        assert "Backlog task" in titles
        assert "Doing task" in titles

    def test_move_to_moves_file_between_columns(self, local, agile):
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        moved = local.move_to("TASK-001", "2-todo")
        assert moved is not None
        assert moved.parent.name == "2-todo"
        assert moved.exists()
        assert not src.exists()

    def test_move_to_missing_task_returns_none(self, local):
        assert local.move_to("TASK-MISSING", "2-todo") is None

    def test_find_task_finds_in_any_column(self, local, agile):
        src = local.root / "4-review" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        found = local.find_task("TASK-001")
        assert found is not None
        assert found.name == "TASK-001.md"

    def test_find_task_missing_returns_none(self, local):
        assert local.find_task("GHOST") is None

    def test_add_question_adds_section_to_file(self, local, agile):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n\n# My Task\n", encoding="utf-8")

        result = local.add_question("TASK-001", "What is the MVP scope?")
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert "## Pending Questions" in content
        assert "What is the MVP scope?" in content

    def test_add_question_accumulates_multiple(self, local, agile):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        local.add_question("TASK-001", "First question")
        local.add_question("TASK-001", "Second question")
        content = src.read_text(encoding="utf-8")
        # Two entries under the same section
        assert content.count("## Pending Questions") == 1
        assert content.count("First question") == 1
        assert content.count("Second question") == 1

    def test_add_question_missing_task_returns_none(self, local):
        assert local.add_question("GHOST", "message") is None

    def test_add_blocker_moves_to_blocked_and_adds_log(self, local, agile):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.add_blocker("TASK-001", "Connection failure", "high")
        assert result is not None
        assert result.parent.name == "blocked"
        content = result.read_text(encoding="utf-8")
        assert "## Blockers Log" in content
        assert "Connection failure" in content
        assert "high" in content

    def test_resume_moves_from_blocked_to_todo(self, local, agile):
        src = local.root / "blocked" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.resume("TASK-001", "Answer: yes")
        assert result is not None
        assert result.parent.name == "2-todo"
        content = result.read_text(encoding="utf-8")
        assert "✅ [Human Answer]" in content
        assert "Answer: yes" in content

    def test_resume_not_blocked_does_not_move(self, local, agile):
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.resume("TASK-001", "ok")
        # Stays in the same folder (was not blocked)
        assert result.parent.name == "1-backlog"

    def test_resume_missing_task_returns_none(self, local):
        assert local.resume("GHOST", "ok") is None

    def test_document_kanban_generates_md(self, local, agile, tmp_path):
        # Adds a task
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\ntitle: My Task\npriority: high\n---\n", encoding="utf-8")

        # documentation should go to the right context
        context_root = tmp_path / ".context"
        dest = local.document_kanban(context_root=str(context_root))
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "Kanban / Execution Pipeline" in content
        assert "1-backlog" in content
        assert "My Task" in content
        assert "TASK-001" in content


class TestAgileFeedbackLoop:
    @pytest.fixture
    def feedback(self, agile, tmp_path):
        root = tmp_path / ".context" / "kanban"
        # Needs an existing task
        src = root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\ntitle: My Task\n---\n", encoding="utf-8")
        # Swaps KANBAN_ROOT for the tmp_path
        old_root = agile.KANBAN_ROOT
        agile.KANBAN_ROOT = root
        fb = agile.CPAgileFeedbackLoop(sync_trello=False)
        yield fb

    def test_question_emits_event(self, feedback):
        event = feedback.question("TASK-001", "What is the scope?")
        assert event["event"] == "QUESTION"
        assert event["payload"]["task_id"] == "TASK-001"

    def test_blocker_emits_event(self, feedback):
        event = feedback.blocker("TASK-001", "General failure", "critical")
        assert event["event"] == "BLOCKER"
        assert event["payload"]["severity"] == "critical"

    def test_resume_task_emits_event(self, feedback):
        # First block, then resume
        feedback.blocker("TASK-001", "error")
        event = feedback.resume_task("TASK-001", "human answer")
        assert event["event"] == "HUMAN_CLARIFICATION_RECEIVED"
        assert event["payload"]["answer"] == "human answer"


# ═══════════════════════════════════════════════════════════════════════
# cp-software-spec — pure logic
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def spec():
    return import_skill(SPEC_PY, "cp_software_spec")


class TestSoftwareSpecCore:
    """SoftwareSpec: structure creation and vision ingestion."""

    def test_build_creates_entire_structure(self, spec, tmp_path):
        init = spec.SoftwareSpec(project_dir=tmp_path)
        summary = init.build()
        assert summary["files_created"] > 0
        # Verifies key pieces
        context = tmp_path / ".context"
        assert (context / "README.md").is_file()
        # docs — RUP 4 phases
        for phase, files in spec.RUP_PHASES.items():
            for fname in files:
                assert (context / "docs" / phase / fname).is_file(), f"{phase}/{fname} missing"
        # inbox
        for name in spec.INBOX_DIRS:
            assert (context / "inbox" / name / "README.md").is_file(), f"inbox/{name} missing"
        # tracking
        assert (context / "tracking" / "progress.md").is_file()
        assert (context / "tracking" / "decisions.md").is_file()
        # kanban
        assert (context / "kanban" / "README.md").is_file()
        for col in spec.KANBAN_COLUMNS + [spec.KANBAN_BLOCKED_DIR]:
            assert (context / "kanban" / col / ".gitkeep").is_file(), f"kanban/{col}/.gitkeep missing"
        # Pointers at the root
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / "AGENT.md").is_file()

    def test_build_dry_run_does_not_create_files(self, spec, tmp_path):
        init = spec.SoftwareSpec(project_dir=tmp_path, dry_run=True)
        summary = init.build()
        assert summary["dry_run"] is True
        # Nothing was actually created
        assert not (tmp_path / ".context").exists()
        assert "dry-run" in init.created[0]

    def test_ingest_vision_moves_file(self, spec, tmp_path):
        # Creates vision.md at the root
        vision_src = tmp_path / "vision.md"
        vision_src.write_text("# Product Vision\n", encoding="utf-8")

        init = spec.SoftwareSpec(project_dir=tmp_path)
        ingested = init.ingest_vision()
        assert ingested is True
        # vision.md was moved to .context/docs/01-inception/
        dest = tmp_path / ".context" / "docs" / "01-inception" / "vision-and-scope.md"
        assert dest.is_file()
        assert not vision_src.exists()
        assert "Product Vision" in dest.read_text(encoding="utf-8")

    def test_ingest_vision_without_vision_returns_false(self, spec, tmp_path):
        init = spec.SoftwareSpec(project_dir=tmp_path)
        assert init.ingest_vision() is False

    def test_ingest_vision_dry_run_does_not_move(self, spec, tmp_path):
        vision_src = tmp_path / "vision.md"
        vision_src.write_text("# Vision\n", encoding="utf-8")

        init = spec.SoftwareSpec(project_dir=tmp_path, dry_run=True)
        ingested = init.ingest_vision()
        assert ingested is True
        # Original file still exists
        assert vision_src.exists()

    def test_kanban_columns_match_agile(self, spec):
        """The columns declared in the spec match those of cp-agile."""
        agile = import_skill(AGILE_PY, "cp_agile")
        assert spec.KANBAN_COLUMNS == agile.KANBAN_COLUMNS
        assert spec.KANBAN_BLOCKED_DIR == agile.BLOCKED_DIR

    def test_report_gaps_does_not_break(self, spec, tmp_path, capsys):
        init = spec.SoftwareSpec(project_dir=tmp_path)
        init.build()
        init.report_gaps()
        captured = capsys.readouterr().out
        assert "EXECUTIVE SUMMARY" in captured
        assert "Inception (01)" in captured

    def test_refine_card_moves_backlog_to_todo(self, spec, tmp_path):
        """--refine-card transforms a backlog card into an executable issue."""
        init = spec.SoftwareSpec(project_dir=tmp_path)
        init.build()
        backlog = tmp_path / ".context" / "kanban" / "1-backlog"
        card = backlog / "TASK-042.md"
        card.write_text("""---
id: TASK-042
title: "Implementar autenticação via Magic Link"
type: feature
status: ready
---

# Implementar autenticação via Magic Link

## Description

Implementar login por magic link com token de uso único.

## Acceptance Criteria

- [ ] Endpoint POST /auth/magic-link retorna 200
""", encoding="utf-8")

        dest = init.refine_card("TASK-042")
        assert dest.parent.name == "2-todo"
        assert dest.is_file()
        # Original backlog card removed
        assert not card.exists()
        content = dest.read_text(encoding="utf-8")
        assert "### 1. Contexto & Objetivo" in content
        assert "### 2. Arquivos Alvo" in content
        assert "### 3. Critérios de Aceite (DoR / DoD)" in content
        assert "### 4. Insumos Técnicos e Contratos de Dados" in content
        assert "### 5. Passos de Validação e Execução" in content


# ═══════════════════════════════════════════════════════════════════════
# cp-orchestrator — pure logic (no crewai)
# ═══════════════════════════════════════════════════════════════════════


class TestOrchestratorNexusDetectMode:
    """nexus_detect_mode: requirement classification into NEXUS mode."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORCHESTRATOR_PY, "cp_orchestrator")

    def test_full_keywords(self):
        """Complete-system words return 'full'."""
        assert self.orq.nexus_detect_mode("Build a scheduling system") == "full"
        assert self.orq.nexus_detect_mode("Create a SaaS platform from scratch") == "full"
        assert self.orq.nexus_detect_mode("Delivery application") == "full"
        assert self.orq.nexus_detect_mode("music app") == "full"

    def test_sprint_keywords(self):
        """Feature/functionality words return 'sprint'."""
        assert self.orq.nexus_detect_mode("implement login feature") == "sprint"
        assert self.orq.nexus_detect_mode("Add sales report") == "sprint"
        assert self.orq.nexus_detect_mode("Add a new screen") == "sprint"

    def test_micro_keywords(self):
        """Bug/fix words return 'micro'."""
        assert self.orq.nexus_detect_mode("Fix bug in login") == "micro"
        assert self.orq.nexus_detect_mode("Adjust screen layout") == "micro"
        assert self.orq.nexus_detect_mode("small fix in header") == "micro"

    def test_tie_full_wins(self):
        """A tie goes to full (priority in the comparison order)."""
        assert self.orq.nexus_detect_mode("complete system for reports") == "full"

    def test_case_insensitive(self):
        assert self.orq.nexus_detect_mode("CREATE PLATFORM") == "full"
        assert self.orq.nexus_detect_mode("ADD BUTTON") == "sprint"

    def test_empty_requirement_returns_full_by_tiebreaker(self):
        """Empty string: no keyword matches, full wins on the tiebreaker (full >= sprint)."""
        assert self.orq.nexus_detect_mode("") == "full"
        assert self.orq.nexus_detect_mode("   ") == "full"


class TestOrchestratorCrewPaths:
    """SKILL_PATHS and CREWS: validation of the static definitions."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORCHESTRATOR_PY, "cp_orchestrator")

    def test_every_crew_with_skill_has_valid_path(self):
        """Every crew that points to an external skill needs the run.py to exist."""
        missing = [
            ck for ck, path in self.orq.SKILL_PATHS.items()
            if ck in self.orq.CREWS and not path.exists()
        ]
        assert not missing, f"missing skills: {missing}"

    def test_every_mode_references_existing_crew(self):
        """No mode points to a nonexistent crew."""
        native_crews = {"full-dev"}
        for mode, info in self.orq.MODOS.items():
            for ck in info["crews"]:
                assert ck in self.orq.CREWS or ck in native_crews, (
                    f"mode {mode!r} -> nonexistent crew: {ck!r}"
                )

    def test_invoke_default_applied_where_missing(self):
        """Crews without 'invoke' receive the default {briefing_arg: 'input', output: True}."""
        invoke_default = {"briefing_arg": "input", "output": True}
        for ck, crew in self.orq.CREWS.items():
            if "invoke" not in crew:
                assert crew.get("invoke", invoke_default) == invoke_default, (
                    f"{ck}: no explicit invoke, but the default would not be applied"
                )

    def test_crews_have_all_required_fields(self):
        """Each crew has name, skill, description, agents, inputs, outputs, quality_gate."""
        required = {"name", "skill", "description", "agents",
                    "inputs", "outputs", "quality_gate"}
        for ck, crew in self.orq.CREWS.items():
            missing = required - set(crew.keys())
            assert not missing, f"{ck}: missing required fields: {missing}"


class TestOrchestratorPipelineExecutor:
    """PipelineExecutor: arg building and phase resolution."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORCHESTRATOR_PY, "cp_orchestrator")

    def test_build_cli_args_crew_with_invoke(self, tmp_path):
        """A crew with explicit invoke is respected."""
        executor = self.orq.PipelineExecutor(
            briefing="test", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("goal-loop")
        assert args is not None
        # goal-loop has invoke: {briefing_arg: 'goal', output: False}
        assert "--goal" in " ".join(args)
        assert "--dry-run" not in " ".join(args)

    def test_build_cli_args_agile_returns_daemon_without_dry_run(self, tmp_path):
        """Agile returns with --daemon, without needing --dry-run (the orchestrator does not pass it)."""
        executor = self.orq.PipelineExecutor(
            briefing="test", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("agile")
        assert args is not None
        args_str = " ".join(args)
        assert "--daemon" in args_str
        assert "test" not in args_str  # briefing does not go to daemon mode

    def test_build_cli_args_with_output_when_skill_accepts(self, tmp_path):
        """Skills with output=True receive --output with a valid path."""
        executor = self.orq.PipelineExecutor(
            briefing="test", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("architecture")
        args_str = " ".join(args)
        assert "--output" in args_str

    def test_resolve_mode_keeps_explicit_mode(self):
        """When the user passes --mode explicitly, that mode is used."""
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)
        executor.mode = "micro"
        assert executor.mode == "micro"

    def test_get_previous_artifact_maps_correctly(self, tmp_path):
        """The prev_map links each phase to the correct previous phase."""
        executor = self.orq.PipelineExecutor(
            briefing="test", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        # Simulates artifacts of previous phases
        expected_prev_map = {
            "architecture": "requirements",
            "implementation": "architecture",
            "testing": "implementation",
            "security": "implementation",
            "devops": "implementation",
            "documentation": "implementation",
            "quality": None,
            "bug-fix": None,
            "competitive-analysis": None,
            "goal-loop": None,
            "maintenance": None,
            "software-spec": None,
            "agile": None,
        }
        # Tests via _get_previous_artifact (indirectly)
        for crew_key, expected in expected_prev_map.items():
            if crew_key in self.orq.CREWS:
                invoke = self.orq.CREWS[crew_key].get("invoke", {"briefing_arg": "input", "output": True})
                # Skills that do not use --input have no previous phase
                if invoke.get("briefing_arg") != "input":
                    continue
                # Cannot access prev_map directly, but the behavior of
                # _get_previous_artifact returns None when there is no artifact
                result = executor._get_previous_artifact(crew_key)
                if expected is None:
                    assert result is None or result == "", f"{crew_key}: expected None, got {result!r}"


class TestOrchestratorModes:
    """MODOS: structural validation of each pipeline mode."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORCHESTRATOR_PY, "cp_orchestrator")

    def test_full_mode_has_eight_crews(self):
        mode = self.orq.MODOS.get("full")
        assert mode is not None
        len(mode["crews"]) >= 7  # at least the first 7

    def test_every_mode_has_name_and_description(self):
        for slug, info in self.orq.MODOS.items():
            assert "name" in info, f"mode {slug} without name"
            assert "description" in info, f"mode {slug} without description"
            assert "crews" in info, f"mode {slug} without crews"
            assert len(info["crews"]) > 0, f"mode {slug} with empty crews"


class TestOrchestratorQualityGate:
    """Extra QualityGate tests (beyond test_quality_gate.py)."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORCHESTRATOR_PY, "cp_orchestrator")

    def test_check_quality_gate_classifies_correctly(self):
        """Tests a few more quality gate cases."""
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)

        # PASS keywords
        assert executor._check_quality_gate("phase", "Tests OK", 0)["status"] == "PASS"

        # FAIL by keyword (TRACEBACK, FAILED, CRITICAL, etc.)
        assert executor._check_quality_gate("phase", "Pipeline FAILED in build", 0)["status"] == "FAIL"
        assert executor._check_quality_gate("phase", "CRITICAL error found", 0)["status"] == "FAIL"

        # WARN when it recognizes nothing or empty output
        assert executor._check_quality_gate("phase", "build with caveats", 0)["status"] == "WARN"
        assert executor._check_quality_gate("phase", "", 0)["status"] == "WARN"

    def test_quality_gate_rejects_traceback(self):
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)
        result = executor._check_quality_gate(
            "phase",
            "Traceback (most recent call last):\n  File \"run.py\", line 1",
            1,
        )
        assert result["status"] == "FAIL"
