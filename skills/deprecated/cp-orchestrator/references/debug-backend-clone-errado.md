# Diagnosis: code correct locally but doesn't work in the app

Real pitfall (11/08/2026, card carousel in crewbotics). I implemented automatic card
detection (`parse_card_list`) in the `instagram_carousel` skill, validated with
passing tests and the real prompt — but the app on port 8080 kept generating the OLD
carousel (without detection). Debugging the skill was useless: the problem was never
the code.

## Root cause: the backend runs from ANOTHER repo clone

The server on port 8000 was not running from the directory where I was working. There were
TWO clones of `crewbotics-back`:
- `C:\Users\renat\Documents\Professional\Crewbotics\crewbotics-back` — where the
  dev work (branches, features) actually happens.
- `C:\Users\renat\PycharmProjects\crewbotics-back` — old clone, which the
  `scripts/all_dev.ps1` used as `$backDir`.

The backend on :8000 started from PycharmProjects (code without the feature), which is why the
old behavior persisted even with the new code ready in the other clone.

## Rule

**Before debugging a skill that "doesn't take effect" in the app, confirm FROM WHICH
directory the process on the port is running.** Check the listener's PID + CommandLine, don't
assume it's the current working repo.

## How to verify (Windows, via execute_code)

`netstat` via git-bash/MSYS sometimes returns empty (unstable); use PowerShell.

```python
import subprocess, os
PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
ps = '''
$ErrorActionPreference='SilentlyContinue'
foreach ($port in 8000,8080) {
  $c = Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -First 1
  if ($c) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"
    $pp = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
    Write-Output ("PORT {0} PID={1} START={2}" -f $port, $c.OwningProcess, $proc.CreationDate)
    Write-Output ("  CMD=" + $proc.CommandLine)
    Write-Output ("  PARENT=" + $pp.CommandLine)
  } else { Write-Output "no listener on $port" }
}
'''
r = subprocess.run([PS,"-NoProfile","-Command",ps], capture_output=True, text=True, timeout=60)
print(r.stdout)
```

The python `CommandLine` reveals the directory (e.g.: `...\PycharmProjects\crewbotics-back\.venv\Scripts\python.exe -m daphne ...`). Compare with the repo where the correct code is.

Also confirm whether the skill file in the process's directory has the new code:
```python
import os
for p in [r"...\cloneA\chat\skills\instagram_carousel_skill.py",
          r"...\cloneB\chat\skills\instagram_carousel_skill.py"]:
    src = open(p, encoding="utf-8", errors="replace").read()
    print(os.path.basename(os.path.dirname(os.path.dirname(p))), "parse_card_list" in src)
```

## Fix

1. Adjust `all_dev.ps1` so `$backDir` points to the correct working clone
   (keeping `$frontDir` in the canonical front clone — it can be another directory).
2. The script already kills processes on ports 8000/8080 at the start — running it again brings down
   the old process automatically.

## Note: feature on an unmerged branch doesn't exist on main

If the change is on a `feature/...` branch that hasn't been merged into main yet, a
backend running from main won't have it. Check `git branch --contains <commit>` to
confirm where the commit exists before assuming the code should be active.
`local main` vs `origin/main` can diverge — `git rev-parse main origin/main`.
