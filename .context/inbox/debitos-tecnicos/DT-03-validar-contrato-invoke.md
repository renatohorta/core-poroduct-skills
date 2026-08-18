# DT-03 — Contrato `invoke` não é validado contra o argparse real

**Tipo**: Débito técnico · **Prioridade**: Alta · **Aberto em**: 2026-08-18

## Contexto

O orquestrador declara, no dict `CREWS`, como cada skill é acionada
(`invoke.briefing_arg` e `invoke.output`). Esse metadado é mantido **à mão**. Se a
skill mudar seu `argparse` e o metadado não for atualizado, a fase quebra em
execução — o argparse da skill rejeita o flag.

Casos já conhecidos: `cp-bug-fix`, `cp-goal-loop` e `cp-agilista` **não** aceitam
`--output`; `cp-goal-loop` só recebe briefing via `--goal`; `cp-agilista` e
`cp-inicializador-doc` não têm argumento posicional.

## Proposta

Teste que, para cada skill:

1. Extrai os `add_argument` reais de `skills/cp-*/scripts/run.py`.
2. Compara com `CREWS[<chave>]['invoke']` do orquestrador.
3. Falha se `output=True` mas a skill não declara `--output`, ou se o
   `briefing_arg` declarado não existe na skill.

Manter `skills/cp-orquestrador/references/skills-cli-inventory.md` como
documentação derivada desse teste.

## Critério de aceite

- Adicionar uma skill nova sem atualizar `CREWS` faz o teste falhar com mensagem
  apontando o campo divergente.
