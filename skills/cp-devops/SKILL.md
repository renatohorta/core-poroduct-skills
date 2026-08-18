---
name: cp-devops
description: "DevOps e Infraestrutura — cria uma crew CrewAI com Engenheiros de CI/CD, Infraestrutura, Monitoramento e Segurança de Infra para configurar pipelines, provisionar infraestrutura e realizar deploy. Use quando o usuário disser 'fazer deploy', 'configurar CI/CD', 'provisionar infraestrutura', 'subir ambiente', 'configurar monitoramento'."
---

# cp-devops — DevOps e Infraestrutura Crew

Cria uma crew CrewAI self-contained com agentes especializados em DevOps e Infraestrutura para configurar pipelines de CI/CD, provisionar infraestrutura como código, configurar monitoramento e realizar revisão de segurança.

## Agentes

| Agente | Função |
|--------|--------|
| **Engenheiro de CI/CD** | Configura pipelines de build/test/deploy (GitHub Actions, GitLab CI) |
| **Engenheiro de Infraestrutura** | Terraform, Docker, Kubernetes, cloud (AWS/GCP/Azure) |
| **Engenheiro de Monitoramento** | Configura logging, métricas, alertas (Grafana, Prometheus, Datadog) |
| **Engenheiro de Segurança de Infra** | Revisa segurança da infraestrutura, firewalls, IAM, secrets |

## Pipeline (Tasks Sequenciais)

```
1. Análise de Requisitos de Infra  →  (Eng. Infraestrutura)
2. Configuração de CI/CD           →  (Eng. CI/CD)
3. Provisionamento de Infraestrutura → (Eng. Infraestrutura)
4. Configuração de Monitoramento   →  (Eng. Monitoramento)
5. Revisão de Segurança            →  (Eng. Segurança Infra)
6. Quality Gate                    →  (Todos — PASS/FAIL)
```

## Entrada

- Descrição do projeto + requisitos de infraestrutura
- Pode ser texto direto ou arquivo via `--input`

## Saída

- Pipeline CI/CD configurado
- Infraestrutura provisionada (IaC)
- Monitoramento ativo (métricas, logs, alertas)
- Relatório de segurança
- Quality Gate: PASS/FAIL

## Quality Gate

O Quality Gate final verifica:
1. Pipeline CI/CD configurado e funcional
2. Health check da infraestrutura passando
3. Monitoramento coletando métricas
4. Sem vulnerabilidades críticas de segurança

Veredito: **PASS** (tudo verde) ou **FAIL** (itens a corrigir).

## Modos

| Modo | Escopo |
|------|--------|
| `full` (default) | Pipeline completo: análise → CI/CD → infra → monitoramento → segurança → quality gate |
| `ci-cd` | Apenas configuração de pipeline CI/CD |
| `infra` | Apenas provisionamento de infraestrutura |
| `monitoring` | Apenas configuração de monitoramento |
| `security` | Apenas revisão de segurança |

## Uso

```bash
# Descrição direta
python .hermes/skills/cp-devops/scripts/run.py "subir ambiente de staging com PostgreSQL e Redis"

# Modo específico
python .hermes/skills/cp-devops/scripts/run.py --mode ci-cd "configurar GitHub Actions para o repositório"

# Arquivo de entrada
python .hermes/skills/cp-devops/scripts/run.py --input requisitos-infra.txt

# Salvar saída
python .hermes/skills/cp-devops/scripts/run.py "deploy em produção" --output relatorio.md

# Dry run (apenas monta a crew)
python .hermes/skills/cp-devops/scripts/run.py "teste" --dry-run
```

## Exemplos

```bash
# Exemplo 1: Deploy completo
python .hermes/skills/cp-devops/scripts/run.py \
  "subir ambiente de produção para o sistema de agendamento: \
   AWS EC2 com Docker, PostgreSQL RDS, Redis ElastiCache, \
   GitHub Actions para CI/CD, Grafana + Prometheus para monitoramento"

# Exemplo 2: Apenas CI/CD
python .hermes/skills/cp-devops/scripts/run.py --mode ci-cd \
  "configurar GitHub Actions com testes, lint, build Docker e deploy automático"

# Exemplo 3: Apenas segurança
python .hermes/skills/cp-devops/scripts/run.py --mode security \
  "revisar segurança da infraestrutura atual: AWS com ECS, RDS, S3, Lambda"
```

## Infra Cleanup (remoção de dependências)

Quando uma migração de código (ex: Celery → asyncio) elimina a necessidade de um serviço de infraestrutura (ex: Redis/ElastiCache), o Terraform e scripts associados precisam ser atualizados. Checklist:

1. **Terraform**: remover o resource do serviço (ex: `aws_elasticache_replication_group`)
2. **Security Groups**: remover SG do serviço removido
3. **ECS Task Definitions**: remover containers que não são mais necessários (ex: `celery-worker`, `celery-beat`)
4. **CloudWatch Log Groups**: remover log groups dos containers removidos
5. **Secrets Manager**: remover secrets que não são mais necessários (ex: `REDIS_URL`)
6. **Outputs**: remover outputs do serviço removido
7. **Dockerfile / docker-compose**: remover referências ao serviço
8. **Scripts de dev**: remover health checks e dependências do serviço
9. **Código**: remover health checks e conexões ao serviço no código da aplicação
10. **Testes**: atualizar mocks e patches que referenciam o serviço removido

**Economia típica:** ElastiCache Redis `cache.t4g.small` = ~$20/mês + NAT Gateway = ~$32/mês + Fargate containers = ~$30/mês.

## Code Migration (troca de worker/broker)

Quando uma migração substitui um sistema de filas (ex: Celery → asyncio nativo), além da infra, o código precisa de atenção nestes pontos:

### 1. Tasks — criar versões async

Criar `*_async.py` para cada app que tinha tasks Celery. A função `run_crew` (pipeline principal) é a mais crítica — precisa chamar `Crew.kickoff_async()` em vez de `Crew.kickoff()`.

### 2. Imports — varredura de stale imports

Após deletar os `tasks.py` antigos, varrer TODOS os arquivos `.py` por imports quebrados:

```python
deleted_modules = ["agents.tasks", "chat.tasks", "crews.tasks", "crews.callbacks",
                   "knowledge.tasks", "integrations.tasks", "activity.tasks", "config.celery"]
```

**Pitfall comum:** imports inseridos dentro de blocos multi-line existentes. Exemplo:
```python
# ERRADO — import dentro dos parênteses do from .models import (...)
from .models import (
from config.task_proxy import enqueue_task_sync  # ← quebra a sintaxe
    CrewInstance,
)
```

### 3. Chamadas `.delay()` → `enqueue_task_sync()`

Toda chamada `task.delay(args)` vira `enqueue_task_sync("task_name", task_async_fn, args)`. O proxy `config/task_proxy.py` fornece `enqueue_task_sync()` para chamadas síncronas (views/services) e `enqueue_task()` para async.

### 4. Funções async chamadas de contexto síncrono

Testes e código que chamavam funções Celery diretamente agora chamam `async def`. Precisam de `asyncio.run()`:

```python
# Antes
sweep_stalled_runs()
# Depois
import asyncio
asyncio.run(sweep_stalled_runs())
```

### 5. Settings removidos acidentalmente

A limpeza de settings `CELERY_*` pode remover settings não-Celery que estavam próximos. Verificar:
- `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_TIMEOUT`
- `CREW_RUN_STALE_AFTER`, `CREW_RUN_TIME_LIMIT`, `CREW_LLM_TIMEOUT`
- `CELERY_TASK_ALWAYS_EAGER` (adicionar como compat, sempre True)

### 6. Testes — `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`

Remover ou comentar decorators que referenciam settings deletados. Substituir por `asyncio.run()` nas chamadas de funções async.

### 7. Boot do Django — `crewai_tools_adapter` pode travar

O módulo `chat/skills/crewai_tools_adapter.py` executa código no nível do módulo (não lazy). Algumas tools do CrewAI chamam `input()` ou fazem I/O de rede no `__init__`, travando o boot do `manage.py` para sempre.

**Solução:** tornar a descoberta lazy — substituir o código no final do arquivo por uma função `get_discovery_summary()` que só roda na primeira chamada, não no import.

**Solução rápida:** setar `CREWAI_TOOLS_DISCOVERY=0` no ambiente ou no `manage.py` antes de qualquer import do Django.

### 8. `manage.py` — conflito de `lxml` entre venvs

Se o Hermes Agent tiver um `lxml` quebrado no path, o `sys.path` do projeto pode carregá-lo antes do `lxml` do `.venv`. Corrigir no `manage.py`:

```python
_project_site = os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages")
_hermes_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "AppData", "Local", "hermes", "hermes-agent", "venv", "Lib", "site-packages",
)
if _project_site in sys.path:
    sys.path.remove(_project_site)
sys.path.insert(0, _project_site)
sys.path = [p for p in sys.path if _hermes_site not in p]
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
