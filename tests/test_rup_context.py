"""rup-context: detect, authorized non-destructive init, pointer note."""
from pathlib import Path

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE
from test_context_persistence import record, run_skill

SKILL = "rup-context"


def project(tmp_path, *dirs):
    root = tmp_path / "proj"
    root.mkdir()
    for d in dirs:
        (root / d).mkdir(parents=True)
    return root, dict(RUP_CONTEXT_DIR=str(root / ".context"))


def env_for(base, extra):
    return dict(base, **extra)


def test_status_reports_missing_marker_and_doc_dirs(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, ".specs", "docs")
    r = run_skill(SKILL, ["--status"], env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "authorized: no" in r.stdout and "exists: no" in r.stdout
    assert ".specs" in r.stdout and "docs" in r.stdout
    assert not (root / ".context").exists()


def init(env, python_cmd, who="Ana"):
    return run_skill(SKILL, ["--init", "--authorized-by", who], env, python_cmd)


def test_init_creates_full_tree_and_marker(clean_env, python_cmd, tmp_path):
    from _shared import consent
    root, extra = project(tmp_path)
    r = init(env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    ctx = root / ".context"
    for rel in consent.standard_tree():
        assert (ctx / rel).exists(), rel
    marker = (ctx / ".rup-standard").read_text(encoding="utf-8")
    assert "authorized_by: Ana" in marker and "version: 1" in marker
    log = (ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8")
    assert "rup-context" in log


def test_init_never_overwrites(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, ".context/docs/02-elaboration", ".context/kanban")
    a = root / ".context/docs/02-elaboration/architecture.md"
    k = root / ".context/kanban/README.md"
    a.write_text("KEEP", encoding="utf-8")
    k.write_text("KEEP", encoding="utf-8")
    assert init(env_for(clean_env, extra), python_cmd).returncode == EXIT_OK
    assert a.read_text(encoding="utf-8") == "KEEP"
    assert k.read_text(encoding="utf-8") == "KEEP"


def test_init_is_idempotent(clean_env, python_cmd, tmp_path):
    from _shared import consent
    root, extra = project(tmp_path)
    env = env_for(clean_env, extra)
    init(env, python_cmd)
    again = consent.init_context(root / ".context", authorized_by="Ana")
    assert again == []
    assert (root / "CLAUDE.md").read_text(encoding="utf-8").count(consent.POINTER_START) == 1
    assert init(env, python_cmd).returncode == EXIT_OK


def test_pointer_note_appended_once_and_preserves_text(clean_env, python_cmd, tmp_path):
    from _shared import consent
    root, extra = project(tmp_path)
    (root / "CLAUDE.md").write_text("OWNER TEXT\n", encoding="utf-8")
    init(env_for(clean_env, extra), python_cmd)
    text = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.startswith("OWNER TEXT") and text.count(consent.POINTER_START) == 1
    assert "`rup-backlog`" in text and "## RUP skills — which one to use" in text
    assert (root / "AGENT.md").is_file()


def test_exit5_message_lists_found_doc_dirs(ctx_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, ".doc")
    env = env_for(ctx_env, extra)
    r = record("rup-ccm", env, python_cmd, tmp_path)
    assert r.returncode == EXIT_NEEDS_CONSENT
    assert ".doc" in r.stdout and "rup-context --init" in r.stdout


def test_context_without_marker_record_exits_5(ctx_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, ".context")
    r = record("rup-ccm", env_for(ctx_env, extra), python_cmd, tmp_path)
    assert r.returncode == EXIT_NEEDS_CONSENT
    assert "marker" in r.stdout


def test_marker_without_version_is_not_authorized(tmp_path):
    from _shared import context
    ctx = tmp_path / ".context"
    ctx.mkdir()
    (ctx / ".rup-standard").write_text("authorized_by: x\n", encoding="utf-8")
    assert context.has_consent(ctx) is False
    (ctx / ".rup-standard").write_text("version: 1\n", encoding="utf-8")
    assert context.has_consent(ctx) is True


def test_init_requires_authorized_by(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path)
    r = run_skill(SKILL, ["--init"], env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_USAGE and "--authorized-by" in r.stdout
    assert not (root / ".context").exists()


def test_init_refuses_when_project_root_missing(clean_env, python_cmd, tmp_path):
    env = env_for(clean_env, dict(RUP_CONTEXT_DIR=str(tmp_path / "nope" / ".context")))
    r = init(env, python_cmd)
    assert r.returncode == EXIT_USAGE
    assert not (tmp_path / "nope").exists()


def test_status_after_init(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path)
    env = env_for(clean_env, extra)
    init(env, python_cmd)
    r = run_skill(SKILL, ["--status"], env, python_cmd)
    assert "authorized: yes" in r.stdout and "missing: 0" in r.stdout
