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
    line = next(l for l in r.stdout.splitlines() if l.startswith("other doc dirs:"))
    assert ".specs" in line and "docs" in line
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


def test_init_refuses_to_overwrite_invalid_marker(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, ".context")
    marker = root / ".context" / ".rup-standard"
    marker.write_bytes(b"authorized_by: x\n")
    r = init(env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_USAGE and "invalid" in r.stdout
    assert marker.read_bytes() == b"authorized_by: x\n"
    assert not (root / ".context" / "kanban").exists()


# ─── import existing docs ────────────────────────────────────────────────
VISION = "docs/01-inception/vision-and-scope.md"
ARCH = "docs/02-elaboration/architecture.md"


def import_project(tmp_path, clean_env):
    from conftest import authorize
    root, extra = project(tmp_path, ".specs", "docs")
    (root / ".specs" / "vision.md").write_text("# Old vision\nWe build X.\n", encoding="utf-8")
    (root / "docs" / "arch.txt").write_text("Old architecture\n", encoding="utf-8")
    (root / "docs" / "image.png").write_bytes(b"\x89PNG")
    authorize(root / ".context")
    return root, env_for(clean_env, extra)


def import_doc(*sections):
    return "\n\n".join(f"## {t}\n{b}" for t, b in sections)


def test_import_packet_lists_inventory_and_targets(clean_env, python_cmd, tmp_path):
    from _shared import consent
    root, env = import_project(tmp_path, clean_env)
    r = run_skill(SKILL, ["--import"], env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "vision.md" in r.stdout and "arch.txt" in r.stdout
    assert "image.png" not in r.stdout
    for target in consent.IMPORT_TARGETS.values():
        assert target in r.stdout
    assert "Source:" in r.stdout and "--record-import" in r.stdout


def test_import_requires_consent(clean_env, python_cmd, tmp_path):
    root, extra = project(tmp_path, "docs")
    r = run_skill(SKILL, ["--import"], env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_NEEDS_CONSENT


def test_import_with_nothing_to_import(clean_env, python_cmd, tmp_path):
    from conftest import authorize
    root, extra = project(tmp_path)
    authorize(root / ".context")
    r = run_skill(SKILL, ["--import"], env_for(clean_env, extra), python_cmd)
    assert r.returncode == EXIT_OK and "nothing to import" in r.stdout


def test_record_import_creates_missing_target(clean_env, python_cmd, tmp_path):
    root, env = import_project(tmp_path, clean_env)
    target = root / ".context" / VISION
    assert not target.exists()
    doc = import_doc((VISION, "Source: .specs/vision.md\nWe build X."))
    r = run_skill(SKILL, ["--record-import", "-"], env, python_cmd, stdin=doc)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    text = target.read_text(encoding="utf-8")
    assert text.startswith("# Vision and scope\n")
    assert '<!-- rup-import source=".specs/vision.md"' in text
    assert "We build X." in text and "<!-- /rup-import -->" in text
    rows = [l for l in (root / ".context/tracking/rup-log.md").read_text(
        encoding="utf-8").splitlines() if "import" in l and l.startswith("| 20")]
    assert len(rows) == 1 and ".specs/vision.md" in rows[0]


def test_record_import_appends_block_and_keeps_existing_lines(clean_env, python_cmd, tmp_path):
    root, env = import_project(tmp_path, clean_env)
    target = root / ".context" / ARCH
    target.parent.mkdir(parents=True)
    existing = "# Architecture\nCurated line 1\nCurated line 2\n"
    target.write_text(existing, encoding="utf-8")
    doc = import_doc((ARCH, "Source: docs/arch.txt\nOld architecture"))
    r = run_skill(SKILL, ["--record-import", "-"], env, python_cmd, stdin=doc)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    text = target.read_text(encoding="utf-8")
    assert text.startswith(existing)
    assert '<!-- rup-import source="docs/arch.txt" date="' in text
    assert text.rstrip().endswith("<!-- /rup-import -->")
    assert "Old architecture" in text


def test_record_import_rejects_unknown_target_or_missing_source(clean_env, python_cmd, tmp_path):
    root, env = import_project(tmp_path, clean_env)
    target = root / ".context" / ARCH
    target.parent.mkdir(parents=True)
    target.write_text("KEEP", encoding="utf-8")
    cases = [
        import_doc((VISION, "Source: a.md\nok"), ("docs/nope.md", "Source: a.md\nx")),
        import_doc((VISION, "Source: a.md\nok"), (ARCH, "no source line here")),
        "no sections at all",
    ]
    for doc in cases:
        r = run_skill(SKILL, ["--record-import", "-"], env, python_cmd, stdin=doc)
        assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
        assert not (root / ".context" / VISION).exists()
        assert target.read_text(encoding="utf-8") == "KEEP"


def test_import_never_touches_originals(clean_env, python_cmd, tmp_path):
    root, env = import_project(tmp_path, clean_env)
    originals = [root / ".specs" / "vision.md", root / "docs" / "arch.txt"]
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in originals]
    run_skill(SKILL, ["--import"], env, python_cmd)
    doc = import_doc((VISION, "Source: .specs/vision.md\nX"), (ARCH, "Source: docs/arch.txt\nY"))
    r = run_skill(SKILL, ["--record-import", "-"], env, python_cmd, stdin=doc)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in originals] == before
