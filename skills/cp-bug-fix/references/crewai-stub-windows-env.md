# Crew runs in STUB ("crewai ausente") even with Gemini configured — Windows

## Symptom
- The crew execution card shows `[STUB — crewai ausente]` as the output of each task.
- The Daphne log shows `crew.kickoff stub (crewai ausente) crew=<nome>`.
- BUT Gemini IS configured: `is_configured()` returns `True`, `GEMINI_API_KEY` present in the `.env`, and the log shows `LiteLLM completion() model= gemini-2.5-flash; provider = gemini` calls (these are from OTHER parts — Copilot/chat — not the crew).

## Root cause
`run_pipeline_async` decides the stub by:
```python
if not _crewai_available() or not llm_configured:
    reason = "crewai ausente" if not _crewai_available() else "LLM não configurado"
```
`_crewai_available()` does `import crewai` in a try/except. If the import fails, it returns `False` → stub. **The Gemini key is irrelevant here** — the problem is the crewai import.

The `import crewai` (1.15.5) pulls in `chromadb` (which calls `Path.home()`) and `crewai_core` (telemetry, which calls `Path(LOCALAPPDATA)`). On Windows, if the process does not have the home variables in the environment, the import breaks:

```
RuntimeError: Could not determine home directory.   # chromadb → Path.home()
TypeError: argument should be a str or an os.PathLike object ... not 'NoneType'  # crewai_core → Path(LOCALAPPDATA)
```

## When it happens
When Daphne is relaunched via `subprocess.Popen` with a hand-built `env` (e.g. only `DJANGO_SETTINGS_MODULE`, `PYTHONPATH`, `SystemRoot`, `WINDIR`) — without `USERPROFILE`/`HOME`/`LOCALAPPDATA`/`APPDATA`/`TEMP`. The Hermes sandbox does not inject these vars into the subprocess.

## Fix
Relaunch Daphne with the full Windows environment:
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

## Verification
Before relaunching, test the import with the SAME env that will be used:
```bash
python -c "import crewai; print('crewai OK', crewai.__version__)"
```
If it prints `crewai OK 1.15.5`, the env is correct. If it gives `RuntimeError: Could not determine home directory` or `TypeError ... not 'NoneType'`, `USERPROFILE`/`LOCALAPPDATA` are missing.

## Note
This is a problem of the restart process via subprocess with an incomplete env — NOT of the project code. When the backend is started by the user's normal shell, these vars exist and crewai imports without error. It is not a production bug.
