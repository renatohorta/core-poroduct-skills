# DT-06 — Sem CI

**Tipo**: Débito técnico · **Prioridade**: Média · **Aberto em**: 2026-08-18
**Depende de**: DT-02, DT-05

## Contexto

Não há workflow de CI. Nada valida um push antes de as skills serem propagadas
para os agentes por `install.sh`.

## Proposta

Workflow (GitHub Actions) a cada push/PR:

1. `bash -n scripts/install.sh` (sintaxe) e `./scripts/install.sh --dry-run`
   com `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` apontando para tempdir.
2. `pytest` (smoke + contrato, DT-02/DT-03).
3. Verificação de higiene: nenhum path absoluto de máquina (`C:\Users\`, `/home/`)
   e nenhum padrão de chave de API nos arquivos versionados.

## Critério de aceite

- PR com skill quebrada é bloqueado pelo CI.
