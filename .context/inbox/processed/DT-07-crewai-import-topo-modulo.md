# DT-07 — `crewai` importado no topo do módulo impede até `--help` [Corrigido]

**Tipo**: Débito técnico · **Prioridade**: Alta · **Aberto em**: 2026-08-18
**Verificado empiricamente**: sim (12/15 skills falham)

## Sintoma

Sem `crewai` instalado, **12 das 15 skills** morrem no import — nem `--help`
funciona:

```
ModuleNotFoundError: No module named 'crewai'
  File ".../cp-requisitos/scripts/run.py", line 19, in <module>
    from crewai import Agent, Task, Crew, Process
```

Afeta: `cp-arquitetura`, `cp-bug-fix`, `cp-competitive-analysis`, `cp-devops`,
`cp-documentacao`, `cp-goal-loop`, `cp-implementacao`, `cp-manutencao`,
`cp-qualidade`, `cp-requisitos`, `cp-seguranca`, `cp-testes`.

Não afeta: `cp-agilista` e `cp-inicializador-doc` (não usam LLM) e
`cp-orquestrador` (já usa import tardio dentro das funções — ver "Referência").

## Impacto

- Impossível inspecionar o contrato CLI de uma skill sem instalar a lib pesada.
- Impossível escrever smoke test de `--help`/`--dry-run` (bloqueia DT-02/DT-03).
- Mensagem de erro é um traceback, não uma instrução acionável.

## Referência — o padrão correto já existe no repositório

`cp-orquestrador/scripts/run.py` faz import tardio com mensagem clara:

```python
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    print("❌ crewai não instalado. Execute: pip install crewai")
    sys.exit(1)
```

## Correção proposta

Substituir o import de topo pelo mesmo padrão, movendo `from crewai import ...`
para dentro de `get_agent()`/`build_crew()`, ou usar guarda no topo:

```python
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = Task = Crew = Process = None
```

...e checar `CREWAI_AVAILABLE` só no ponto de execução real (`kickoff`), deixando
`--help` e `--dry-run` funcionarem sempre.

## Critério de aceite

- `python skills/cp-<qualquer>/scripts/run.py --help` retorna 0 em venv limpo.
- Executar sem `crewai` produz mensagem acionável e exit code ≠ 0.


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
