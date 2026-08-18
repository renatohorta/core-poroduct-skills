# DT-01 — UnicodeEncodeError no console Windows (cp1252) [Corrigido]

**Tipo**: Bug · **Severidade**: Média · **Aberto em**: 2026-08-18

## Sintoma

`skills/cp-orquestrador/scripts/run.py` aborta ao imprimir o banner:

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2-65
  File ".../encodings/cp1252.py", line 19, in encode
```

## Reprodução

```bash
python skills/cp-orquestrador/scripts/run.py "x" --mode full --dry-run
```

(sem `PYTHONUTF8=1`, em console Windows com codepage cp1252)

## Causa

O banner e os emojis de status usam caracteres fora do cp1252; o `stdout` padrão do
Python no Windows não está em UTF-8. Afeta qualquer skill que imprima box-drawing
ou emoji — não só o orquestrador.

## Workaround atual

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python .../run.py ...
```

## Correção proposta

No topo de cada `run.py` (ou em `_shared`), reconfigurar o stdout antes de imprimir:

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

`errors="replace"` garante que nenhum ambiente exótico derrube a execução.

## Critério de aceite

- `python skills/cp-orquestrador/scripts/run.py "x" --mode full --dry-run` retorna 0
  em console Windows **sem** env vars de encoding.


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
