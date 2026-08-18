# DT-05 — Dependências não declaradas

**Tipo**: Débito técnico · **Prioridade**: Alta · **Aberto em**: 2026-08-18

## Contexto

As skills importam `crewai`, mas o repositório não tem `requirements.txt` nem
`pyproject.toml`. A instalação depende de o agente hospedeiro já ter a lib —
não há como reproduzir o ambiente nem fixar versão.

Consequências: `scripts/chat.py` precisa **detectar** um Python com `crewai`
instalado, e uma quebra de API do CrewAI aparece sem aviso.

## Proposta

`requirements.txt` na raiz fixando ao menos `crewai` (versão conhecida-boa), com
nota em `docs/INSTALLATION.md` sobre criar um venv local para desenvolvimento.

## Critério de aceite

- `pip install -r requirements.txt` em venv limpo permite rodar
  `python scripts/chat.py --list` e um `--dry-run` de skill.
