#!/usr/bin/env python3
"""
cp-devops — DevOps e Infraestrutura Crew (self-contained)

Cria uma crew CrewAI com agentes especializados em DevOps:
  Eng. CI/CD → Eng. Infraestrutura → Eng. Monitoramento → Eng. Segurança Infra

Uso:
  python run.py "subir ambiente de staging com PostgreSQL e Redis"
  python run.py --mode ci-cd "configurar GitHub Actions"
  python run.py --input requisitos.txt --output relatorio.md
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # DT-07: a lib so e exigida na execucao real, nao no --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # DT-01: UTF-8 no stdout/stderr (console Windows e cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# AGENTES EMBUTIDOS (self-contained)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "engenheiro-ci-cd": {
        "role": "Engenheiro de CI/CD",
        "goal": "Configurar pipelines de build, teste e deploy automatizados e confiáveis",
        "backstory": (
            "Engenheiro de CI/CD obcecado por automação. Você odeia deploys manuais "
            "e acredita que todo processo repetitivo deve ser automatizado. "
            "Especialista em GitHub Actions, GitLab CI, Jenkins e CircleCI. "
            "Você configura pipelines com build, testes automatizados, análise estática, "
            "scan de segurança, build de containers Docker e deploy em múltiplos ambientes. "
            "Seu lema: 'Se precisa de um humano para rodar, não é um pipeline — é uma tarefa.' "
            "Você garante que cada pipeline tenha stages claros, cache inteligente, "
            "e falhe rápido com mensagens de erro úteis."
        ),
    },
    "engenheiro-infraestrutura": {
        "role": "Engenheiro de Infraestrutura",
        "goal": "Provisionar infraestrutura escalável, segura e reproduzível como código",
        "backstory": (
            "Engenheiro de infraestrutura que trata tudo como código. "
            "Você NUNCA faz SSH para configurar um servidor — tudo é Terraform, "
            "Pulumi, CloudFormation, Docker Compose ou Kubernetes. "
            "Especialista em AWS, GCP e Azure, com profundo conhecimento de "
            "VPCs, subnets, security groups, IAM roles, load balancers, "
            "auto-scaling groups, bancos de dados gerenciados e Kubernetes. "
            "Você projeta infraestrutura seguindo o Well-Architected Framework: "
            "excelência operacional, segurança, confiabilidade, eficiência de performance "
            "e otimização de custos. Seu mantra: 'Se não está no repositório, não existe.'"
        ),
    },
    "engenheiro-monitoramento": {
        "role": "Engenheiro de Monitoramento",
        "goal": "Configurar observabilidade completa: métricas, logs, tracing e alertas proativos",
        "backstory": (
            "SRE experiente que descobre problemas antes dos usuários. "
            "Você configura observabilidade de ponta a ponta com Prometheus, "
            "Grafana, Datadog, New Relic, ELK Stack e OpenTelemetry. "
            "Você cria dashboards que contam a história do sistema, "
            "alertas com thresholds inteligentes (evitando alert fatigue), "
            "e logging estruturado que permite debug rápido. "
            "Você implementa SLIs, SLOs e error budgets. "
            "Seu lema: 'Se não está sendo monitorado, não está em produção.' "
            "Você odeia dashboards bonitos mas inúteis — cada métrica deve "
            "responder a uma pergunta específica sobre a saúde do sistema."
        ),
    },
    "engenheiro-seguranca-infra": {
        "role": "Engenheiro de Segurança de Infraestrutura",
        "goal": "Identificar e mitigar vulnerabilidades de segurança na infraestrutura",
        "backstory": (
            "Security engineer paranóico — e com razão. Você assume que tudo está "
            "comprometido até prova em contrário. Especialista em segurança de cloud: "
            "IAM policies, security groups, network ACLs, encryption at rest e in transit, "
            "secret management, vulnerability scanning e compliance (SOC2, HIPAA, PCI). "
            "Você revisa cada porta aberta, cada permissão de IAM, cada variável de ambiente "
            "que pode conter um secret. Você implementa o princípio do menor privilégio "
            "religiosamente. Seu lema: 'Não é paranóia se eles realmente estão atrás de você.' "
            "Você sempre pergunta: 'E se esse container for comprometido? Qual o raio do estrago?'"
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    """Get a CrewAI Agent from the embedded definitions."""
    data = AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agente não encontrado: {slug} — usando fallback genérico")
        return Agent(
            role=name,
            goal=f"Completar a tarefa com excelência como {name}",
            backstory=f"Agente especializado atuando como {name}.",
            llm=_crew_llm,
            verbose=True,
            allow_delegation=False,
        )
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        llm=_crew_llm,
        verbose=True,
        allow_delegation=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Crew builder
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(description: str, mode: str = "full"):
    """Build a CrewAI crew for DevOps and Infrastructure."""

    eng_ci_cd = get_agent("engenheiro-ci-cd")
    eng_infra = get_agent("engenheiro-infraestrutura")
    eng_monitoring = get_agent("engenheiro-monitoramento")
    eng_security = get_agent("engenheiro-seguranca-infra")

    tasks = []

    # ── Task 1: Análise de Requisitos de Infra ──────────────────────────
    if mode in ("full", "infra"):
        task_analise = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — ANÁLISE DE REQUISITOS DE INFRAESTRUTURA:
            Analise a descrição do projeto e produza um plano detalhado de infraestrutura:

            1. **Requisitos de infraestrutura** — compute, armazenamento, rede, banco de dados
            2. **Provedor cloud recomendado** — AWS, GCP ou Azure com justificativa
            3. **Arquitetura proposta** — diagrama textual dos componentes e suas conexões
            4. **Serviços necessários** — EC2/ECS/EKS, RDS, ElastiCache, S3, CloudFront, etc.
            5. **Dimensionamento estimado** — instâncias, storage, bandwidth
            6. **Estratégia de deploy** — blue/green, canary, rolling update
            7. **Estimativa de custos** — mensal aproximada por serviço

            Seja específico. Nada de genérico como "use a nuvem".
            """,
            expected_output=(
                "Plano de infraestrutura detalhado: provedor, arquitetura, "
                "serviços, dimensionamento, estratégia de deploy e estimativa de custos"
            ),
            agent=eng_infra,
        )
        tasks.append(task_analise)

    # ── Task 2: Configuração de CI/CD ──────────────────────────────────
    if mode in ("full", "ci-cd"):
        task_cicd = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — CONFIGURAÇÃO DE PIPELINE CI/CD:
            Projete e descreva a configuração completa do pipeline de CI/CD:

            1. **Plataforma escolhida** — GitHub Actions, GitLab CI, Jenkins (justifique)
            2. **Estrutura do pipeline** — stages, jobs, dependências
            3. **Stages obrigatórios**:
               - Build: compilação/build da aplicação
               - Lint: análise estática de código
               - Test: testes unitários, integração, e2e
               - Security Scan: SAST, dependency scanning
               - Build Docker: build e push de imagem
               - Deploy: deploy em staging/produção
            4. **Estratégia de cache** — dependências, layers Docker
            5. **Gerenciamento de secrets** — como expor variáveis de ambiente seguras
            6. **Estratégia de deploy** — blue/green, canary, rolling
            7. **Rollback** — como reverter em caso de falha
            8. **Notificações** — Slack, email, Discord em caso de falha/sucesso

            Forneça o YAML/config real do pipeline, não apenas descrição textual.
            """,
            expected_output=(
                "Configuração completa do pipeline CI/CD com YAML real, "
                "estratégia de deploy, gerenciamento de secrets e rollback"
            ),
            agent=eng_ci_cd,
        )
        tasks.append(task_cicd)

    # ── Task 3: Provisionamento de Infraestrutura ──────────────────────
    if mode in ("full", "infra"):
        task_provisionamento = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — PROVISIONAMENTO DE INFRAESTRUTURA:
            Com base na análise de requisitos, produza o código IaC necessário:

            1. **Terraform/HCL** — recursos principais (VPC, subnets, security groups, EC2/ECS, RDS, etc.)
            2. **Docker Compose ou Kubernetes manifests** — se aplicável
            3. **Estrutura de diretórios** — organização do repositório de infra
            4. **Variáveis e outputs** — parametrização do módulo
            5. **State management** — backend remoto (S3 + DynamoDB, GCS, etc.)
            6. **Network topology** — VPC, subnets públicas/privadas, NAT gateway, load balancer
            7. **Database** — RDS, configuração de backup, multi-AZ
            8. **Storage** — S3 buckets, políticas de lifecycle
            9. **IAM** — roles e policies com menor privilégio

            Forneça o código HCL real, não apenas descrição.
            """,
            expected_output=(
                "Código IaC completo (Terraform HCL, Docker Compose ou K8s manifests) "
                "com variáveis, outputs, state management e network topology"
            ),
            agent=eng_infra,
        )
        tasks.append(task_provisionamento)

    # ── Task 4: Configuração de Monitoramento ──────────────────────────
    if mode in ("full", "monitoring"):
        task_monitoring = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — CONFIGURAÇÃO DE MONITORAMENTO:
            Projete a estratégia completa de observabilidade:

            1. **Métricas** — Prometheus/Datadog:
               - Métricas de infraestrutura (CPU, memória, disco, rede)
               - Métricas de aplicação (latência, throughput, error rate, saturation)
               - Métricas de negócio (usuários ativos, transações, revenue)
            2. **Dashboards** — Grafana:
               - Dashboard de visão geral do sistema
               - Dashboard de performance e latência
               - Dashboard de erros e exceções
               - Dashboard de custos
            3. **Logging** — ELK/Loki/CloudWatch:
               - Logging estruturado (JSON)
               - Níveis de log (debug, info, warn, error, fatal)
               - Agregação e busca centralizada
            4. **Alertas**:
               - Regras de alerta com thresholds e severidades
               - Escalações (PagerDuty/OpsGenie)
               - Notificações (Slack, email)
            5. **Tracing** — OpenTelemetry/Jaeger:
               - Distributed tracing para requisições cross-service
            6. **SLOs/SLIs**:
               - Definição de Service Level Objectives
               - Error budgets

            Seja específico nas configurações: thresholds, queries PromQL, painéis.
            """,
            expected_output=(
                "Estratégia de observabilidade completa: métricas, dashboards, "
                "logging, alertas, tracing e SLOs com configurações específicas"
            ),
            agent=eng_monitoring,
        )
        tasks.append(task_monitoring)

    # ── Task 5: Revisão de Segurança ────────────────────────────────────
    if mode in ("full", "security"):
        task_security = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — REVISÃO DE SEGURANÇA DE INFRAESTRUTURA:
            Revise toda a infraestrutura proposta e identifique vulnerabilidades:

            1. **Network Security**:
               - Portas expostas desnecessariamente?
               - Security groups muito permissivos (0.0.0.0/0)?
               - Subnets públicas vs privadas corretas?
               - WAF configurado?
            2. **IAM e Acesso**:
               - Princípio do menor privilégio aplicado?
               - Roles vs users vs service accounts?
               - MFA obrigatório?
               - Access keys rotacionadas?
            3. **Data Security**:
               - Encryption at rest (EBS, RDS, S3)?
               - Encryption in transit (TLS)?
               - Secrets management (Vault, AWS Secrets Manager)?
            4. **Container Security**:
               - Imagens escaneadas por vulnerabilidades?
               - Container rodando como root?
               - Resource limits configurados?
               - Read-only filesystem?
            5. **Compliance**:
               - A aplicação precisa de SOC2, HIPAA, PCI, LGPD?
               - Audit logging configurado?
            6. **Incident Response**:
               - Plano de resposta a incidentes?
               - Backup e disaster recovery?
               - Runbooks documentados?

            Para cada vulnerabilidade encontrada, classifique: CRÍTICA, ALTA, MÉDIA, BAIXA.
            Forneça recomendações específicas de mitigação para cada uma.
            """,
            expected_output=(
                "Relatório de segurança completo: vulnerabilidades classificadas "
                "por severidade, recomendações de mitigação, e checklist de compliance"
            ),
            agent=eng_security,
        )
        tasks.append(task_security)

    # ── Task 6: Quality Gate ────────────────────────────────────────────
    if mode == "full":
        quality_gate = Task(
            description=f"""
            DESCRIÇÃO DO PROJETO:
            {description}

            SEU TRABALHO — QUALITY GATE FINAL:
            Revise todas as entregas das etapas anteriores e emita um veredito.

            Verifique:

            1. **Pipeline CI/CD**:
               - Pipeline configurado com todos os stages necessários?
               - Estratégia de deploy definida?
               - Rollback configurado?
               - Secrets gerenciados com segurança?

            2. **Infraestrutura**:
               - Código IaC completo e reproduzível?
               - State management configurado?
               - Network topology segura?
               - Backup e disaster recovery?

            3. **Monitoramento**:
               - Métricas essenciais coletadas?
               - Dashboards criados?
               - Alertas configurados com thresholds?
               - Logging estruturado?

            4. **Segurança**:
               - Sem vulnerabilidades CRÍTICAS ou ALTAS?
               - Encryption configurado (at rest e in transit)?
               - IAM com menor privilégio?
               - Secrets management implementado?

            Emita o veredito:

            ✅ **PASS** — Tudo verde. A infraestrutura está pronta para produção.
            ❌ **FAIL** — Itens a corrigir antes de prosseguir.

            Se FAIL, liste exatamente o que precisa ser corrigido, priorizado por severidade.
            """,
            expected_output=(
                "Quality Gate final: veredito PASS/FAIL com checklist completo "
                "de cada dimensão (CI/CD, infra, monitoramento, segurança)"
            ),
            agent=eng_security,
        )
        tasks.append(quality_gate)

    # ── Crew ────────────────────────────────────────────────────────────
    agents = []
    if mode in ("full", "ci-cd"):
        agents.append(eng_ci_cd)
    if mode in ("full", "infra"):
        agents.append(eng_infra)
    if mode in ("full", "monitoring"):
        agents.append(eng_monitoring)
    if mode in ("full", "security"):
        agents.append(eng_security)

    # Ensure all agents are included for full mode
    if mode == "full":
        agents = [eng_ci_cd, eng_infra, eng_monitoring, eng_security]

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-devops: DevOps e Infraestrutura Crew (self-contained)",
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Descrição do projeto e requisitos de infraestrutura",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o relatório",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "ci-cd", "infra", "monitoring", "security"],
        default="full",
        help="Modo de execução (default: full — pipeline completo)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: mensagem acionavel em vez de traceback

    # --- Resolve description ---
    description = None
    if args.input_file:
        description = Path(args.input_file).read_text(encoding="utf-8")
    elif args.description:
        description = args.description
    else:
        parser.print_help()
        print("\n❌ Erro: forneça a descrição do projeto (argumento ou --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    mode_labels = {
        "full": "Pipeline completo (CI/CD + Infra + Monitoramento + Segurança + Quality Gate)",
        "ci-cd": "Apenas CI/CD",
        "infra": "Apenas Infraestrutura",
        "monitoring": "Apenas Monitoramento",
        "security": "Apenas Segurança",
    }

    print(f"\n📋 Projeto: {description[:120]}...")
    print(f"🔧 Modo: {mode_labels.get(mode, mode)}")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(description, mode)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            desc_short = task.description[:80].replace("\n", " ").strip()
            print(f"  {i}. {task.agent.role}: {desc_short}...")
        print("\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de DevOps...\n")
    require_llm()  # DT-08: falha cedo, com mensagem, se nao ha LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Relatório de DevOps gerado!\n")
    print(result_str)

    # --- Save output ---
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")
    else:
        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"devops_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()