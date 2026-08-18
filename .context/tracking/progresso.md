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
| Testes automatizados | ✅ 158 testes, sem credencial de LLM (DT-02/DT-03) |
| CI/CD | ✅ GitHub Actions: Linux 3.12/3.13 + Windows informativo (DT-06) |
| Dependências declaradas | ✅ `requirements.txt` / `requirements-dev.txt` (DT-05) |

## Proximos passos sugeridos

O backlog levantado na inicializacao foi integralmente concluido em 2026-08-18.
Nao ha item aberto. Sugestoes para quando houver apetite:

1. **`.gitattributes`** — o repo nao tem, e o Git converte LF->CRLF nos `.md` no
   Windows. Outra maquina (ou o job Windows do CI) vera diffs de arquivo inteiro
   sem mudanca real. `* text=auto eol=lf` resolve.
2. **Cobertura de codigo** — a suite cobre contrato e tratamento de erro; a
   logica interna das crews (montagem de tasks, encadeamento) segue sem teste.
3. **Versionamento das skills** — sem versao nem changelog, nao da para saber
   qual versao de uma skill esta instalada num agente.

Backlog completo: `.context/docs/06-kanban.md`.
