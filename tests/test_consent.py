"""Authorization gate: no writes into .context/ without the .rup-standard marker."""
from pathlib import Path

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, ORCHESTRATOR, authorize
from test_context_persistence import record, run_skill


def test_record_without_marker_exits_5_and_writes_nothing(ctx_env, python_cmd, tmp_path):
    unauthorized = dict(ctx_env, RUP_CONTEXT_DIR=str(tmp_path / "fresh" / ".context"))
    r = record("cp-ccm", unauthorized, python_cmd, tmp_path)
    assert r.returncode == EXIT_NEEDS_CONSENT, r.stdout + r.stderr
    assert "cp-context --init" in r.stdout and "ask the user" in r.stdout
    assert not (tmp_path / "fresh" / ".context").exists()


def test_estimate_without_marker_exits_5(ctx_env, python_cmd, tmp_path):
    env = dict(ctx_env, RUP_CONTEXT_DIR=str(tmp_path / "fresh" / ".context"))
    r = run_skill(ORCHESTRATOR, ["--estimate"], env, python_cmd)
    assert r.returncode == EXIT_NEEDS_CONSENT, r.stdout + r.stderr
    assert not (tmp_path / "fresh" / ".context").exists()


def test_packet_without_marker_still_prints_with_warning(ctx_env, python_cmd, tmp_path):
    env = dict(ctx_env, RUP_CONTEXT_DIR=str(tmp_path / "fresh" / ".context"))
    r = run_skill("cp-ccm", ["b"], env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "not authorized" in r.stdout


def test_record_with_marker_writes(ctx_env, python_cmd, tmp_path):
    env = dict(ctx_env, RUP_CONTEXT_DIR=str(tmp_path / "fresh" / ".context"))
    authorize(Path(env["RUP_CONTEXT_DIR"]))
    r = record("cp-ccm", env, python_cmd, tmp_path)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert (Path(env["RUP_CONTEXT_DIR"]) / "docs" / "02-elaboration" / "cp-ccm.md").is_file()
