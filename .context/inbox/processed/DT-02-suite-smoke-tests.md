# DT-02 — Sem suíte de testes automatizados [Concluido]

**Tipo**: Débito técnico · **Prioridade**: Alta · **Aberto em**: 2026-08-18

## Contexto

O repositório tem 15 skills e 15 scripts `run.py`, e **zero testes**. Toda
validação é manual (`--dry-run` ad hoc), então regressões de contrato CLI só
aparecem quando o orquestrador quebra em produção.

## Proposta

`pytest` parametrizado sobre `skills/*/scripts/run.py`:

1. `--help` retorna exit 0 para toda skill.
2. `--dry-run` (com o briefing no formato correto por skill) retorna exit 0.
3. `install.sh --dry-run` lista as 15 skills + `_shared`.
4. `_shared/llm.py`: ordem de resolução (env do agente > `.env` > detecção por
   chave > default) com `monkeypatch`.

Nenhum teste deve chamar LLM real — caro e não-determinístico.

## Critério de aceite

- `pytest` roda em < 60s sem credencial de LLM configurada.
- Uma skill com contrato CLI quebrado faz o teste falhar.


---

## Resolucao

**Concluido em 2026-08-18.** Verificado com a suite (`pytest`, 158 testes, sem
credencial de LLM). Ver `.context/docs/04-qualidade-qa.md`.
