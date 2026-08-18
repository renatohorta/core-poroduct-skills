# Catálogo de Skills

Catálogo detalhado de cada skill do repositório, com gatilhos de uso, agentes e
saídas. Para o conteúdo completo, veja o `SKILL.md` de cada skill.

## Fábrica de Software (CrewAI)

### cp-orquestrador
**Gerente da Fábrica de Software.** Coordena todas as crews em sequência, gerencia
artefatos entre fases e aplica quality gates. Inclui o pipeline NEXUS nativo.

- **Gatilho**: "executar pipeline completo", "fazer fábrica de software", "entregar produto"
- **Agentes**: Orquestrador de Pipeline, Gestor de Artefatos, Tomador de Decisão, Relator de Progresso
- **Modos**: full, sprint, micro, security-audit, documentation, bugfix, competitive, full-dev, goal-loop, manutencao
- **Script**: `scripts/run.py`

### cp-requisitos
**Engenharia de Requisitos.** Elicita, especifica, valida e prioriza requisitos.

- **Gatilho**: "levantar requisitos", "especificar", "criar user stories"
- **Agentes**: Analista de Negócios, Especificador, Validador, PO Proxy
- **Saída**: Documento de Requisitos, Backlog Priorizado (MoSCoW)

### cp-arquitetura
**Arquitetura e Design de Software.** Projeta arquitetura, modela dados, desenha APIs.

- **Gatilho**: "definir arquitetura", "modelar dados", "desenhar API", "criar ADR"
- **Agentes**: Arquiteto de Software, Dados, API, UX, Revisor Técnico
- **Saída**: Documento de Arquitetura, ADRs, Modelagem de Dados, Contratos de API

### cp-implementacao
**Implementação de Software.** Codifica features backend/frontend/mobile com code review.

- **Gatilho**: "implementar", "codificar", "desenvolver", "fazer code review"
- **Agentes**: Dev Backend, Frontend, Mobile, Revisor, Integrador
- **Saída**: Código Fonte, Relatório de Code Review, Relatório de Integração

### cp-testes
**Testes de Software.** Executa testes unitários, integração, E2E e performance.

- **Gatilho**: "testar", "criar testes", "validar qualidade", "aumentar cobertura"
- **Agentes**: Eng. Testes Unitários, Integração, E2E, Performance, Analista
- **Saída**: Relatório de Testes, Evidências, Cobertura

### cp-seguranca
**Segurança de Software.** Análise de vulnerabilidades, pentest, compliance.

- **Gatilho**: "auditar segurança", "fazer pentest", "verificar vulnerabilidades", "OWASP"
- **Agentes**: Analista de Segurança, Pentester, Compliance, Engenheiro de Correção
- **Saída**: Relatório de Segurança, Correções Implementadas

### cp-devops
**DevOps e Infraestrutura.** CI/CD, infraestrutura como código, monitoramento, deploy.

- **Gatilho**: "fazer deploy", "configurar CI/CD", "provisionar infraestrutura"
- **Agentes**: Eng. CI/CD, Infra, Monitoramento, Segurança de Infra
- **Saída**: Pipeline CI/CD, Infraestrutura Provisionada, Monitoramento Ativo

### cp-documentacao
**Documentação de Software.** Gera documentação técnica, de API, de usuário e diagramas.

- **Gatilho**: "documentar", "criar documentação", "escrever README", "gerar docs da API"
- **Agentes**: Redator Técnico, Usuário, Diagramador, Revisor
- **Saída**: README.md, Documentação de API, Manual do Usuário, Diagramas

### cp-qualidade
**Qualidade de Software.** Auditoria final: métricas, artefatos, melhoria contínua.

- **Gatilho**: "auditar qualidade", "medir métricas", "garantir qualidade"
- **Agentes**: Auditor, Analista de Métricas, Melhoria Contínua, Validador
- **Saída**: Relatório de Qualidade, Certificado de Qualidade

### cp-bug-fix
**Correção de Bug (NEXUS-Micro).** Corrige bugs com Developer → QA → Evidence Collector.

- **Gatilho**: "corrigir bug", "consertar erro", "fix"
- **Agentes**: Developer, QA (API Tester), Test Automation Engineer, Evidence Collector
- **Saída**: Correção implementada, Testes automatizados, Evidências
- **Limite**: máx. 3 retries

### cp-competitive-analysis
**Análise Competitiva.** Compara produtos, features, preços, posicionamento e estratégia.

- **Gatilho**: "analisar concorrentes", "análise competitiva", "battle card", "SWOT"
- **Agentes**: Analista de Mercado, Competidores, Pricing/Posicionamento, Estrategista
- **Saída**: Relatório de Inteligência Competitiva, Battle Cards, SWOT

### cp-goal-loop
**Loop Autônomo de Tentativa-e-Correção.** Executa um processo até atingir sucesso.

- **Gatilho**: "realizar processo completo", "testar de ponta a ponta", "validar fluxo"
- **Entrada**: `--goal` (obrigatório), `--steps`
- **Saída**: Processo concluído, Log de tentativas

### cp-manutencao
**Manutenção e Evolução de Software.** Diagnostica bugs, refatora código, avalia impacto.

- **Gatilho**: "corrigir bug", "refatorar", "melhorar código", "fazer manutenção"
- **Agentes**: Analista de Bugs, Desenvolvedor de Correção, Refatoração, Analista de Impacto
- **Modos**: bug-fix, refactor, improvement, full

### cp-agilista
**Esteira de Execução.** Monitora o backlog (local `.kanban/` ou Trello), despacha
tarefas prontas para a `cp-orquestrador` e gerencia o loop bidirecional de feedback.

- **Gatilho**: "agilista", "esteira de tarefas", "kanban", "monitorar backlog", "dúvida", "impedimento"
- **Componentes**: CPAgilistaDaemon (polling), CPAgilistaFeedbackLoop (dúvidas/impedimentos/retomada), TrelloIntegration, LocalIntegration
- **Eventos**: TASK_DISPATCHED, DUVIDA, IMPEDIMENTO, HUMAN_CLARIFICATION_RECEIVED
- **Script**: `scripts/run.py` (`--daemon`, `--duvida`, `--impedimento`, `--resume`, `--init`, `--doc`)

### cp-inicializador-doc
**Inicializador de Documentação.** Centraliza o contexto do projeto em `.context/`
como fonte de verdade única, cria ponteiros `CLAUDE.md`/`AGENT.md` na raiz e gera
a estrutura de documentação por disciplina.

- **Gatilho**: "inicializar documentação", "iniciar projeto", "setup de docs", "criar estrutura de contexto"
- **Estrutura**: `.context/docs/` (disciplinas), `.context/inbox/` (iniciativas, tasks, bugs, débitos), `.context/tracking/` (progresso, decisões)
- **Script**: `scripts/run.py` (`--dir`, `--dry-run`)
