# Inventário CLI das skills cp-* (contrato de acionamento)

Ao adicionar uma skill nova ao orquestrador ou depurar por que uma fase não é
acionada, confira o contrato CLI real da skill em `scripts/run.py` — NÃO assuma
que toda skill aceita `--output` nem que o briefing entra como argumento
posicional. Cada skill tem interface própria.

## Como o orquestrador aciona (metadado `invoke` no `CREWS`)

Cada crew carrega `invoke` com dois campos:
- `briefing_arg`: `positional` (arg posicional), `goal` (`--goal`), ou `input` (`--input`)
- `output`: `True` se a skill aceita `--output`, `False` caso contrário

O `_build_cli_args` lê esse metadado. Se uma skill nova for adicionada sem o
metadado, o default é `{"briefing_arg": "input", "output": True}` — que quebra
skills que não aceitam `--output` (argparse rejeita flag desconhecido).

## Contrato CLI por skill (verificado 2026-08)

### Fases do pipeline (todas aceitam `--input` e `--output`)
| skill | briefing | output |
|-------|----------|--------|
| cp-requisitos | posicional / `--input` | SIM |
| cp-arquitetura | posicional / `--input` | SIM |
| cp-implementacao | posicional / `--input` | SIM (+ `--type`) |
| cp-testes | posicional / `--input` | SIM (+ `--source`, `--acceptance`, `--mode`) |
| cp-seguranca | posicional / `--input` | SIM (+ `--mode`) |
| cp-devops | posicional / `--input` | SIM (+ `--mode`) |
| cp-documentacao | posicional / `--input` | SIM (+ `--mode`) |
| cp-qualidade | posicional / `--input` | SIM (+ `--mode`) |

### Skills complementares (modos dedicados)
| skill | briefing | output | flags extras |
|-------|----------|--------|--------------|
| cp-bug-fix | posicional (`bug_description`) | **NÃO** | `--type backend/frontend` |
| cp-competitive-analysis | posicional (`context`) / `--input` | SIM | — |
| cp-goal-loop | **`--goal` (obrigatório)** | **NÃO** | `--steps`, `--steps-file`, `--max-attempts`, `--max-time` |
| cp-manutencao | posicional (`descricao`) / `--input` | SIM | `--mode bug-fix/refactor/improvement/full` |

> **`cp-full-dev` foi fundido no orquestrador (eliminado).** O pipeline NEXUS (7 fases,
> 39 agentes) agora roda nativamente via `NexusExecutor` no `run.py` do orquestrador.
> O modo `full-dev` executa o NEXUS em memória (detecção automática full/sprint/micro,
> quality gates por fase) — não há mais `scripts/run.py` externo para chamar.

## Pitfalls
- `cp-goal-loop` NÃO tem argumento posicional — o briefing entra só via `--goal`.
  Passar o briefing como posicional faz o argparse falhar.
- `cp-bug-fix` e `cp-goal-loop` NÃO aceitam `--output`. Passar
  esse flag faz o argparse rejeitar (argumento desconhecido).
- O NEXUS (`full-dev`) é nativo: não use `SKILL_PATHS`/`CREWS` para ele — o
  `main()` desvia para `NexusExecutor` quando `mode == "full-dev"`.

## Como verificar o contrato de uma skill nova
```python
import re
from pathlib import Path
content = Path(".../cp-X/scripts/run.py").read_text(encoding="utf-8")
print("output:", "--output" in content)
print("input:", "--input" in content)
m = re.search(r'add_argument\(\s*"([a-z_]+)"', content)  # arg posicional
print("posicional:", m.group(1) if m else None)
```
