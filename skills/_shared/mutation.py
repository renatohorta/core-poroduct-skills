"""
mutation.py — mutation testing for Python projects (cp-test --audit, ADR-0016).

Coverage says which lines ran; mutation says whether a test would notice if a
line were wrong. This module:

- enumerates AST mutants of a Python file (`candidates`, `apply`);
- runs them against the project's own test command in disposable copies of the
  project, one per worker, in parallel, resumable (`run`);
- consolidates the results per module (`report`) and keeps a triage table of the
  survivors whose rows are checked (`triage_check`).

Only line + description are stored per mutant (`ast.unparse` reformats the whole
file); `show` rebuilds a mutant from its index when a diff is needed.

The project's test command comes from `.context/tests/profile.json`, written by
the agent (step A0). The original repository is never modified, and git is never
run: the commit SHA is read from the `.git` files.

Pure standard library.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# ─── mutant generator ────────────────────────────────────────────────────

SWAP_CMP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt,
            ast.Gt: ast.LtE, ast.LtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In,
            ast.Is: ast.IsNot, ast.IsNot: ast.Is}
SWAP_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
            ast.Div: ast.Mult, ast.FloorDiv: ast.Mult}
# Calls whose removal only drops a log/print line (mass equivalent mutants).
SKIP_CALL_ROOTS = {"logger", "log", "logging", "_log", "_logger", "warnings", "print"}

KINDS = ("cmp", "bool", "unnot", "bin", "aug", "bool_const", "int", "negif",
         "retnone", "delcall")


def _root_name(func) -> str:
    while isinstance(func, (ast.Attribute, ast.Call)):
        func = func.func if isinstance(func, ast.Call) else func.value
    return func.id if isinstance(func, ast.Name) else ""


def _annotation_nodes(tree) -> set:
    """ids of nodes inside type annotations (mutating them changes nothing)."""
    skip = set()
    for n in ast.walk(tree):
        anns = []
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            anns.append(n.returns)
            a = n.args
            anns += [x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs]
            anns += [x.annotation for x in (a.vararg, a.kwarg) if x]
        elif isinstance(n, ast.AnnAssign):
            anns.append(n.annotation)
        for ann in anns:
            if ann is not None:
                skip |= {id(x) for x in ast.walk(ann)}
    return skip


def candidates(src: str) -> list:
    """Mutants of a source: [(index, kind, sub, line, description)].

    `index` is the position of the node in `ast.walk` order, so `apply` can find
    it again on a fresh parse of the same source.
    """
    tree = ast.parse(src)
    skip = _annotation_nodes(tree)
    out = []
    for i, n in enumerate(ast.walk(tree)):
        if id(n) in skip:
            continue
        ln = getattr(n, "lineno", 0)
        if isinstance(n, ast.Compare):
            for j, op in enumerate(n.ops):
                if type(op) in SWAP_CMP:
                    out.append((i, "cmp", j, ln,
                                f"{type(op).__name__} -> {SWAP_CMP[type(op)].__name__}"))
        elif isinstance(n, ast.BoolOp):
            new = "Or" if isinstance(n.op, ast.And) else "And"
            out.append((i, "bool", 0, ln, f"{type(n.op).__name__} -> {new}"))
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            out.append((i, "unnot", 0, ln, "remove not"))
        elif isinstance(n, ast.BinOp) and type(n.op) in SWAP_BIN:
            out.append((i, "bin", 0, ln,
                        f"{type(n.op).__name__} -> {SWAP_BIN[type(n.op)].__name__}"))
        elif isinstance(n, ast.AugAssign) and type(n.op) in SWAP_BIN:
            out.append((i, "aug", 0, ln,
                        f"{type(n.op).__name__}= -> {SWAP_BIN[type(n.op)].__name__}="))
        elif isinstance(n, ast.Constant) and type(n.value) is bool:
            out.append((i, "bool_const", 0, ln, f"{n.value} -> {not n.value}"))
        elif isinstance(n, ast.Constant) and type(n.value) is int:
            out.append((i, "int", 0, ln, f"{n.value} -> {n.value + 1}"))
        elif isinstance(n, ast.If):
            out.append((i, "negif", 0, ln, "negate if"))
        elif isinstance(n, ast.Return) and n.value is not None and not (
                isinstance(n.value, ast.Constant) and n.value.value is None):
            out.append((i, "retnone", 0, ln, "return None"))
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
                and _root_name(n.value.func) not in SKIP_CALL_ROOTS:
            out.append((i, "delcall", 0, ln, "remove call " + ast.unparse(n.value.func)[:50]))
    return out


def apply(src: str, cand) -> str:
    """The source with one mutant applied (normalised by `ast.unparse`)."""
    index, kind, sub = cand[0], cand[1], cand[2]
    tree = ast.parse(src)
    nodes = list(ast.walk(tree))
    n = nodes[index]
    if kind == "cmp":
        n.ops[sub] = SWAP_CMP[type(n.ops[sub])]()
    elif kind == "bool":
        n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
    elif kind == "unnot":
        for parent in nodes:
            for field, val in ast.iter_fields(parent):
                if val is n:
                    setattr(parent, field, n.operand)
                elif isinstance(val, list):
                    for k, v in enumerate(val):
                        if v is n:
                            val[k] = n.operand
    elif kind in ("bin", "aug"):
        n.op = SWAP_BIN[type(n.op)]()
    elif kind == "bool_const":
        n.value = not n.value
    elif kind == "int":
        n.value = n.value + 1
    elif kind == "negif":
        n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
    elif kind in ("retnone", "delcall"):
        n.value = ast.Constant(value=None)
    else:
        raise ValueError(f"unknown mutant kind {kind!r}")
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def show(src: str, cand, path: str = "file.py") -> str:
    """A readable unified diff of a mutant (both sides normalised by ast.unparse)."""
    before = ast.unparse(ast.parse(src)).splitlines(keepends=True)
    after = apply(src, cand).splitlines(keepends=True)
    return "".join(difflib.unified_diff(before, after, f"a/{path}", f"b/{path}", n=2))


# ─── line filters (--lines file.py:10-40) ────────────────────────────────

def parse_lines(specs) -> dict:
    """['a.py:10-20', 'a.py:33', 'b.py'] -> {'a.py': [(10, 20), (33, 33)], 'b.py': None}."""
    out = {}
    for spec in specs or []:
        m = re.match(r"^(.+?)(?::(\d+)(?:-(\d+))?)?$", spec.strip())
        if not m:
            raise ValueError(f"bad --lines value {spec!r} (want file.py:START-END)")
        path, a, b = m[1], m[2], m[3]
        if a is None:
            out[path] = None
            continue
        rng = (int(a), int(b or a))
        if rng[0] > rng[1]:
            raise ValueError(f"bad range in {spec!r}")
        if out.get(path, []) is not None:
            out.setdefault(path, []).append(rng)
    return out


def in_ranges(line: int, ranges) -> bool:
    return ranges is None or any(a <= line <= b for a, b in ranges)


# ─── project profile (step A0) ───────────────────────────────────────────

DEFAULT_IGNORE = [".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
                  ".context", "__pycache__", ".pytest_cache", ".mypy_cache",
                  ".ruff_cache", ".tox", ".nox", "dist", "build", "htmlcov",
                  "media", "staticfiles", ".idea", ".vscode"]

PROFILE_TEMPLATE = {
    "language": "python",
    "runner": "pytest",
    "python": ".venv/bin/python",
    "test_command": ["{python}", "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider",
                     "-W", "ignore", "{tests}"],
    "killed_exit_codes": [1],
    "workers": 0,
    "env": {"DB_NAME": "test_mut{worker}"},
    "copy_ignore": DEFAULT_IGNORE,
    "test_map": {"src/app": ["src/app/tests"]},
    "priority": {"src/app/service.py": ["src/app/tests/test_service.py"]},
    "timeout_factor": 3,
    "timeout_extra_s": 30,
    "notes": "How external services are isolated (DB per worker, fake queues, moto…).",
}

TEMPLATE_HELP = """\
Fields of profile.json (paths relative to the project root):
  python            interpreter of the project ({python} in test_command); default: this one
  test_command      the suite command; {tests} expands to the selected test paths
                    (appended at the end when absent). Keep a stop-on-first-failure
                    flag (pytest -x) so a killed mutant is fast.
  killed_exit_codes exit codes that mean "a test failed" (pytest: 1). Any other
                    non-zero code is an error (collection/usage), not a kill.
  workers           parallel copies; 0 = CPU cores - 1
  env               extra env per worker; {worker} is the worker number (own DB!)
  copy_ignore       directory names not copied into the worker copies
  test_map          source path prefix -> tests to run (longest prefix wins;
                    default: the whole suite)
  priority          source file -> tests to run first (default: test_<module>.py)
  timeout_factor / timeout_extra_s   mutant timeout = baseline * factor + extra
"""


def load_profile(path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ProfileError(f"no profile at {path}: write it first (step A0, --profile-template)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ProfileError(f"cannot read {path}: {e}")
    if not isinstance(data, dict):
        raise ProfileError(f"{path}: the profile must be a JSON object")
    cmd = data.get("test_command")
    if not (isinstance(cmd, list) and cmd and all(isinstance(c, str) for c in cmd)):
        raise ProfileError(f"{path}: `test_command` must be a non-empty list of strings")
    profile = {k: v for k, v in PROFILE_TEMPLATE.items() if k not in ("test_map", "priority")}
    profile.update({"test_map": {}, "priority": {}, "env": {}, "python": ""})
    profile.update(data)
    return profile


class ProfileError(Exception):
    pass


class RunError(Exception):
    pass


# ─── git SHA without running git ─────────────────────────────────────────

def head_sha(project_root) -> str:
    """The commit SHA of HEAD, read from the `.git` files ('' if unknown)."""
    git = Path(project_root) / ".git"
    try:
        if git.is_file():  # worktree / submodule: "gitdir: <path>"
            target = git.read_text(encoding="utf-8").split(":", 1)[1].strip()
            git = (Path(project_root) / target).resolve()
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(":", 1)[1].strip()
        common = git
        if (git / "commondir").is_file():
            common = (git / (git / "commondir").read_text(encoding="utf-8").strip()).resolve()
        for base in (git, common):
            if (base / ref).is_file():
                return (base / ref).read_text(encoding="utf-8").strip()
        packed = common / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.endswith(" " + ref):
                    return line.split(" ", 1)[0]
    except (OSError, IndexError):
        pass
    return ""


# ─── project tree: fingerprint and copies ────────────────────────────────

def _walk(root: Path, ignore: set):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ignore)
        for f in sorted(filenames):
            if not f.endswith((".pyc", ".pyo")):
                yield Path(dirpath) / f


TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}


def is_test_file(rel: Path) -> bool:
    """Test code may change during an audit (that is how a gap is closed)."""
    name = rel.name
    return (name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".spec.js",
                                                       ".test.ts", ".spec.ts"))
            or name == "conftest.py" or any(part in TEST_DIRS for part in rel.parts[:-1]))


def fingerprint(root, ignore) -> str:
    """Hash of every copied non-test file (path + content): detects code that changed
    under the run. Test files are left out: adding the test that kills a survivor
    is the point of `--rerun-survivors`."""
    root, h = Path(root), hashlib.sha256()
    for p in _walk(root, set(ignore)):
        if is_test_file(p.relative_to(root)):
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        h.update(str(p.relative_to(root)).replace("\\", "/").encode())
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _copy(src: Path, dst: Path, ignore) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*ignore, "*.pyc"),
                    symlinks=True)


def default_workdir(project_root) -> Path:
    key = hashlib.sha256(str(Path(project_root).resolve()).encode()).hexdigest()[:10]
    return Path(tempfile.gettempdir()) / "cp-mutation" / key


# ─── which tests run for a file ──────────────────────────────────────────

def tests_for(profile, path: str) -> list:
    best = ""
    for prefix in profile.get("test_map") or {}:
        if path.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    return list(profile["test_map"][best]) if best else []


def priority_tests(profile, project_root, path: str, ignore) -> list:
    given = (profile.get("priority") or {}).get(path)
    if given:
        return list(given)
    name = "test_" + Path(path).stem + ".py"
    root = Path(project_root)
    return [str(p.relative_to(root)).replace("\\", "/")
            for p in _walk(root, set(ignore)) if p.name == name]


def command(profile, python: str, tests: list) -> list:
    out, placed = [], False
    for part in profile["test_command"]:
        if part == "{tests}":
            out += tests
            placed = True
        else:
            out.append(part.replace("{python}", python))
    return out if placed else out + tests


# ─── results ─────────────────────────────────────────────────────────────

def load_results(path) -> dict:
    """{(file, index): latest record} — later lines win (re-runs of survivors)."""
    latest = {}
    path = Path(path)
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue  # a line cut by an interrupted run
            latest[(r["file"], r["idx"])] = r
    return latest


def detected(status: str) -> bool:
    return status in ("killed", "timeout")


# ─── the run ─────────────────────────────────────────────────────────────

def parse_budget(text) -> float | None:
    if not text:
        return None
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([hms]?)\s*$", str(text))
    if not m:
        raise ValueError(f"bad budget {text!r} (examples: 2h, 30m, 900s)")
    return float(m[1]) * {"h": 3600, "m": 60, "s": 1, "": 1}[m[2]]


def _tail(text: str) -> str:
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return lines[-1][:300] if lines else ""


def _exec(cmd, cwd, env, timeout):
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, time.time() - t, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "timeout", time.time() - t, ""
    except OSError as e:
        return "oserror", time.time() - t, str(e)


def run(profile, *, project_root, out_dir, files, lines=None, workers=None,
        budget_s=None, fresh=False, workdir=None, rerun_survivors=False, log=print) -> dict:
    """Run the mutants of `files` (paths relative to `project_root`).

    State lives in `out_dir` (`.context/tests/mutation/`): `state.json` (SHA,
    tree fingerprint, baselines, totals) and `results.jsonl` (one line per mutant,
    appended, resumable). Raises RunError for anything that invalidates the run.
    """
    project_root = Path(project_root).resolve()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path, results_path = out_dir / "state.json", out_dir / "results.jsonl"
    ignore = list(profile.get("copy_ignore") or DEFAULT_IGNORE)
    lines = lines or {}
    files = list(dict.fromkeys(list(files or []) + list(lines)))
    if not files:
        raise RunError("no files to mutate (--files or --lines)")

    sources = {}
    for f in files:
        p = project_root / f
        if not p.is_file():
            raise RunError(f"{f}: not found under {project_root}")
        text = p.read_text(encoding="utf-8")
        try:
            ast.parse(text)
        except SyntaxError as e:
            raise RunError(f"{f}: not valid Python ({e})")
        sources[f] = text

    sha, tree = head_sha(project_root), fingerprint(project_root, ignore)
    if fresh:
        for p in (state_path, results_path):
            if p.exists():
                p.unlink()
    state = {}
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("tree") != tree:
            raise RunError(
                "the code under test changed since this mutation run started (a non-test "
                "file was edited, or the branch/commit changed): results would mix two "
                f"versions of the code. Go back to that tree (commit "
                f"{state.get('sha', '')[:12] or 'unknown'}), or start over with --fresh.")
        if state.get("sha", "") != sha:
            log(f"note: commit {state.get('sha', '')[:12] or '?'} -> {sha[:12] or '?'}; "
                "only test files changed, so earlier results stay valid.")

    nworkers = int(workers or profile.get("workers") or 0) or max(1, (os.cpu_count() or 2) - 1)
    workdir = Path(workdir) if workdir else default_workdir(project_root)
    python = profile.get("python") or sys.executable
    if not Path(python).is_absolute() and (project_root / python).exists():
        python = str(project_root / python)

    # Jobs: every candidate in the selected lines not already done.
    done = load_results(results_path)
    jobs = []
    for f in files:
        for c in candidates(sources[f]):
            if not in_ranges(c[3], lines.get(f) if f in lines else None):
                continue
            prev = done.get((f, c[0]))
            if prev is None or (rerun_survivors and prev["status"] == "survived"):
                jobs.append((f, c))
    selected = {(f, c[0]) for f in files for c in candidates(sources[f])
                if in_ranges(c[3], lines.get(f) if f in lines else None)}
    total = len(selected | set(done))

    # Fresh copies every time: an interrupted run may have left a mutant applied.
    log(f"Preparing {nworkers} worker copies in {workdir} …")
    workdir.mkdir(parents=True, exist_ok=True)
    copies = []
    for w in range(nworkers):
        d = workdir / f"w{w}"
        _copy(project_root, d, ignore)
        copies.append(d)

    def env_for(w):
        e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for k, v in (profile.get("env") or {}).items():
            e[k] = str(v).replace("{worker}", str(w))
        return e

    # Baselines: every test set must pass, unmutated, in every worker.
    sets = sorted({tuple(tests_for(profile, f)) for f, _ in jobs})
    baselines = dict(state.get("baselines") or {})
    for s in sets:
        key = " ".join(s) or "<whole suite>"
        cmd = command(profile, python, list(s))
        results = [None] * nworkers
        with ThreadPoolExecutor(nworkers) as pool:
            futs = {pool.submit(_exec, cmd, copies[w], env_for(w), None): w for w in range(nworkers)}
            for fut, w in futs.items():
                results[w] = fut.result()
        for w, (rc, dt, output) in enumerate(results):
            if rc != 0:
                raise RunError(f"baseline failed in worker {w} for {key} (exit {rc}): every "
                               f"mutant would look killed. Fix the suite or the profile "
                               f"(isolation per worker?). Last output:\n{output[-2000:]}")
        baselines[key] = max(dt for _, dt, _ in results)
        log(f"baseline {key}: {baselines[key]:.1f}s ✓")

    state = {"sha": sha, "tree": tree, "project_root": str(project_root),
             "started_at": state.get("started_at") or datetime.now().isoformat(timespec="seconds"),
             "files": sorted(set(state.get("files", [])) | set(files)),
             "total": total,
             "baselines": baselines, "workers": nworkers}
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    if jobs:
        avg = sum(baselines.get(" ".join(tests_for(profile, f)) or "<whole suite>", 0)
                  for f, _ in jobs) / len(jobs)
        log(f"{len(jobs)} mutants to run with {nworkers} workers — forecast ≤ "
            f"{avg * len(jobs) / nworkers / 60:.1f} min (baseline time per mutant; killed "
            "mutants stop early)")
    else:
        log("Nothing to run: every mutant of the selection already has a result.")

    prio = {f: priority_tests(profile, project_root, f, ignore) for f in files}
    slots = queue.Queue()
    for w in range(nworkers):
        slots.put(w)
    lock = threading.Lock()
    deadline = time.time() + budget_s if budget_s else None
    counts = {"ran": 0, "skipped_budget": 0}

    def one(job):
        f, c = job
        if deadline and time.time() > deadline:
            with lock:
                counts["skipped_budget"] += 1
            return
        w = slots.get()
        try:
            target = copies[w] / f
            try:
                mutated = apply(sources[f], c)
            except Exception as e:  # noqa: BLE001 — an unbuildable mutant is a result
                rec = {"status": "invalid", "secs": 0, "tail": str(e)[:300]}
            else:
                target.write_text(mutated, encoding="utf-8")
                tests = prio[f] + tests_for(profile, f)
                base = baselines.get(" ".join(tests_for(profile, f)) or "<whole suite>", 60)
                timeout = base * float(profile.get("timeout_factor", 3)) \
                    + float(profile.get("timeout_extra_s", 30))
                rc, dt, output = _exec(command(profile, python, tests), copies[w],
                                       env_for(w), timeout)
                target.write_text(sources[f], encoding="utf-8")
                killed_codes = profile.get("killed_exit_codes") or [1]
                status = ("survived" if rc == 0 else "timeout" if rc == "timeout"
                          else "killed" if rc in killed_codes else f"error{rc}")
                rec = {"status": status, "secs": round(dt, 1), "tail": _tail(output)}
            rec = {"file": f, "idx": c[0], "line": c[3], "kind": c[1], "desc": c[4], **rec,
                   "sha": sha[:12], "at": datetime.now().isoformat(timespec="seconds")}
            with lock:
                with results_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                counts["ran"] += 1
                if counts["ran"] % 25 == 0:
                    log(f"  {counts['ran']}/{len(jobs)} …")
        finally:
            slots.put(w)

    with ThreadPoolExecutor(nworkers) as pool:
        list(pool.map(one, jobs))

    if counts["skipped_budget"]:
        log(f"Budget reached: {counts['skipped_budget']} mutants left. Run the same "
            "command again to resume.")
    return {"ran": counts["ran"], "left": counts["skipped_budget"], "total": state["total"],
            "results": str(results_path), "state": str(state_path)}


# ─── status and report ───────────────────────────────────────────────────

def summarize(results: dict) -> dict:
    """{file: {mutants, killed, timeout, survived, error, invalid, score}} + totals."""
    per = {}
    for (f, _), r in results.items():
        row = per.setdefault(f, {"mutants": 0, "killed": 0, "timeout": 0, "survived": 0,
                                 "error": 0, "invalid": 0})
        row["mutants"] += 1
        s = r["status"]
        row[s if s in row else "error"] += 1
    for row in per.values():
        decided = row["killed"] + row["timeout"] + row["survived"]
        row["score"] = round(100 * (row["killed"] + row["timeout"]) / decided) if decided else None
    return per


def status_text(out_dir) -> str:
    out_dir = Path(out_dir)
    state_path = out_dir / "state.json"
    if not state_path.is_file():
        return "No mutation run in this .context/ yet (cp-test --mutate)."
    state = json.loads(state_path.read_text(encoding="utf-8"))
    results = load_results(out_dir / "results.jsonl")
    per = summarize(results)
    done = len(results)
    lines = [f"Mutation run @ {state.get('sha', '')[:12] or '(no git SHA)'} — started "
             f"{state.get('started_at')}",
             f"Progress: {done}/{state.get('total', '?')} mutants with a result"]
    for f in sorted(per):
        r = per[f]
        lines.append(f"- {f}: {r['mutants']} done · {r['killed'] + r['timeout']} detected · "
                     f"{r['survived']} survived · {r['error'] + r['invalid']} error"
                     + (f" · score {r['score']}%" if r["score"] is not None else ""))
    return "\n".join(lines)


def report(out_dir) -> str:
    """Markdown report of `results.jsonl` (per module, worst first, survivors by kind)."""
    out_dir = Path(out_dir)
    state = json.loads((out_dir / "state.json").read_text(encoding="utf-8")) \
        if (out_dir / "state.json").is_file() else {}
    results = load_results(out_dir / "results.jsonl")
    if not results:
        raise RunError("no results yet: run cp-test --mutate first")
    per = summarize(results)
    tot = {k: sum(r[k] for r in per.values()) for k in
           ("mutants", "killed", "timeout", "survived", "error", "invalid")}
    decided = tot["killed"] + tot["timeout"] + tot["survived"]
    score = round(100 * (tot["killed"] + tot["timeout"]) / decided) if decided else 0
    order = sorted(per, key=lambda f: (per[f]["score"] if per[f]["score"] is not None else 101, f))
    md = [f"# Mutation report — @ {state.get('sha', '')[:12] or '(no git SHA)'}", "",
          f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
          f"- Mutants with a result: {len(results)} of {state.get('total', len(results))}",
          f"- **Mutation score: {score}%** ({tot['killed'] + tot['timeout']} detected of "
          f"{decided}; timeouts count as detected: {tot['timeout']})",
          f"- Survivors: {tot['survived']} · errors: {tot['error']} · invalid: {tot['invalid']} "
          "(errors and invalid mutants are left out of the score)", "",
          "## Per module (worst first)", "",
          "| Module | Mutants | Detected | Survived | Errors | Score |",
          "|---|---:|---:|---:|---:|---:|"]
    for f in order:
        r = per[f]
        md.append(f"| `{f}` | {r['mutants']} | {r['killed'] + r['timeout']} | {r['survived']} | "
                  f"{r['error'] + r['invalid']} | "
                  f"{'—' if r['score'] is None else str(r['score']) + '%'} |")
    kinds = {}
    for r in results.values():
        if r["status"] == "survived":
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    md += ["", "## Survivors by mutation kind", ""]
    md += [f"- `{k}`: {n}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])] or ["- none"]
    errors = [r for r in results.values() if r["status"].startswith("error")]
    if errors:
        md += ["", "## Errors (collection/usage — not kills)", ""]
        md += [f"- `{r['file']}`:{r['line']} {r['desc']} — {r['status']}: {r.get('tail', '')}"
               for r in errors[:20]]
    md += ["", "Next: classify every survivor in `triage.md` (references/triage.md), then "
           "`cp-test --triage-check`."]
    return "\n".join(md) + "\n"


# ─── triage table ────────────────────────────────────────────────────────

CLASSES = ("equivalent", "real gap", "dead code", "out of scope")
TRIAGE_HEADER = ["| Module | # | Line | Mutation | Class | Reason / scenario | Action |",
                 "|---|---:|---:|---|---|---|---|"]
_EMPTY = {"", "-", "—", "?", "todo", "tbd"}


def _cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def triage_rows(text: str) -> list:
    """Data rows of the triage table: [{module, idx, line, mutation, class, reason, action}]."""
    rows = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 7 or not cells[1].isdigit():
            continue  # header / separator
        rows.append({"module": cells[0].strip("`"), "idx": int(cells[1]), "line": cells[2],
                     "mutation": cells[3], "class": cells[4].lower(), "reason": cells[5],
                     "action": " | ".join(cells[6:])})
    return rows


def triage_skeleton(out_dir, project="") -> tuple:
    """Write/extend `triage.md` with one empty row per survivor. -> (path, rows added)."""
    out_dir = Path(out_dir)
    results = load_results(out_dir / "results.jsonl")
    path = out_dir / "triage.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    have = {(r["module"], r["idx"]) for r in triage_rows(text)}
    new = [r for (f, i), r in sorted(results.items(), key=lambda kv: (kv[0][0], kv[1]["line"]))
           if r["status"] == "survived" and (f, i) not in have]
    if not text:
        state = out_dir / "state.json"
        sha = json.loads(state.read_text(encoding="utf-8")).get("sha", "")[:12] \
            if state.is_file() else ""
        text = "\n".join([f"# Survivor triage — {project or 'project'} @ {sha or '(no SHA)'}", "",
                          "Class: " + " · ".join(f"`{c}`" for c in CLASSES)
                          + " — rules in cp-test references/triage.md.", "",
                          *TRIAGE_HEADER]) + "\n"
    rows = [f"| `{r['file']}` | {r['idx']} | {r['line']} | {r['desc'].replace('|', '/')} |  |  |  |"
            for r in new]
    if rows:
        text = text.rstrip("\n") + "\n" + "\n".join(rows) + "\n"
    path.write_text(text, encoding="utf-8")
    return path, len(rows)


def triage_check(out_dir) -> tuple:
    """(problems, notes) for `triage.md` against `results.jsonl` (rules 3.3)."""
    out_dir = Path(out_dir)
    path = out_dir / "triage.md"
    if not path.is_file():
        return [f"no {path}: run cp-test --mutation-report first"], []
    results = load_results(out_dir / "results.jsonl")
    rows = triage_rows(path.read_text(encoding="utf-8"))
    by_key = {(r["module"], r["idx"]): r for r in rows}
    problems, notes = [], []
    for (f, i), r in sorted(results.items()):
        if r["status"] == "survived" and (f, i) not in by_key:
            problems.append(f"{f} #{i} (line {r['line']}, {r['desc']}): survivor not triaged")
    open_gaps = 0
    for row in rows:
        ref = f"{row['module']} #{row['idx']}"
        cls, reason, action = row["class"], row["reason"].strip(), row["action"].strip()
        if cls not in CLASSES:
            problems.append(f"{ref}: class {cls!r} — use one of: {', '.join(CLASSES)}")
            continue
        if reason.lower() in _EMPTY or len(reason) < 12:
            what = {"equivalent": "why no test can tell (e.g. 'no caller uses the return — grep')",
                    "real gap": "the scenario: input -> wrong behavior the suite lets pass",
                    "dead code": "why the code is unreachable/unused (grep, callers)",
                    "out of scope": "why it does not matter (log text, message format)"}[cls]
            problems.append(f"{ref}: {cls} needs the reason — {what}")
        if cls == "real gap" and not re.search(r"\b(TK|BUG)-\d+\b", action):
            problems.append(f"{ref}: real gap needs an action with the TK-/BUG- card of the "
                            "test to write (cp-backlog --new task … --source cp-test#mutation:…)")
        if cls == "dead code" and not re.search(r"\bCR\b|CR-\d+", action):
            problems.append(f"{ref}: dead code becomes a simplification CR (cp-ccm), not a test")
        latest = results.get((row["module"], row["idx"]))
        if cls == "real gap" and latest and latest["status"] == "survived":
            open_gaps += 1
    if open_gaps:
        notes.append(f"{open_gaps} real gap(s) still open: after writing each test, re-run the "
                     "survivors (cp-test --mutate --rerun-survivors …); a gap closes only when "
                     "its mutant dies.")
    counts = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    notes.append("Triage: " + " · ".join(f"{c} {n}" for c, n in counts.items()))
    return problems, notes
