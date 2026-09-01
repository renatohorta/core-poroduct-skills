# Diagnosis: traceback of a lib the on-disk code no longer uses (process with old code)

## Pattern
The user pastes a traceback pointing to a library (e.g. Playwright `_connection.py` /
`_make_subprocess_transport`), but the on-disk code **has already been migrated** to another
(e.g. `resvg-py`). The cause is NOT wrong code — it is the server (Daphne/runserver) running
with an old module loaded in memory since before the fix was merged.

**Do NOT re-apply a fix that is already on main.** Diagnose the disk↔process divergence
before editing anything.

## How to confirm (before touching the code)
1. **Scan the flow for REAL use of the old lib** — not just comments/docs:
   ```python
   import re
   for rel in [files of the path]:
       t = open(rel, encoding="utf-8").read()
       real = [l for l in t.splitlines()
               if re.search(r"from playwright|sync_playwright|async_playwright|\.chromium", l)]
       # if it only appears in a docstring/comment → code ok
   ```
2. **Run the production function DIRECTLY** in a shell with the user's real state
   (`manage.py shell -c "..."` or a script): if it works, the code is correct and only
   the process needs to restart. E.g. `export_carousel_pngs(pres.state, outdir, len(slides))`
   generated the 7 PNGs of the real state — code confirmed good.
3. **Check the process**: `netstat -ano | findstr :8000`; distinguish WSGI vs ASGI by the
   `Server:` header of the response. Restart Daphne with the full Windows env
   (USERPROFILE/HOME/LOCALAPPDATA/APPDATA/TEMP) to load the new code.

## Classic symptom
The user reports a bug in a flow that YOU already fixed and merged; the traceback points to
the old code. Diagnose the disk↔process divergence BEFORE re-fixing.

---

# Resolving outdated docs branches — extract value, do NOT merge directly

## Pattern
A docs branch (e.g. `docs/consolidar-documentacao`) was created days ago and main
has evolved. A direct merge can **REMOVE content that main gained later** (e.g. the branch
deletes `knowledge_folder`, ActivityLog/password-reset sections added later).

## Checks before merging
- `git diff main <branch> -- <arquivo>` and count additions vs removals — a removal much larger
  than the addition in a reference doc = likely loss.
- Check whether the file the branch deletes (e.g. `00-vision.md` 35KB with checklist/contract)
  has the content in ANOTHER doc. If not, do NOT let the branch delete it.
- `git merge-base main <branch>` and compare the age — an old merge-base + many new
  commits on main = high risk of conflict/loss.

## Preferred action
1. Extract only the value (e.g. merge `01-visao-geral.md` + `01-visao-negocio.md` into a
   `01-visao.md` manually, preserving the complete `00-vision.md`).
2. Commit on main.
3. `git branch -D` the branches (before, `git ls-remote --heads origin` to confirm whether
   they exist on the remote — if not, only delete locally).
