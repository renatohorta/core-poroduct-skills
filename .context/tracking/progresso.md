# Progresso do Projeto — Core Product Skills

> Atualizado pelo orquestrador a cada fase concluída. Última atualização: 2026-08-18.

## Inicialização da documentação

| Fase | Status | Data | Artefato |
|------|--------|------|----------|
| Estrutura `.context/` | ✅ Concluído | 2026-08-18 | `.context/` + `CLAUDE.md` + `AGENT.md` |
| Visão do produto | ✅ Concluído | 2026-08-18 | `docs/00-vision.md` |
| Requisitos | ✅ Concluído | 2026-08-18 | `docs/01-requisitos.md` |
| Arquitetura | ✅ Concluído | 2026-08-18 | `docs/02-arquitetura.md` |
| Segurança/LGPD | ✅ Concluído | 2026-08-18 | `docs/03-seguranca-lgpd.md` |
| Qualidade/QA | ✅ Concluído | 2026-08-18 | `docs/04-qualidade-qa.md` |
| DevOps/Operações | ✅ Concluído | 2026-08-18 | `docs/05-devops-operacoes.md` |
| Kanban | ✅ Concluído | 2026-08-18 | `docs/06-kanban.md` |

## Estado do produto

| Área | Estado |
|------|--------|
| Skills `cp-*` | ✅ 15 skills implementadas e propagáveis |
| Orquestração | ✅ Ponto único de entrada com quality gates e 12 modos |
| Resolução de LLM | ✅ Provider-agnostic, com falha acionável (`require_llm`) |
| Distribuição | ✅ `install.sh` (Hermes + Claude) |
| Testes automatizados | ❌ Inexistentes (DT-02) — desbloqueado: `--help` funciona em 15/15 |
| CI/CD | ❌ Inexistente (DT-06) |
| Dependências declaradas | ❌ Inexistentes (DT-05) |

## Próximos passos sugeridos

Revisados após a rodada de correções de 2026-08-18:

1. **DT-05** — declarar dependências (`requirements.txt`); desbloqueia DT-02/DT-06.
2. **DT-02** — smoke tests (`--help` já funciona em 15/15, então é escrevível agora).
3. **DT-03** — validar contrato `invoke` × `argparse` (pegaria BUG-05 antes).
4. **DT-06** — CI amarrando os itens acima.
5. **DT-04** / **DOC-01** — autenticação do proxy e alinhamento de porta.

Backlog completo: `.context/docs/06-kanban.md`.
