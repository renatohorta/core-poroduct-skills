# BUG-05 — Modo `goal-loop` do orquestrador está quebrado [Corrigido]

**Tipo**: Bug · **Severidade**: Média · **Aberto em**: 2026-08-18
**Verificado empiricamente**: sim

## Sintoma

O exemplo documentado no `SKILL.md` do `cp-orquestrador` falha:

```bash
python run.py "deploy em staging funcionando" --mode goal-loop --auto
```

A skill sai com código 1:

```
[!] Forneca --steps ou --steps-file
```

## Causa

Contrato divergente entre o que o orquestrador envia e o que a skill exige:

| | |
|---|---|
| Orquestrador envia (`invoke.briefing_arg = "goal"`) | `--goal <briefing>` |
| `cp-goal-loop` exige | `--goal` **e** (`--steps` ou `--steps-file`) |

Os `cli_args` declarados na crew já listam `--steps`, mas `_build_cli_args()` só
monta `--goal` — o metadado `cli_args` é documental, não é usado para montar a
chamada.

## Correção proposta

Duas opções:

1. **Derivar os passos do briefing** — o orquestrador quebra o briefing em passos
   e envia `--steps`. Mais alinhado ao papel de orquestrador, exige heurística.
2. **Tornar `--steps` opcional na skill** — sem passos, `cp-goal-loop` deriva um
   passo único a partir do `--goal`. Menor mudança, e o loop de
   tentativa-e-correção continua fazendo sentido com um passo só.

Recomendo (2): mantém o contrato `invoke` simples e faz o exemplo documentado
funcionar.

## Critério de aceite

- `python run.py "<objetivo>" --mode goal-loop --auto` executa sem erro de argumento.
- Este caso vira teste do DT-03 (validação de contrato `invoke` × `argparse`).


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
