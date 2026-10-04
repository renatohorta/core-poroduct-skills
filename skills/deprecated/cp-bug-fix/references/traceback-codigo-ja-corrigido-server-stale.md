# Traceback of already-fixed code — stale server process

## When to apply
The user pastes a traceback that references a lib/approach that **you think has already been replaced**
(e.g. a Playwright `NotImplementedError` traceback in `_make_subprocess_transport` when the code
has already been migrated to `resvg-py`). Before diagnosing/fixing anything, confirm whether the
traceback matches the CURRENT on-disk code.

## Verification flow (3 steps) — NEVER skip
1. **Grep the disk** — confirm that the file in the working tree no longer imports the old lib.
   Use a regex that catches a real import, not a comment/docstring:
   ```python
   real = [l for l in t.splitlines()
           if re.search(r"from playwright|import playwright|async_playwright|sync_playwright|p\.chromium", l)]
   ```
   Only comments/docs = code already migrated.

2. **Test the real path end-to-end** — run the function in `manage.py shell` (or a subprocess
   with `.venv/Scripts/python.exe`) using the real state persisted in the database:
   ```python
   from presentations.services.png_export import export_carousel_pngs
   pres = Presentation.objects.filter(uuid="...").first()
   pngs = export_carousel_pngs(pres.state, tempdir, len(slides))
   ```
   If the artifacts (PNGs) are generated without the old lib, the code is correct.

3. **If code OK + test passes → stale server process.** The Daphne/runserver that was up
   was started BEFORE the fix was merged and keeps the old module loaded in memory. `netstat`
   may not even show the port (it already crashed). The fix is **restart the server**, not edit code.
   Record the bug as `[Corrigido]` (the fix is already on main) and document that it needs a restart.

## Why this happens
`git merge` updates the disk, but does NOT reload Python modules already imported in a live process.
The user tests against the old process → sees the pre-fix error. The log traceback is evidence of the
old code, not the current code.

## Golden rule
Do not "fix" code that is already correct. Traceback + on-disk code already migrated = stale server,
not a new bug. Verifying first avoids unnecessary edits and empty "fix" commits.
