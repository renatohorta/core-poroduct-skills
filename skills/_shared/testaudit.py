"""
testaudit.py — static audit of a whole Python test suite (cp-test --static-audit).

Where `testcheck` checks the tests named in one delivery, this scans every test
of the project and reports the ones that cannot catch a bug:

- NO_ASSERT        no assertion (assert, assert*() call, pytest.raises, or a
                   module helper that asserts);
- TRIVIAL_ASSERT   every assertion is constant or a tautology (`assert True`,
                   `assert 1 == 1`, `assert x == x`, a non-empty literal);
- NO_PROJECT_CALL  never calls code outside builtins/pytest;
- SELF_MOCK        patches a function defined in the very module it tests
                   (`patch("app.service.compute")` in test_service.py), so the
                   test checks the mock, not the unit.

Tests are never run. Pure standard library.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

from _shared.testcheck_py import _Analysis, _callee, _pytest_names

KINDS = {
    "NO_ASSERT": "no assertion",
    "TRIVIAL_ASSERT": "only constant/tautological assertions",
    "NO_PROJECT_CALL": "calls no project code",
    "SELF_MOCK": "mocks the unit under test",
}
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", ".context", "__pycache__",
             ".tox", ".nox", "build", "dist", ".mypy_cache", ".pytest_cache"}
_PATCHERS = {"patch", "setattr", "object"}  # mock.patch / monkeypatch.setattr / patch.object


def test_files(root) -> list:
    root = Path(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            if f.endswith(".py") and (f.startswith("test_") or f.endswith("_test.py")):
                found.append(Path(dirpath) / f)
    return found


def subject_stem(path: Path) -> str:
    stem = path.stem
    return stem[5:] if stem.startswith("test_") else stem[:-5] if stem.endswith("_test") else stem


def _defined_names(module_path: Path) -> set:
    """Top-level functions/classes defined (not imported) in a module."""
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return set()
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _subject_defs(root: Path, test_path: Path, cache: dict) -> tuple:
    """(stem, names defined in the module under test) — '' / empty if not found."""
    stem = subject_stem(test_path)
    if stem not in cache:
        names = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if f"{stem}.py" in filenames:
                names |= _defined_names(Path(dirpath) / f"{stem}.py")
        cache[stem] = names
    return stem, cache[stem]


def _self_mocks(func, extra_nodes, stem: str, defs: set) -> list:
    """Patch targets that replace a function of the module under test."""
    hits = []
    for node in [*ast.walk(func), *(x for d in extra_nodes for x in ast.walk(d))]:
        if not isinstance(node, ast.Call):
            continue
        final, _ = _callee(node.func)
        if final not in _PATCHERS or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str) and "." in first.value:
            *mod, attr = first.value.split(".")
            if mod and mod[-1] == stem and attr in defs:
                hits.append(first.value)
        elif isinstance(first, ast.Name) and first.id == stem and len(node.args) > 1:
            second = node.args[1]
            if isinstance(second, ast.Constant) and second.value in defs:
                hits.append(f"{stem}.{second.value}")
    return hits


def _asserting_helpers(tree) -> set:
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("test"):
            if any(isinstance(x, ast.Assert) or (isinstance(x, ast.Call) and
                   (_callee(x.func)[0] or "").startswith("assert")) for x in ast.walk(n)):
                names.add(n.name)
    return names


def _tests_in(tree):
    """(qualified name, function node, class node or None)."""
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            yield n.name, n, None
        elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and m.name.startswith("test"):
                    yield f"{n.name}::{m.name}", m, n


def audit(root) -> dict:
    """{'files': n, 'tests': n, 'findings': [(kind, path, line, test, detail)]}."""
    root = Path(root).resolve()
    findings, n_tests, files, cache = [], 0, test_files(root), {}
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            findings.append(("SYNTAX", path.relative_to(root).as_posix(), 0, "-", "cannot parse"))
            continue
        modules, helpers = _pytest_names(tree)
        asserting = _asserting_helpers(tree)
        stem, defs = _subject_defs(root, path, cache)
        rel = path.relative_to(root).as_posix()
        for name, func, cls in _tests_in(tree):
            n_tests += 1
            any_assert, trivial, calls = _Analysis(func, modules, helpers).run()
            uses_helper = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                              and x.func.id in asserting for x in ast.walk(func))
            if not any_assert and not uses_helper:
                findings.append(("NO_ASSERT", rel, func.lineno, name, KINDS["NO_ASSERT"]))
            elif trivial and not uses_helper:
                findings.append(("TRIVIAL_ASSERT", rel, func.lineno, name,
                                 KINDS["TRIVIAL_ASSERT"]))
            if not calls and not uses_helper:
                findings.append(("NO_PROJECT_CALL", rel, func.lineno, name,
                                 KINDS["NO_PROJECT_CALL"]))
            decorators = list(func.decorator_list) + (list(cls.decorator_list) if cls else [])
            for target in _self_mocks(func, decorators, stem, defs):
                findings.append(("SELF_MOCK", rel, func.lineno, name,
                                 f"patches `{target}`, defined in the module under test"))
    return {"files": len(files), "tests": n_tests, "findings": findings}


def render(result, root, sha="") -> str:
    by_kind = {}
    for f in result["findings"]:
        by_kind[f[0]] = by_kind.get(f[0], 0) + 1
    flagged = len({(f[1], f[3]) for f in result["findings"]})
    md = [f"# Static test audit — @ {sha[:12] or '(no git SHA)'}", "",
          f"- Root: `{root}`",
          f"- Test files: {result['files']} · tests: {result['tests']} · flagged tests: {flagged}",
          ""]
    md += [f"- {k} ({KINDS.get(k, k)}): {n}" for k, n in sorted(by_kind.items())] or \
        ["- No findings."]
    if result["findings"]:
        md += ["", "| Kind | Location | Test | Detail | Verdict |", "|---|---|---|---|---|"]
        md += [f"| {k} | `{p}:{ln}` | `{t}` | {d} |  |"
               for k, p, ln, t, d in sorted(result["findings"], key=lambda x: (x[1], x[2]))]
        md += ["", "Fill **Verdict** for each row: `fix` (rewrite the test), `legit` with the "
               "reason (e.g. 'checks it does not raise'), or `delete`."]
    md += ["", "Heuristics only: Python tests are analysed; other languages are listed by "
           "the ecosystem tools (references/audit.md)."]
    return "\n".join(md) + "\n"
