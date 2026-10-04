# Development pipeline execution (crewbotics-back) — real pitfalls

Durable lessons from real pipeline executions (INI-80, 11/08/2026). Complements
`roadmap-inbox-manutencao.md` (real state vs roadmap) and
`windows-wsl-bash-relay-workaround.md` (bash relay).

## Running tests: use `uv run pytest`, NOT `.venv`

The project uses `uv` and has **no own `.venv`** in the repo. `uv run` creates the venv on
demand (and syncs deps, updating `uv.lock`). Don't look for `python.exe` in
`.venv/` — it doesn't exist. Pattern:

```python
import os, subprocess
base = r"C:\Users\renat\Documents\Professional\Crewbotics\crewbotics-back"
env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
r = subprocess.run(["uv", "run", "pytest", "tests/chat/test_x.py", "-q", "-p", "no:cacheprovider"],
                   capture_output=True, text=True, env=env, cwd=base, timeout=600)
print(r.returncode, r.stdout[-3000:], r.stderr[-2000:])
```

- `uv run` can be slow the 1st time (installs deps) — use a generous timeout (600s).
- `uv run` updates `uv.lock` if deps were outdated. That's legitimate to
  commit (e.g.: `resvg-py` was already imported but missing from the lock). Check the diff
  before including it.

## Tests that touch the database fail without `.env`/Postgres

Tests that import Django models (e.g.: `test_instagram_carousel_skill.py`) fail
with `OperationalError: password authentication failed for user "postgres"` when
there is no `.env`/accessible database. This is **pre-existing and unrelated to your
change** — don't try to "fix" the code. Tests that DON'T touch the database (e.g.: a pure
PIL executor) pass. When reporting, clearly distinguish: "my tests pass;
X's fail due to Postgres connection (pre-existing)".

## Commit: ALWAYS check `git status --short` before committing

Real pitfall: I staged only some files, committed, and 3 modified files
(`canvas_design_crew.py`, `presentation_skill.py`, `tasks.md`) were left out of the
commit — `git commit` only picks up what's staged. The commit "passed" but the work
was orphaned.

Safe pattern:
1. `git add <files>` (list ALL the change's files explicitly).
2. `git status --short` → confirm ALL intended files are staged
   (`A`/`M` column in the 1st position).
3. Only then `git commit`.
4. After the commit, `git status --short` again → should be clean (or only what
   was intentionally left out).

If a commit came out incomplete, make a follow-up commit with the remaining files
— don't rewrite history.

## PIL + `tempfile.TemporaryDirectory` on Windows: close the image

A test that opens a PNG with `Image.open(p)` and then uses `TemporaryDirectory` fails on
Windows with `PermissionError: [WinError 32] ... being used by another process` —
`Image.open` holds the file handle and prevents the tempdir's `rmtree`.

Fix: use the context manager `with Image.open(p) as im:` (closes the handle when leaving
the block). Always close PIL images before deleting the directory that contains them.

## `false` vs `False` in a Python parameter dict

When writing a JSON Schema dict in Python (e.g.: a skill's `parameters`), use
`True`/`False` (Python), NOT `true`/`false` (JSON/JS). `"default": false` raises
`NameError: name 'false' is not defined` on module import. `ast.parse` catches the
syntax but does NOT catch this runtime error — run the test/import to confirm.
