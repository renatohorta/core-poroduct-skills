# Crew runs in STUB even with Gemini configured — cause: backend restart via subprocess without the Windows env

## Symptom
- The crew is fired, the card shows "Erro na execução" or the run completes DONE but all outputs are `[STUB — crewai ausente] Task 'X' por ...`.
- The Daphne log shows `crew.kickoff stub (crewai ausente) crew=<nome>`.
- **Contradiction:** Gemini IS configured (`is_configured()` returns `True`, `GEMINI_API_KEY` present in the `.env`, and the log shows `LiteLLM completion() model= gemini-2.5-flash; provider = gemini`). The LiteLLM calls that appear are from OTHER parts (Copilot/chat), not the crew.

## Root cause
`run_pipeline_async` decides the stub by:
```python
if not _crewai_available() or not llm_configured:
    reason = "crewai ausente" if not _crewai_available() else "LLM não configurado"
```
`_crewai_available()` does `import crewai` in a try/except. When the backend is restarted via **subprocess** (e.g. `subprocess.Popen([py, "-m", "daphne", ...])`) with a hand-built `env`, the `import crewai` (1.15.5) breaks silently because `chromadb` calls `Path.home()` and `crewai_core` (telemetry) calls `Path(LOCALAPPDATA)`.

Real import errors (without the Windows env vars):
```
RuntimeError: Could not determine home directory.   # chromadb → Path.home()
TypeError: argument should be a str or an os.PathLike object ... not 'NoneType'  # crewai_core → Path(LOCALAPPDATA)
```

## Fix
When relaunching Daphne/ASGI via subprocess on Windows, the `env` MUST include the Windows environment variables that crewai/chromadb require:
```python
env = {
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "PYTHONPATH": os.path.join(back, ".venv", "Lib", "site-packages"),
    "PATH": os.path.join(back, ".venv", "Scripts") + os.pathsep + os.environ.get("PATH", ""),
    "VIRTUAL_ENV": os.path.join(back, ".venv"),
    "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
    "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    "USERPROFILE": os.environ.get("USERPROFILE", r"C:\Users\<user>"),
    "HOMEDRIVE": os.environ.get("HOMEDRIVE", "C:"),
    "HOMEPATH": os.environ.get("HOMEPATH", r"\Users\<user>"),
    "HOME": os.environ.get("HOME", r"C:\Users\<user>"),
    "TEMP": os.environ.get("TEMP", r"C:\Users\<user>\AppData\Local\Temp"),
    "TMP": os.environ.get("TMP", r"C:\Users\<user>\AppData\Local\Temp"),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", r"C:\Users\<user>\AppData\Local"),
    "APPDATA": os.environ.get("APPDATA", r"C:\Users\<user>\AppData\Roaming"),
}
```
Quick verification before starting:
```bash
python -c "import crewai; print(crewai.__version__)"   # with the SAME env as the Popen
```
If it prints the version, the import works and the crew will run for real.

## Important note
This is NOT a bug in the project code. When the backend is started by the normal flow (Windows terminal), these variables exist and crewai imports without error. The problem only appears when the agent restarts the backend via subprocess with an incomplete `env`. Always inherit the process's `os.environ` and only override what is necessary (PYTHONPATH, DJANGO_SETTINGS_MODULE), instead of building a minimal env from scratch.

## Fix confirmation
After relaunching with the full env, fire the crew in a NEW conversation and check:
- The run stays `RUNNING` (not stub, not ERROR) and completes `DONE` in ~1-2 min.
- Outputs have real content (len > 5KB) and the quality gate returns `PASS` — not `[STUB — crewai ausente]`.
