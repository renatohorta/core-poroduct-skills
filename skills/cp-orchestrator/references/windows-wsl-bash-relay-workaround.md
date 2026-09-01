# Windows: WSL bash relay fails intermittently — use execute_code

## Symptom
On this Windows host, the `terminal` and `write_file`/`patch` tools sometimes
fail with:
```
<3>WSL (NN - Relay) ERROR: CreateProcessCommon:735: execvpe(/bin/bash) failed: No such file or directory
```
This is Hermes' relay trying to start `/bin/bash` via WSL and not finding the
binary — it is NOT an error in your command nor in the project. It's intermittent: the same
command can work in one call and fail in the next.

## Reliable workaround
Use `execute_code` with pure Python (subprocess / open) — it doesn't go through the bash relay:

- **Run git / pytest / commands:**
  ```python
  import os, subprocess
  env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
  back = r"C:\Users\renat\PycharmProjects\crewbotics-back"
  py = os.path.join(back, ".venv", "Scripts", "python.exe")
  r = subprocess.run([py, "-m", "pytest", "tests/chat/test_agui.py", "-q"],
                     capture_output=True, text=True, env=env, cwd=back, timeout=600)
  print(r.returncode, r.stdout[-3000:], r.stderr[-3000:])
  ```
  For git, define a helper `def git(*args): subprocess.run(["git"]+list(args), ...)`.

- **Write/read a file:** use `open(p, "w", encoding="utf-8")` / `open(p, encoding="utf-8").read()`
  instead of `write_file`/`read_file` when the relay is failing.

## Read pitfall
`read_file` can return "File unchanged since last read" (dedup) even when
you never read the file in this session — if you need the real content, read it via
`open(p, encoding="utf-8").read()` in `execute_code`.

## Note
Don't treat this as a permanent "terminal doesn't work" — it's an intermittent relay.
Try `terminal` first; if it fails with the WSL error, fall back to `execute_code`.

## Pitfall: `git push` hangs on Git Credential Manager (headless)

On this Windows host, `git push` can **hang indefinitely** (300s timeout in
`execute_code`) because the credential helper is `manager` (Git Credential Manager), which
tries to open an authentication dialog that never completes in a headless environment. Symptoms:
- `git push` never returns; `execute_code` blows the 300s timeout even with
  `subprocess.run(..., timeout=45)` — the wrapper stays stuck.
- Multiple `git.exe` / `git-credential-manager.exe` processes accumulate in `tasklist`.

Diagnosis and workaround:

1. **Confirm it's the GCM:** run with the helper disabled to see the real error fast:
   ```python
   env["GIT_TERMINAL_PROMPT"] = "0"
   subprocess.run(["git", "-c", "credential.helper=", "push", "origin", "main"], ...)
   ```
   If it fails immediately with `Authentication failed` / `Repository not found`, it's the GCM
   not providing a credential — not a network or branch problem.
2. **Run the push with forced kill** (don't let the wrapper hang):
   ```python
   p = subprocess.Popen(["git", "push", "origin", "main"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=env, cwd=back, start_new_session=True, text=True)
   try:
       out, err = p.communicate(timeout=45)
   except subprocess.TimeoutExpired:
       os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # kills the whole group
       out, err = p.communicate()
   ```
   `start_new_session=True` + `os.killpg` is what unlocks it — without it `communicate`
   stays stuck and `execute_code` blows the 300s timeout.
3. **Clean up accumulated processes:** `taskkill /F /IM git.exe`, `git-remote-https.exe`,
   `git-credential-manager.exe` (via `subprocess.run(["taskkill","/F","/IM",img])`).
4. **The hang is transient:** the same push can work on a later attempt
   (the GCM sometimes completes). If it persists, the reliable path is the user running
   `git push origin main` in their terminal, where the GCM opens the dialog normally.

Don't treat it as a permanent "push doesn't work" — it's the headless GCM. The retry pattern with
forced kill + `-c credential.helper=` for diagnosis is the durable lesson.
