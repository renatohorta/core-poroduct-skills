"""
testcheck.py — value checks of the tests listed in a delivery (INIT-03 §7.7, G5).

Declaration-based: the tests are never run. Each listed test must exist, be tied
to an acceptance criterion (or the bug ID), assert something that is not a
constant, exercise project code, and come with the red output the agent saw.
Python is analysed with `ast` (`testcheck_py`); JS/TS with regexes (`testcheck_js`); any other
language only by name (with a warning).

Pure standard library.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _shared import testcheck_js, testcheck_py
from _shared.cards import Card, acceptance_criteria, covers
from _shared.discipline import _norm, missing_artifacts

REQUIRED_SECTIONS = ["What was done", "Files changed", "Tests", "Red evidence"]
JS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
ABOVE = 3  # comment lines directly above a test that count as "on the test"

_TEST_LINE = re.compile(r"^\s*[-*]\s+`?(?P<ref>.+?::.+?)`?\s+(?:—|–|-)\s+covers\s+(?P<ids>.+?)\s*$",
                        re.IGNORECASE)
_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


@dataclass
class Delivery:
    sections: dict = field(default_factory=dict)  # heading -> body
    tests: list = field(default_factory=list)     # [(path, name, [IDs])]
    red: dict = field(default_factory=dict)       # "path::name" -> failing output
    unparsed: list = field(default_factory=list)  # `- ` lines of ## Tests not understood


@dataclass
class TestInfo:
    __test__ = False  # not a pytest test class
    name: str
    text: str  # the test source plus the comment lines directly above it
    has_assertion: bool
    trivial: bool
    calls_code: bool


# ─── parsing ─────────────────────────────────────────────────────────────

def _ref(path: str, name: str) -> str:
    return f"{path}::{name}"


def _split_ref(ref: str):
    path, _, name = ref.strip().strip("`").partition("::")
    return path.strip(), name.strip()


def _sections(text: str, prefix: str) -> dict:
    found, current = {}, None
    for line in text.splitlines():
        if line.startswith(prefix):
            current = line[len(prefix):].strip()
            found[current] = []
        elif current is not None:
            found[current].append(line)
    return {k: "\n".join(v).strip() for k, v in found.items()}


def _section(sections: dict, name: str) -> str:
    return next((v for k, v in sections.items() if _norm(name) in _norm(k)), "")


def parse_delivery(text: str) -> Delivery:
    """Sections, the `## Tests` lines and the `### path::name` red-evidence blocks."""
    sections = _sections(text or "", "## ")
    delivery = Delivery(sections=sections)
    for line in _section(sections, "Tests").splitlines():
        m = _TEST_LINE.match(line)
        if m:
            path, name = _split_ref(m["ref"])
            ids = [i.strip().strip("`*").strip() for i in m["ids"].split(",")]
            delivery.tests.append((path, name, [i for i in ids if i]))
        elif re.match(r"^\s*[-*]\s+\S", line):
            delivery.unparsed.append(line.strip())
    for heading, body in _sections(_section(sections, "Red evidence"), "### ").items():
        block = _FENCE.search(body)
        delivery.red[_ref(*_split_ref(heading))] = block[1].strip() if block else ""
    return delivery


def id_pattern(ref_id: str) -> re.Pattern:
    """`ST-001/AC-1` also as `st_001_ac_1`, `ST001-AC1`... (case-insensitive)."""
    parts = []
    for token in re.findall(r"[A-Za-z]+|\d+", ref_id):
        parts.append(f"0*{int(token)}" if token.isdigit() else re.escape(token))
    return re.compile(r"(?<![A-Za-z0-9])" + r"[/_-]?".join(parts) + r"(?!\d)", re.IGNORECASE)


# ─── locating and analysing one test ─────────────────────────────────────

def _resolve(project_root: Path, path: str):
    """(file, None) or (None, problem). Never raises."""
    try:
        root = Path(project_root).resolve()
        file = (root / path).resolve()  # an absolute `path` replaces root
    except (OSError, RuntimeError, ValueError):
        return None, "file not found"
    if not file.is_relative_to(root):
        return None, "outside the project"
    if not file.is_file():
        return None, "file not found"
    return file, None


def _find_by_name(text: str, name: str):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if name in line:
            body = lines[max(0, i - ABOVE):i + 40]
            return TestInfo(name, "\n".join(body), True, False, True)
    return None


def find_test(project_root: Path, path: str, name: str):
    """The test `name` in `path` (under project_root), analysed; None if absent/outside."""
    file, _problem = _resolve(project_root, path)
    if file is None or not name:
        return None
    try:
        text = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    suffix = file.suffix.lower()
    if suffix == ".py":
        found = testcheck_py.find(text, name)
        return TestInfo(name, *found) if found else None
    if suffix in JS_SUFFIXES:
        found = testcheck_js.find(text, name)
        return TestInfo(name, *found) if found else None
    return _find_by_name(text, name)


def _analysed(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix == ".py" or suffix in JS_SUFFIXES


# ─── the checks ──────────────────────────────────────────────────────────

def _canonical(declared: str, known) -> str | None:
    """The known ID that `declared` spells (`st_001_ac_1` -> `ST-001/AC-1`), if any."""
    return next((k for k in sorted(known) if id_pattern(k).fullmatch(declared.strip())), None)


def _test_problems(delivery, path, name, ids, allowed, owner, project_root) -> tuple:
    """(problems, canonical IDs the test both declares and references)."""
    ref, out, referenced = _ref(path, name), [], set()
    file, problem = _resolve(project_root, path)
    info = find_test(project_root, path, name) if file else None
    if problem:
        out.append(f"{ref}: {problem}")
    elif info is None:
        out.append(f"{ref}: test not found")
    if not ids:
        out.append(f"{ref}: declares no covered ID")
    for i in ids:
        if _canonical(i, allowed) is None:
            out.append(f"{ref}: {i} is not {owner}")
    if info is not None:
        for i in ids:  # the test source only: the delivery's name is a claim, not the test
            if id_pattern(i).search(info.text):
                referenced.add(_canonical(i, allowed) or i)
            else:
                out.append(f"{ref}: does not reference {i}")
        if not info.has_assertion:
            out.append(f"{ref}: has no assertion")
        elif info.trivial:
            out.append(f"{ref}: only asserts constants (trivial)")
        if not info.calls_code:
            out.append(f"{ref}: never calls project code")
    if not delivery.red.get(ref):
        out.append(f"{ref}: no red evidence")
    return out, referenced


def check_delivery(delivery: Delivery, task: Card, story, project_root: Path) -> list:
    """Problems with the delivery's tests, in document order; [] means OK."""
    problems = []
    headings = "\n".join(f"## {h}" for h in delivery.sections)
    missing = missing_artifacts(headings, REQUIRED_SECTIONS)
    if missing:
        problems.append("The delivery lacks required sections: "
                        + ", ".join(f"## {m}" for m in missing))
    problems += [f"Unrecognised line in ## Tests (expected `- <path>::<test> — covers <ID>`): {u}"
                 for u in delivery.unparsed]
    if not delivery.tests:
        problems.append("The delivery lists no tests.")

    criteria = acceptance_criteria(story) if story is not None else []
    story_name = story.id if story is not None else "the parent story"
    if task.type == "bug":
        allowed, owner = {task.id, *criteria}, f"the bug ID {task.id} or a criterion of {story_name}"
    else:
        allowed, owner = set(criteria), f"a criterion of {story_name}"
    covered = set()  # only IDs a found test both declares and references count
    for path, name, ids in delivery.tests:
        found, referenced = _test_problems(delivery, path, name, ids, allowed, owner, project_root)
        problems += found
        covered |= referenced
    if task.type == "bug":
        if task.id not in covered:
            problems.append(f"No test references the bug ID {task.id}.")
    else:
        problems += [f"Criterion {c} (task Covers) has no test." for c in covers(task)
                     if c not in covered]
    return problems


def delivery_warnings(delivery: Delivery, project_root: Path) -> list:
    """Non-blocking notes: tests in languages that are only checked by name."""
    return [f"{_ref(path, name)}: language not analysed (only the test name was checked)"
            for path, name, _ in delivery.tests
            if not _analysed(path) and _resolve(project_root, path)[0] is not None]
