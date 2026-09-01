# Playwright async on Windows — NotImplementedError in `_make_subprocess_transport`

## Symptom

Exporting PNG of carousel slides via Playwright (`playwright_export.py`) fails with:

```
ERROR    Task exception was never retrieved
File "...\playwright\_impl\_transport.py", line 120, in connect
    self._proc = await asyncio.create_subprocess_exec(...)
File "...\asyncio\base_events.py", line 528, in _make_subprocess_transport
    raise NotImplementedError
NotImplementedError
```

The carousel HTML is generated OK ("Carrossel HTML gerado: ..."), but the PNG
export fails silently (the exception is swallowed in the `except` of `_build_carousel`).

## Root cause

`asyncio.create_subprocess_exec` only works on loops that support subprocess. On
Windows:

- **ProactorEventLoop** → supports subprocess (used by `WindowsProactorEventLoopPolicy`,
  which is the default on Python 3.8+)
- **SelectorEventLoop** → does NOT support subprocess → `NotImplementedError` in
  `_make_subprocess_transport`

Playwright async needs a loop with subprocess support. If the function runs under
`asyncio.run()` in a context where the effective policy is the Selector (e.g. the process inherited
a policy, or the loop was created explicitly), the Chromium launch breaks in the
subprocess.

## Fix

Force the Proactor policy before `asyncio.run()`:

```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def export_carousel_pngs(...):
    ...
    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Falha no export PNG do carrossel: %s", exc)
        return []
```

Put the `set_event_loop_policy` call at the start of the function that runs Playwright
(or in the module), BEFORE the `asyncio.run()`.

## Verification

- `type(asyncio.new_event_loop()).__name__` must be `ProactorEventLoop` (not
  `SelectorEventLoop`).
- Run `python -c "from playwright.async_api import async_playwright; import asyncio; asyncio.run(async_playwright().start().chromium.launch())"`
  must launch Chromium without `NotImplementedError`.

## Additional pitfall (do not confuse with the one above)

If the launch fails with `Executable doesn't exist at ...\ms-playwright\...`, it is NOT the
loop bug — it is the browser not installed: `python -m playwright install chromium`.

## PREFERRED: replace Playwright/Chromium with `resvg-py` (cross-platform, ECS-safe)

To export PNG from SVG (e.g. carousel 1080x1350), **do not use Playwright/Chromium in
production**. It requires downloading ~150MB of Chromium (the download can fail) and the
ECS Fargate Linux container has no Chrome/Edge installed for `channel=`. `resvg-py` is a
Rust SVG renderer (binary wheel, no external native lib, no browser) that
works the same on Windows and ECS Linux.

```python
# presentations/services/png_export.py (replaces playwright_export.py)
import resvg_py
def export_carousel_pngs(state, output_dir, total_slides):
    # render_slide_svg(slide, theme, "4:5", browser=True) -> svg (already 1080x1350)
    png_bytes = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)
```

- Import is `import resvg_py` (not `resvg`), function `svg_to_bytes(svg_string=..., width=..., height=...)`.
- `svg_string` expects `str` (not bytes).
- Reuses the SVG that `svg_renderer.render_slide_svg` already generates (same engine as PPTX/HTML).
- Add `resvg-py>=0.3` to `pyproject.toml`; no need to change the Dockerfile.
- `_build_carousel` (orchestrator) and the `/pngs/` endpoint (views) now call `png_export` with the `state` (not the html_path).

Tests: `tests/presentations/test_png_export.py` (3 tests: available, generates PNG 1080x1350, empty without slides).

## BETTER ALTERNATIVE — replace Playwright with `resvg-py` (recommended for prod)

If the user cannot install Chromium (`playwright install` fails on the ~150MB
download) OR the service is going to production on **ECS Fargate Linux** (where there is no
Chrome/Edge and Chromium must be downloaded in the container), abandon Playwright and
convert the **SVG the project already generates** to PNG via **`resvg-py`**:

- Rust SVG renderer, **binary wheel** — no browser, no external native lib
  (unlike `cairosvg`/`reportlab.renderPM` which require the C `libcairo`, absent on
  Windows and annoying on ECS). Works the same in dev (Windows) and production (Linux).
- Usage: `resvg_py.svg_to_bytes(svg_string=str, width=1080, height=1350)` → PNG bytes.
  The import module is **`resvg_py`** (not `resvg`); the function is **`svg_to_bytes`**
  (not `render`). `svg_string` expects `str`, not bytes.
- Prerequisite: the slides are already rendered as canonical 1080x1350 SVG
  (`svg_renderer.render_slide_svg(..., "4:5")`) — the PNG reflects the same design as the
  HTML/PPTX without needing a browser to "photograph" the HTML.
- Dependency: add `resvg-py>=0.3` to `pyproject.toml` (no need to change the
  Dockerfile — the wheel installs via `uv sync`).
- Example export module: `presentations/services/png_export.py` (accepts the
  `state` dict, not the HTML path, since the PNG comes from each slide's SVG).

**Sanity test:** `resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)`
must return PNG bytes. Verify dimensions with `PIL.Image`; use
`with Image.open(p) as img:` (close the image or the `TemporaryDirectory` fails with
`PermissionError` on Windows).

**`channel="chrome"` as a quick option (dev):** `p.chromium.launch(channel="chrome")`
uses the Google Chrome/Edge already installed on the system (without downloading Chromium). Good for quick
dev, BUT does not work on ECS (no browser installed). If prod is Linux, prefer
`resvg-py`.

## PRODUCTION alternative: resvg-py (preferred when there is a container/ECS)

When the service runs in production (e.g. AWS ECS Fargate, Linux) and the PNG export of a
carousel/slide will run there, **do not use Playwright+Chromium** — there is no Chrome/Edge in the
container and downloading Chromium (~150MB) fails or bloats the image. The open-source
alternative is **`resvg-py`** (Rust SVG renderer, binary wheel, no browser and
no external native lib). Works on Windows dev AND on Linux production, without changing the
Dockerfile.

- Add `resvg-py>=0.3` to `pyproject.toml` (not to the tools extra — it is a dependency of the
  PNG export service).
- Installation in a `uv`-managed venv: **there is no `pip`** (`No module named pip`) — use
  `uv pip install resvg-py`, or add it to pyproject and `uv sync`.
- Import: `import resvg_py` (the module name is `resvg_py`, NOT `resvg`).
- Conversion: `resvg_py.svg_to_bytes(svg_string=<str>, width=1080, height=1350)` —
  `svg_string` expects **`str`**, not bytes (error: `'bytes' object is not an instance of 'str'`).
  Write the return with `Path(...).write_bytes(png_bytes)`.
- Reuses the canonical SVG the project already generates (e.g. `render_slide_svg(slide, theme, "4:5")`,
  which already comes out at 1080×1350) — no need to "photograph" the HTML.

**Why the other alternatives fail (tested):**
- `cairosvg` → needs the native C lib `libcairo` (`OSError: no library called "cairo-2"`) — does not run pure on Windows.
- `svglib` + `reportlab` `renderPM` → also requires the native `rlPyCairo` backend (`RenderPMError: cannot import desired renderPM backend rlPyCairo`).
- `Pillow` → does NOT render SVG (`UnidentifiedImageError`).

Only `resvg-py` (Rust binary) works without a system dependency.

**Function signature:** `svg_to_bytes(svg_string=None, svg_path=None, width=None, height=None, ...)` — if you pass `svg_path`, you can pass bytes; if you pass `svg_string`, it must be `str`.

## Key diagnosis: Playwright traceback at runtime ≠ code still uses Playwright

The most misleading error in this flow: the **runtime log keeps showing the Playwright
traceback** (`playwright/_impl/_transport.py` → `NotImplementedError`) even after
you have already switched the code to `resvg-py`. Before going back to editing code,
check whether the server is running with **old code in memory**.

Cause: the resvg fix was already merged into main, but the **Daphne process was not restarted**
after the merge — the old module (`playwright_export.py`) stayed loaded in the process
memory. `manage.py runserver`/Daphne **does NOT auto-reload** these changes.

Diagnostic flow (in order):
1. **Check the code on disk** — real grep (not comments) for `from playwright`,
   `async_playwright`, `sync_playwright`, `p.chromium`, `async with async_playwright`.
   If there are only mentions in comments/docstrings, the code has already migrated.
2. **Check if the server is running** — `netstat -ano | findstr :8000`. If there is no
   process listening, the traceback was from an old execution.
3. **Test the export directly via shell** with the real object state (e.g. get the
   `Presentation` by uuid and call `export_carousel_pngs(state, dir, n)`). If it generates the
   PNGs without error, the code is correct and the problem is the old process.
4. **Restart Daphne** — kill the process on port 8000 (`taskkill /PID <pid> /F`) and
   relaunch with the full Windows env (USERPROFILE/HOME/LOCALAPPDATA/APPDATA — see
   `crewai-stub-on-subprocess-restart.md`). Then re-test the download.

Rule: **if the code on disk is correct and the shell test generates the PNGs, do NOT edit
code anymore — restart the server.** The Playwright runtime traceback after the migration is
almost always the old process in memory, not a residual code path.

## Complete migration: it is NOT just changing the function — the signature and ALL call-sites change

When replacing Playwright with resvg-py, the new `export_carousel_pngs` module changes the
signature and **there is more than one call-site**. The migration in `crewbotics-back`:
- New `presentations/services/png_export.py` with signature `export_carousel_pngs(state: dict, output_dir: str, total_slides: int)` — needs the `state` (to render the SVG per slide), NOT the `html_path`.
- **`playwright_export.py` deleted** (replaced).
- **`orchestrator.py`** (`_build_carousel`): now calls `export_carousel_pngs(state, png_dir, len(slides))`.
- **`presentations/views.py`** (endpoint `GET .../pngs/` → ZIP): BEFORE called `export_carousel_pngs(carousel_path, png_dir, len(slides))` with the HTML path; AFTER `export_carousel_pngs(pres.state, png_dir, len(slides))` with the presentation's `state`.

Migration pitfalls:
- **Always look for ALL call-sites** before changing the signature — `grep` for `export_carousel_pngs` and `playwright_export` across the whole repo (not just the file). Leaving an old call-site (with positional `html_path`) breaks with `TypeError`.
- Check for stale imports after deleting `playwright_export.py`: no `from .playwright_export import ...` should remain.
- `resvg-py` goes in the **main dependencies** of `pyproject.toml` (not in an extra) — the PNG export service runs in production.

## TEST pitfall on Windows: Pillow lazy-open blocks the TemporaryDirectory cleanup

When testing `export_carousel_pngs` (which writes PNGs) with `tempfile.TemporaryDirectory()`, the
Pillow `Image.open(p)` opens the file **lazily** — the handle stays open until the image is
discarded. On Windows, `TemporaryDirectory.cleanup()` fails to delete the PNG still in use:

```
PermissionError: [WinError 32] The process cannot access the file because it is
being used by another process: '...\\tmpXXX\\slide_2.png'
```

Fix in the test: use Pillow's context manager to close the handle before cleanup:

```python
with tempfile.TemporaryDirectory() as tmp:
    paths = export_carousel_pngs(SAMPLE, tmp, 2)
    for p in paths:
        with open(p, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"
        from PIL import Image
        with Image.open(p) as img:   # closes the handle
            assert img.size == (1080, 1350)
```

Without the `with Image.open(...)` the test fails only at teardown (not at the assert), which is confusing.
The same applies to any test that writes files with Pillow inside a TemporaryDirectory.
