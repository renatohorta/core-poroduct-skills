# Debugging: code on disk vs running process + DRF/serializer pitfalls

Pitfalls that emerged while fixing the carousel PNG export bug (Playwright→resvg-py)
and while adding a new field to the message serializer (branch picker + parts).

## 1. Traceback of a lib the ON-DISK code no longer uses = old process in memory

Symptom: the traceback points to a library/module that the current code does not import
(e.g. a Playwright error in `playwright/_impl/_connection.py`, but `png_export.py`
already uses `resvg-py` and does not reference Playwright). The cause is a **Daphne/server
process running with old modules loaded** — the fix was merged but the server was NOT
restarted.

Do NOT redo the fix in the code (it is correct). 3-step diagnosis:

1. **Scan the real imports** of the lib in the current flow, ignoring comments/docs:
   ```python
   real = [l for l in txt.splitlines() if re.search(r"from playwright|import playwright|sync_playwright|async with async_playwright", l)]
   ```
   If it only appears in comments → code OK.
2. **Test the artifact end-to-end via shell** with the real database state
   (e.g. `export_carousel_pngs(pres.state, outdir, len(slides))` generated the 7 PNGs).
   If it works → code correct.
3. **The cause is the outdated process** → restart the server (kill the PID on the port
   and relaunch Daphne). The bug is resolved by restarting, not editing.

Record in the inbox as `[Corrigido]` but move to `processed` — the "fix" is the
finding that the code was already correct + the restart instruction.

## 2. DRF `@action` — `url_path` vs method name

DRF derives the URL from the **method name** (preserves the underscore). The `branch_version` method
generates `.../branch_version/` (underscore), but the frontend/curl may call
`.../branch-version/` (hyphen) → **404**. Fix: force `url_path` in the decorator:

```python
@action(detail=True, methods=["get"], url_path="branch-version")
def branch_version(self, request, uuid=None): ...
```

When creating an `@action`, ALWAYS check which URL the consumer will use and force the
`url_path` to match. See the routes with: `for url in router.urls: print(url.pattern)`.

## 3. Adding a field to the serializer breaks the key-set contract test

When adding a field (e.g. `parts`) to a `ModelSerializer`, tests that assert the
exact set of keys break:

```python
assertEqual(set(body["messages"][0].keys()), {"id","uuid","role","content",...})
# → AssertionError: Items in the first set but not the second: 'parts'
```

This is expected — update the set in the contract test to include the new field.

## 4. New field (self FK / index) requires migration + --create-db

When modeling a new field (e.g. `parent` self FK + `branch_index` in `ChatMessage`):
- `makemigrations <app>` generates the migration; `migrate <app>` applies it to the dev DB
  (pytest creates the schema from scratch, but dev accumulates orphan columns from other branches →
  `DROP COLUMN IF EXISTS` first if needed).
- In tests use `--create-db` (never `--reuse-db` with an old schema → IntegrityError
  or nonexistent field).
