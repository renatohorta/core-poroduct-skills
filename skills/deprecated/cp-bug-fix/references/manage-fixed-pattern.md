# manage.py — Hermes + Django project with conflicting lxml + crewai_tools discovery

## Double Problem

### 1. Conflicting lxml

Hermes Agent runs in its own venv (`~/AppData/Local/hermes/hermes-agent/venv/`). When Hermes runs the project's Django commands via `execute_code` or `terminal`, the `sys.path` may load Hermes' `lxml` BEFORE the project's `lxml`. This causes:

```
ImportError: cannot import name 'etree' from 'lxml'
```

### 2. crewai_tools discovery hangs the boot

The `chat/skills/crewai_tools_adapter.py` module tried to automatically discover 63 CrewAI tools at import time. Several tools call `input()` in `__init__` or do network I/O, hanging the process **forever** (not just 5-10s — hours). The `lambda: "N"` that neutralized `input()` was not enough.

## Final Solution (applied in manage.py)

The project's `manage.py` now incorporates two fixes:

1. **Fixes `sys.path`** — removes Hermes' site-packages and inserts the project's at the top
2. **Removes the `crewai_tools_adapter`** — the whole module was deleted, along with `chat/skills/crewai_custom/` and the import in `chat/skills/__init__.py`

```python
"""manage.py — with path fix and without crewai_tools discovery."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Fixes sys.path: project first, Hermes removed
_project_site = os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages")
_hermes_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "AppData", "Local", "hermes", "hermes-agent", "venv", "Lib", "site-packages",
)
if _project_site in sys.path:
    sys.path.remove(_project_site)
sys.path.insert(0, _project_site)
sys.path = [p for p in sys.path if _hermes_site not in p]

from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
```

## Why remove instead of fix?

The `crewai_tools_adapter` was an experiment that never worked in production:
- 63 automatically discovered tools, most with missing optional dependencies
- Several call `input()` in `__init__` (even with `lambda: "N"`, some ignore it)
- Some do network I/O (Firecrawl, etc.) and can time out
- **Copilot does not use these tools** — it uses the native skills (`web_search`, `create_presentation`, `execute_crew`, etc.) registered manually in `chat/skills/`

If a specific CrewAI tool is ever needed, it must be registered **manually** as a skill, not discovered automatically.

## Usage

```bash
.venv\Scripts\python manage.py check    # ~5s (before it hung forever)
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver  # works without --noreload
```
