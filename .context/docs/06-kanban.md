# Kanban / Esteira — Core Product Skills

> Disciplina: Esteira de execução (`cp-agilista`). Atualizado em 2026-08-18.

## Status

- [x] Backlog inicial registrado
- Fonte de verdade do kanban: **local** (`.context/inbox/`). Trello, se conectado,
  é apenas uma visão espelhada.

## Fluxo

```
.context/inbox/{iniciativas,tasks,bugs,debitos-tecnicos}/
        │  cp-agilista (polling)
        ▼
   cp-orquestrador  ──► skill do modo adequado ──► .context/docs/<disciplina>.md
        │
        └─► dúvida/impedimento ──► volta ao inbox aguardando resposta humana
```

## Board

### 🔵 Backlog

| ID | Item | Tipo | Prioridade |
|----|------|------|-----------|
| DT-05 | Declarar dependências (`requirements.txt`) | Débito técnico | Alta |
| DT-02 | Criar suíte de smoke tests das skills | Débito técnico | Alta |
| DT-03 | Validar contrato `invoke` × `argparse` automaticamente | Débito técnico | Alta |
| DT-06 | Adicionar CI (dry-run do install + smoke tests) | Débito técnico | Média |
| DT-04 | Autenticação no `claude_proxy.py` | Segurança | Média |
| DOC-01 | Alinhar porta do proxy entre README e código | Doc/Bug | Baixa |

**Sequência recomendada**: DT-05 → DT-02 / DT-03 → DT-06 → DT-04 → DOC-01.
DT-07 (já corrigido) desbloqueou DT-02: com `--help` funcionando em todas as
skills, o smoke test agora é escrevível.

### 🟡 Em andamento

_(vazio)_

### 🟢 Concluído

| ID | Item | Data |
|----|------|------|
| BUG-03 | Quality gate passa a reprovar por exit code ≠ 0 | 2026-08-18 |
| BUG-04 | Quality gate casa keywords por palavra inteira | 2026-08-18 |
| BUG-05 | `cp-goal-loop` deriva passo único do `--goal` | 2026-08-18 |
| DT-07 | `crewai` com import guardado nas 12 skills — `--help` sempre funciona | 2026-08-18 |
| DT-08 | `require_llm()` falha cedo com mensagem acionável | 2026-08-18 |
| DT-01 | `setup_console()` força UTF-8 no stdout/stderr | 2026-08-18 |
| INIT-01 | Inicialização da documentação em `.context/` | 2026-08-18 |

## Convenções

- Um arquivo `.md` por item, dentro da pasta de inbox correspondente.
- Item concluído: marcar `[Concluído]` (feature) ou `[Corrigido]` (bug) no título e
  mover com `git mv` para a pasta de processados, preservando o histórico.
- Prioridade segue MoSCoW, alinhada a `.context/docs/01-requisitos.md`.
