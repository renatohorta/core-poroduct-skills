"""rup-discover: the discovery conversation packet and its hooks in the other skills (INIT-03 §7.7b, §7.12)."""
from pathlib import Path

from conftest import EXIT_OK, full_document
from test_context_persistence import record, run_skill, spec_of

SECTIONS = ["Problem", "Users", "Goals", "Non-goals", "Anti-goals", "Constraints",
            "Open questions"]


def test_discover_packet_defaults_to_inception_and_lists_sections(ctx_env, python_cmd):
    r = run_skill("rup-discover", ["a booking app for clinics"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "**Phase**: Inception" in r.stdout
    for section in SECTIONS:
        assert f"  - {section}" in r.stdout
    assert "one question per message" in r.stdout


def test_discover_record_writes_rup_discover_md(ctx_env, python_cmd, tmp_path):
    spec = spec_of("rup-discover")
    path = tmp_path / "discover.md"
    path.write_text(full_document(spec), encoding="utf-8")
    r = run_skill("rup-discover", ["--record", str(path), "a booking app"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs" / "01-inception"
            / "rup-discover.md").is_file()


def test_discover_artifact_embedded_first_in_requirements_packet(ctx_env, python_cmd, tmp_path):
    record("rup-discover", ctx_env, python_cmd, tmp_path, phase="Inception")
    for phase in ("Inception", "Elaboration"):
        r = run_skill("rup-requirements", ["briefing", "--phase", phase], ctx_env, python_cmd)
        assert r.returncode == EXIT_OK, r.stdout + r.stderr
        assert r.stdout.count("### Discovery (rup-discover)") == 1
        assert "Content of Problem." in r.stdout
        if "### Project Management" in r.stdout:
            assert (r.stdout.index("### Discovery (rup-discover)")
                    < r.stdout.index("### Project Management"))


def test_governance_packet_mentions_rup_backlog_plan(ctx_env, python_cmd):
    r = run_skill("rup-orchestrator", ["briefing"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "rup-backlog --plan <EP-ID> --iteration <R<n>-I<m>>" in r.stdout
