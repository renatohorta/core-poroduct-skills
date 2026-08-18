# manage.py — Hermes + Projeto Django com lxml conflitante + crewai_tools discovery

## Problema Duplo

### 1. lxml conflitante

O Hermes Agent roda em seu próprio venv (`~/AppData/Local/hermes/hermes-agent/venv/`). Quando o Hermes executa comandos Django do projeto via `execute_code` ou `terminal`, o `sys.path` pode carregar o `lxml` do Hermes ANTES do `lxml` do projeto. Isso causa:

```
ImportError: cannot import name 'etree' from 'lxml'
```

### 2. crewai_tools discovery trava o boot

O módulo `chat/skills/crewai_tools_adapter.py` tentava descobrir automaticamente 63 tools do CrewAI no momento do import. Várias tools chamam `input()` no `__init__` ou fazem I/O de rede, travando o processo **para sempre** (não apenas 5-10s — horas). O `lambda: "N"` que neutralizava `input()` não era suficiente.

## Solução Final (aplicada no manage.py)

O `manage.py` do projeto agora incorpora duas correções:

1. **Corrige `sys.path`** — remove o site-packages do Hermes e insere o do projeto no topo
2. **Remove o `crewai_tools_adapter`** — o módulo inteiro foi deletado, junto com `chat/skills/crewai_custom/` e o import em `chat/skills/__init__.py`

```python
"""manage.py — com path fix e sem crewai_tools discovery."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Corrige sys.path: projeto primeiro, Hermes removido
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

## Por que remover em vez de consertar?

O `crewai_tools_adapter` foi um experimento que nunca funcionou em produção:
- 63 tools descobertas automaticamente, a maioria com dependências opcionais ausentes
- Várias chamam `input()` no `__init__` (mesmo com `lambda: "N"`, algumas ignoram)
- Algumas fazem I/O de rede (Firecrawl, etc.) e podem timeout
- **O Copilot não usa essas tools** — ele usa as skills nativas (`web_search`, `create_presentation`, `execute_crew`, etc.) registradas manualmente em `chat/skills/`

Se um dia for necessário usar uma tool específica do CrewAI, ela deve ser registrada **manualmente** como skill, não descoberta automaticamente.

## Uso

```bash
.venv\Scripts\python manage.py check    # ~5s (antes travava para sempre)
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver  # funciona sem --noreload
```
