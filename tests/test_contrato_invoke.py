"""DT-03 — Validates the orchestrator's `invoke` contract against the real argparse.

The orchestrator declares, in the `CREWS` dict, how each skill is triggered
(`invoke.briefing_arg` and `invoke.output`). This metadata is maintained by hand:
if a skill changes its argparse and the metadata does not follow, the phase
breaks only at runtime — and, because of the quality gate, it could even go
unnoticed.

The check does not regex the source code: it uses each skill's real `--help`
(which DT-07 guaranteed always works) and, in the strongest test, runs the
command line the orchestrator itself would build.

This file would have caught BUG-05 (the goal-loop mode sent only `--goal`, but
the skill required `--steps`).
"""
import importlib.util
import subprocess

import pytest

from conftest import EXIT_OK, REPO_ROOT, SKILLS_DIR

ORQ_RUN = SKILLS_DIR / "cp-orchestrator" / "scripts" / "run.py"


def _load_orchestrator():
    """Imports the orchestrator's run.py as a module, to read CREWS/MODOS."""
    spec = importlib.util.spec_from_file_location("orq_run", ORQ_RUN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ORQ = _load_orchestrator()

# Crews that point to an external skill (NEXUS runs natively, without subprocess).
CREWS_WITH_SKILL = sorted(
    k for k, v in ORQ.CREWS.items()
    if k in ORQ.SKILL_PATHS and ORQ.SKILL_PATHS[k].exists()
)

# Crews executed natively by the orchestrator (NexusExecutor), without subprocess.
NATIVE_CREWS = {"full-dev"}

# Default applied by `_build_cli_args` when the crew does not declare `invoke`.
# The 8 pipeline crews depend on it — and that is intentional, not an oversight.
INVOKE_DEFAULT = {"briefing_arg": "input", "output": True}


def effective_invoke(crew_key: str) -> dict:
    """The `invoke` metadata as the production code sees it."""
    return ORQ.CREWS[crew_key].get("invoke", INVOKE_DEFAULT)


# Which flag each briefing_arg requires to exist in the skill's argparse.
FLAG_PER_BRIEFING_ARG = {
    "goal": "--goal",
    "daemon": "--daemon",
    "dir": "--dir",
    "input": "--input",
    "inspect": "--inspect",
    "positional": None,  # positional does not appear as a flag
}


@pytest.fixture(scope="module")
def help_per_crew(clean_env, python_cmd):
    """`--help` output of each skill referenced by the orchestrator."""
    outputs = {}
    for ck in CREWS_WITH_SKILL:
        path = ORQ.SKILL_PATHS[ck]
        r = subprocess.run(
            [python_cmd, str(path), "--help"],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT), env=clean_env, encoding="utf-8", errors="replace",
        )
        assert r.returncode == EXIT_OK, f"{ck}: --help failed\n{r.stdout}{r.stderr}"
        outputs[ck] = r.stdout
    return outputs


@pytest.mark.parametrize("crew_key", CREWS_WITH_SKILL)
def test_briefing_arg_is_known_value(crew_key):
    """The effective `briefing_arg` must be one of the modes `_build_cli_args` handles.

    A new value (e.g. "daemon" when it was introduced) without the corresponding
    branch silently falls into the `else` branch, which passes the briefing as
    positional — and the skill rejects it.
    """
    briefing_arg = effective_invoke(crew_key).get("briefing_arg")
    assert briefing_arg in FLAG_PER_BRIEFING_ARG, (
        f"{crew_key}: unknown briefing_arg: {briefing_arg!r}. "
        f"Add the branch in _build_cli_args before using it.")


@pytest.mark.parametrize("crew_key", CREWS_WITH_SKILL)
def test_declared_output_matches_argparse(crew_key, help_per_crew):
    """`invoke.output` must reflect whether the skill really accepts `--output`.

    Declaring `output=True` on a skill that does not accept it makes its argparse
    reject the flag and the phase dies.
    """
    declared = effective_invoke(crew_key).get("output", True)
    accepts = "--output" in help_per_crew[crew_key]
    assert declared == accepts, (
        f"{crew_key}: invoke.output={declared} but the skill "
        f"{'accepts' if accepts else 'does NOT accept'} --output")


@pytest.mark.parametrize("crew_key", CREWS_WITH_SKILL)
def test_briefing_arg_exists_in_skill(crew_key, help_per_crew):
    """The flag required by `briefing_arg` must exist in the skill's argparse."""
    briefing_arg = effective_invoke(crew_key)["briefing_arg"]
    flag = FLAG_PER_BRIEFING_ARG[briefing_arg]
    if flag is None:
        return
    assert flag in help_per_crew[crew_key], (
        f"{crew_key}: invoke.briefing_arg={briefing_arg!r} requires {flag}, "
        f"absent from the skill's --help")


@pytest.mark.parametrize("crew_key", CREWS_WITH_SKILL)
def test_command_built_by_orchestrator_is_accepted(crew_key, clean_env, python_cmd,
                                                   tmp_path):
    """The strong test: runs the line the orchestrator would build, with --dry-run.

    Builds the arguments with the same `_build_cli_args` used in production and
    verifies the skill accepts them. An argparse error (argparse exit 2,
    "unrecognized arguments", "required") fails.

    This is the test that would have caught BUG-05.
    """
    # Real constructor: building the executor by hand hides new attributes.
    executor = ORQ.PipelineExecutor(
        briefing="test briefing", mode="full",
        output_dir=str(tmp_path), python_cmd=python_cmd,
    )

    args = executor._build_cli_args(crew_key)
    assert args is not None, f"{crew_key}: _build_cli_args returned None"

    # cp-agile without --dry-run starts a polling daemon: does not run here.
    if "--daemon" in args:
        pytest.skip("cp-agile in daemon mode does not terminate on its own")

    r = subprocess.run(
        args + ["--dry-run"], capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=clean_env, encoding="utf-8", errors="replace",
    )
    output = r.stdout + r.stderr

    assert "unrecognized arguments" not in output, (
        f"{crew_key}: the orchestrator passes a flag the skill rejects.\n"
        f"  command: {' '.join(str(a) for a in args)}\n{output}")
    assert "the following arguments are required" not in output, (
        f"{crew_key}: the skill requires an argument the orchestrator does not send "
        f"(the BUG-05 case).\n  command: {' '.join(str(a) for a in args)}\n{output}")
    assert r.returncode == EXIT_OK, (
        f"{crew_key}: command built by the orchestrator failed (exit "
        f"{r.returncode}).\n  command: {' '.join(str(a) for a in args)}\n{output}")


def test_every_mode_references_existing_crew():
    """No mode can point to a nonexistent crew.

    `full-dev` is the legitimate exception: it runs natively via NexusExecutor,
    without an entry in CREWS.
    """
    for mode, info in ORQ.MODOS.items():
        for ck in info["crews"]:
            assert ck in ORQ.CREWS or ck in NATIVE_CREWS, (
                f"mode {mode!r} references nonexistent crew: {ck!r}")


def test_every_crew_with_skill_has_valid_path():
    """Every crew that points to an external skill needs the run.py to exist."""
    missing = [
        ck for ck, path in ORQ.SKILL_PATHS.items()
        if ck in ORQ.CREWS and not path.exists()
    ]
    assert not missing, f"skills declared but absent on disk: {missing}"
