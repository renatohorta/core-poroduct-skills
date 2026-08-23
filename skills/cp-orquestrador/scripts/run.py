#!/usr/bin/env python3
"""
cp-orquestrador — Orquestrador da Fábrica de Software (self-contained)

Coordena todo o pipeline de desenvolvimento. Dois modos:

  SIMULAÇÃO (default):  Usa CrewAI para planejar, simular e documentar o pipeline.
  AUTO (--auto):        Executa as crews reais em sequência, passando artefatos
                        entre fases e aplicando quality gates automaticamente.

Modos de pipeline:
  full              — Todas as 8 crews (requisitos → arquitetura → implementação
                      → testes → segurança → devops → documentação → qualidade)
  sprint            — requisitos → arquitetura → implementação → testes → devops
  micro             — implementação → testes (bug fix)
  security-audit    — segurança → qualidade
  documentation     — documentação → qualidade
  bugfix            — cp-bug-fix (Developer → QA → Evidence Collector)
  competitive       — cp-competitive-analysis (inteligência competitiva)
  full-dev          — pipeline NEXUS completo (nativo, merge de cp-full-dev)
  goal-loop         — cp-goal-loop (tentativa-e-correção até sucesso)
  manutencao        — cp-manutencao (bug-fix/refactor/improvement/full)
  agilista          — cp-agilista (esteira de execução + feedback loop)

Uso:
  # Simulação (planejamento)
  python run.py "sistema de agendamento para clínicas"

  # Execução automática (roda as crews de verdade)
  python run.py "sistema de agendamento para clínicas" --auto
  python run.py "feature de relatório PDF" --mode sprint --auto
  python run.py "corrigir erro de login" --mode micro --auto
  python run.py "app financeiro" --mode security-audit --auto
  python run.py --input briefing.txt --auto
  python run.py "sistema de estoque" --start-phase implementacao --auto

  # Skills complementares via orquestrador
  python run.py "o endpoint /login retorna 500" --mode bugfix --auto
  python run.py "SaaS de clínicas; concorrentes: Doctoralia" --mode competitive --auto
  python run.py "sistema de agendamento" --mode full-dev --auto
  python run.py "deploy em staging funcionando" --mode goal-loop --auto
  python run.py "refatorar módulo de pagamentos" --mode manutencao --auto
"""

import argparse
import sys
import json
import os
import subprocess
import re
import time
from pathlib import Path
from datetime import datetime
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import build_crew_llm, require_llm, setup_console

setup_console()  # DT-01: UTF-8 no stdout/stderr (console Windows e cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO — caminhos das skills
# ═══════════════════════════════════════════════════════════════════════════

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent  # skills/
ORQUESTRADOR_DIR = Path(__file__).resolve().parent.parent

SKILL_PATHS = {
    "requisitos": SKILLS_DIR / "cp-requisitos" / "scripts" / "run.py",
    "arquitetura": SKILLS_DIR / "cp-arquitetura" / "scripts" / "run.py",
    "implementacao": SKILLS_DIR / "cp-implementacao" / "scripts" / "run.py",
    "testes": SKILLS_DIR / "cp-testes" / "scripts" / "run.py",
    "seguranca": SKILLS_DIR / "cp-seguranca" / "scripts" / "run.py",
    "devops": SKILLS_DIR / "cp-devops" / "scripts" / "run.py",
    "documentacao": SKILLS_DIR / "cp-documentacao" / "scripts" / "run.py",
    "qualidade": SKILLS_DIR / "cp-qualidade" / "scripts" / "run.py",
    # Skills complementares — acionáveis pelo orquestrador
    "bug-fix": SKILLS_DIR / "cp-bug-fix" / "scripts" / "run.py",
    "competitive-analysis": SKILLS_DIR / "cp-competitive-analysis" / "scripts" / "run.py",
    "goal-loop": SKILLS_DIR / "cp-goal-loop" / "scripts" / "run.py",
    "manutencao": SKILLS_DIR / "cp-manutencao" / "scripts" / "run.py",
    "agilista": SKILLS_DIR / "cp-agilista" / "scripts" / "run.py",
    "inicializador-doc": SKILLS_DIR / "cp-inicializador-doc" / "scripts" / "run.py",
}

# ═══════════════════════════════════════════════════════════════════════════
# DEFINIÇÃO DAS CREWS / FASES DO PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

CREWS = {
    "requisitos": {
        "name": "Engenharia de Requisitos",
        "skill": "cp-requisitos",
        "description": "Elicita, especifica, valida e prioriza requisitos de software.",
        "agents": ["Analista de Negócios", "Especificador de Requisitos",
                    "Validador de Requisitos", "Product Owner (Proxy)"],
        "inputs": ["Briefing do cliente"],
        "outputs": ["Documento de Requisitos", "Backlog Priorizado (MoSCoW)"],
        "quality_gate": "Validação de completude, consistência e viabilidade",
        "cli_args": [],
    },
    "arquitetura": {
        "name": "Arquitetura e Design de Software",
        "skill": "cp-arquitetura",
        "description": "Projeta a arquitetura do sistema: ADRs, diagramas, schemas, APIs.",
        "agents": ["Arquiteto de Software", "Arquiteto de Dados",
                    "Arquiteto de API", "UX Architect", "Revisor Técnico"],
        "inputs": ["Documento de Requisitos"],
        "outputs": ["Documento de Arquitetura", "ADRs", "Modelagem de Dados", "Contratos de API"],
        "quality_gate": "Revisão de arquitetura: viabilidade técnica, aderência a requisitos não-funcionais",
        "cli_args": ["--input"],
    },
    "implementacao": {
        "name": "Implementação de Software",
        "skill": "cp-implementacao",
        "description": "Implementa código backend, frontend e mobile com code review.",
        "agents": ["Desenvolvedor Backend", "Desenvolvedor Frontend",
                    "Desenvolvedor Mobile", "Revisor de Código", "Integrador"],
        "inputs": ["Documento de Arquitetura", "Contratos de API"],
        "outputs": ["Código Fonte", "Relatório de Code Review", "Relatório de Integração"],
        "quality_gate": "Code review aprovado, integração validada, testes unitários passando",
        "cli_args": ["--input", "--type"],
    },
    "testes": {
        "name": "Testes de Software",
        "skill": "cp-testes",
        "description": "Executa testes unitários, integração, E2E e performance.",
        "agents": ["Eng. Testes Unitários", "Eng. Testes Integração",
                    "Eng. Testes E2E", "Eng. Testes Performance", "Analista de Resultados"],
        "inputs": ["Código Fonte", "Critérios de Aceitação"],
        "outputs": ["Relatório de Testes", "Evidências", "Cobertura"],
        "quality_gate": "Cobertura mínima ≥ 80%, 0 bugs críticos, performance dentro do SLA",
        "cli_args": ["--input", "--source"],
    },
    "seguranca": {
        "name": "Segurança de Software",
        "skill": "cp-seguranca",
        "description": "Análise de segurança, pentest, compliance LGPD/GDPR.",
        "agents": ["Analista de Segurança", "Penetration Tester",
                    "Especialista em Compliance", "Engenheiro de Correção"],
        "inputs": ["Código Fonte", "Documento de Arquitetura"],
        "outputs": ["Relatório de Segurança", "Correções Implementadas"],
        "quality_gate": "0 vulnerabilidades críticas/altas, conformidade verificada",
        "cli_args": ["--input"],
    },
    "devops": {
        "name": "DevOps e Infraestrutura",
        "skill": "cp-devops",
        "description": "CI/CD, infraestrutura como código, monitoramento, deploy.",
        "agents": ["Eng. CI/CD", "Eng. Infraestrutura",
                    "Eng. Monitoramento", "Eng. Segurança Infra"],
        "inputs": ["Código Fonte", "Documento de Arquitetura", "Requisitos Não-Funcionais"],
        "outputs": ["Pipeline CI/CD", "Infraestrutura Provisionada", "Monitoramento Ativo"],
        "quality_gate": "Pipeline CI/CD verde, deploy automatizado validado, monitoramento operacional",
        "cli_args": ["--input"],
    },
    "documentacao": {
        "name": "Documentação de Software",
        "skill": "cp-documentacao",
        "description": "Gera documentação técnica, de API, de usuário e diagramas.",
        "agents": ["Redator Técnico", "Redator de Usuário", "Diagramador", "Revisor"],
        "inputs": ["Código Fonte", "Documento de Arquitetura", "Contratos de API"],
        "outputs": ["README.md", "Documentação de API", "Manual do Usuário", "Diagramas"],
        "quality_gate": "Documentação completa, clara e consistente com o código implementado",
        "cli_args": ["--input"],
    },
    "qualidade": {
        "name": "Qualidade de Software",
        "skill": "cp-qualidade",
        "description": "Auditoria final: métricas, artefatos, melhoria contínua.",
        "agents": ["Auditor de Qualidade", "Analista de Métricas",
                    "Eng. Melhoria Contínua", "Validador de Artefatos"],
        "inputs": ["Todos os artefatos do pipeline"],
        "outputs": ["Relatório de Qualidade", "Certificado de Qualidade"],
        "quality_gate": "Todos os quality gates anteriores PASS, artefatos completos e consistentes",
        "cli_args": ["--input"],
    },
    # ── Skills complementares (acionáveis pelo orquestrador) ──
    "bug-fix": {
        "name": "Correção de Bug (NEXUS-Micro)",
        "skill": "cp-bug-fix",
        "description": "Corrige bugs com crew Developer → QA → Evidence Collector (máx. 3 retries).",
        "agents": ["Developer", "QA (API Tester)", "Test Automation Engineer", "Evidence Collector"],
        "inputs": ["Descrição do bug"],
        "outputs": ["Correção implementada", "Testes automatizados", "Evidências"],
        "quality_gate": "Bug corrigido, testes passando, evidências coletadas",
        "cli_args": ["--type"],
        "invoke": {"briefing_arg": "positional", "output": False},
    },
    "competitive-analysis": {
        "name": "Análise Competitiva",
        "skill": "cp-competitive-analysis",
        "description": "Analisa concorrentes, features, preços, posicionamento e estratégia de mercado.",
        "agents": ["Analista de Mercado", "Analista de Competidores",
                    "Analista de Pricing/Posicionamento", "Estrategista"],
        "inputs": ["Contexto: produto, concorrentes, indústria"],
        "outputs": ["Relatório de Inteligência Competitiva", "Battle Cards", "SWOT"],
        "quality_gate": "Relatório completo com dados de concorrentes e recomendações estratégicas",
        "cli_args": ["--input"],
        "invoke": {"briefing_arg": "positional", "output": True},
    },
    "goal-loop": {
        "name": "Loop Autônomo de Tentativa-e-Correção",
        "skill": "cp-goal-loop",
        "description": "Executa um processo até atingir a condição de sucesso, corrigindo bloqueios no caminho.",
        "agents": ["Executor", "Diagnosticador", "Corretor", "Validador"],
        "inputs": ["Objetivo (--goal)", "Passos (--steps)"],
        "outputs": ["Processo concluído com sucesso", "Log de tentativas"],
        "quality_gate": "Condição de sucesso atingida dentro do limite de tentativas",
        "cli_args": ["--goal", "--steps", "--max-attempts", "--max-time"],
        "invoke": {"briefing_arg": "goal", "output": False},
    },
    "manutencao": {
        "name": "Manutenção e Evolução de Software",
        "skill": "cp-manutencao",
        "description": "Diagnostica bugs, implementa correções, refatora código e avalia impacto.",
        "agents": ["Analista de Bugs", "Desenvolvedor de Correção",
                    "Engenheiro de Refatoração", "Analista de Impacto"],
        "inputs": ["Descrição do bug / melhoria / refatoração"],
        "outputs": ["Correções implementadas", "Código refatorado", "Relatório de impacto"],
        "quality_gate": "Correção/refatoração validada sem regressões",
        "cli_args": ["--mode"],
        "invoke": {"briefing_arg": "positional", "output": True},
    },
    "agilista": {
        "name": "Agilista (Esteira de Execução)",
        "skill": "cp-agilista",
        "description": "Monitora o backlog, despacha tarefas prontas para o orquestrador e gerencia o loop bidirecional de feedback (dúvidas, impedimentos, retomada).",
        "agents": ["CPAgilistaDaemon", "CPAgilistaFeedbackLoop", "TrelloIntegration", "LocalIntegration"],
        "inputs": ["Backlog (local .context/kanban/ ou Trello)"],
        "outputs": ["Tarefas despachadas (TASK_DISPATCHED)", "Dúvidas/Impedimentos registrados", "Retomadas (HUMAN_CLARIFICATION_RECEIVED)"],
        "quality_gate": "Tarefas prontas despachadas, feedback bidirecional operacional",
        "cli_args": ["--daemon", "--source", "--duvida", "--impedimento", "--resume"],
        "invoke": {"briefing_arg": "daemon", "output": False},
    },
    "inicializador-doc": {
        "name": "Inicializador de Documentação",
        "skill": "cp-inicializador-doc",
        "description": "Centraliza o contexto do projeto em .context/ (fonte de verdade única), cria ponteiros CLAUDE.md/AGENT.md e gera a estrutura de documentação por disciplina.",
        "agents": ["InicializadorDoc"],
        "inputs": ["Diretório do projeto"],
        "outputs": [".context/ (docs, inbox, tracking)", "CLAUDE.md", "AGENT.md"],
        "quality_gate": "Estrutura .context/ criada, ponteiros na raiz, vision.md ingerido",
        "cli_args": ["--dir", "--dry-run"],
        "invoke": {"briefing_arg": "dir", "output": False},
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# MODOS DO PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

MODOS = {
    "full": {
        "name": "Completo",
        "description": "Executa todas as 8 crews em sequência — do requisito à entrega",
        "crews": ["requisitos", "arquitetura", "implementacao", "testes",
                   "seguranca", "devops", "documentacao", "qualidade"],
    },
    "sprint": {
        "name": "Sprint",
        "description": "Executa 5 crews — requisitos → arquitetura → implementação → testes → devops",
        "crews": ["requisitos", "arquitetura", "implementacao", "testes", "devops"],
    },
    "micro": {
        "name": "Micro (Bug Fix)",
        "description": "Executa 2 crews — implementação → testes (para correções rápidas)",
        "crews": ["implementacao", "testes"],
    },
    "security-audit": {
        "name": "Auditoria de Segurança",
        "description": "Executa 2 crews — segurança → qualidade",
        "crews": ["seguranca", "qualidade"],
    },
    "documentation": {
        "name": "Documentação",
        "description": "Executa 2 crews — documentação → qualidade",
        "crews": ["documentacao", "qualidade"],
    },
    "bugfix": {
        "name": "Correção de Bug",
        "description": "Executa a crew cp-bug-fix (Developer → QA → Evidence Collector)",
        "crews": ["bug-fix"],
    },
    "competitive": {
        "name": "Análise Competitiva",
        "description": "Executa a crew cp-competitive-analysis (inteligência competitiva)",
        "crews": ["competitive-analysis"],
    },
    "full-dev": {
        "name": "Pipeline NEXUS Completo",
        "description": "Executa o pipeline NEXUS nativo (Discovery → ... → Operate), merge de cp-full-dev",
        "crews": ["full-dev"],
    },
    "goal-loop": {
        "name": "Loop Autônomo",
        "description": "Executa a skill cp-goal-loop (tentativa-e-correção até sucesso)",
        "crews": ["goal-loop"],
    },
    "manutencao": {
        "name": "Manutenção e Evolução",
        "description": "Executa a crew cp-manutencao (bug-fix/refactor/improvement/full)",
        "crews": ["manutencao"],
    },
    "agilista": {
        "name": "Agilista (Esteira de Execução)",
        "description": "Executa a skill cp-agilista (daemon de polling + feedback loop)",
        "crews": ["agilista"],
    },
    "inicializador-doc": {
        "name": "Inicializador de Documentação",
        "description": "Executa a skill cp-inicializador-doc (estrutura .context/ + ponteiros)",
        "crews": ["inicializador-doc"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE NEXUS (merge de cp-full-dev) — agentes embutidos
# ═══════════════════════════════════════════════════════════════════════════

NEXUS_AGENTS = {
    # ── Engineering ──
    "engineering-backend-architect": {
        "role": "Backend Architect",
        "goal": "Design and implement scalable, secure, and performant backend systems",
        "backstory": "Senior backend architect specializing in scalable system design, database architecture, API development, and cloud infrastructure. Strategic, security-focused, scalability-minded.",
    },
    "engineering-frontend-developer": {
        "role": "Frontend Developer",
        "goal": "Build responsive, accessible, and performant web applications",
        "backstory": "Expert frontend developer specializing in modern web technologies, React/Vue/Angular, UI implementation, and performance optimization. Detail-oriented and user-centric.",
    },
    "engineering-ai-engineer": {
        "role": "AI Engineer",
        "goal": "Design and implement AI/ML solutions that integrate with the application",
        "backstory": "AI/ML engineer specializing in LLM integration, RAG pipelines, and intelligent automation. Experienced in production AI systems.",
    },
    "engineering-devops-automator": {
        "role": "DevOps Automator",
        "goal": "Automate infrastructure, CI/CD, and deployment pipelines",
        "backstory": "DevOps specialist who automates everything. Expert in CI/CD, containerization, cloud infrastructure, and infrastructure as code.",
    },
    "engineering-mobile-app-builder": {
        "role": "Mobile App Builder",
        "goal": "Build cross-platform mobile applications",
        "backstory": "Mobile developer specializing in React Native and Flutter. Builds performant, native-feeling mobile apps.",
    },
    "engineering-senior-developer": {
        "role": "Senior Developer",
        "goal": "Implement premium, production-ready features with high quality",
        "backstory": "Senior full-stack developer who creates premium web experiences. Creative, detail-oriented, performance-focused, and innovation-driven.",
    },
    "engineering-rapid-prototyper": {
        "role": "Rapid Prototyper",
        "goal": "Quickly build functional prototypes to validate ideas",
        "backstory": "Rapid prototyping specialist who builds functional MVPs fast. Focuses on speed-to-validation over polish.",
    },

    # ── Testing ──
    "testing-api-tester": {
        "role": "API Tester",
        "goal": "Validate APIs through comprehensive functional, security, and performance testing",
        "backstory": "Expert API testing specialist focused on comprehensive API validation. Thorough, security-conscious, automation-driven. Breaks APIs before users do.",
    },
    "testing-test-automation-engineer": {
        "role": "Test Automation Engineer",
        "goal": "Create deterministic, reliable automated test suites",
        "backstory": "Expert end-to-end test automation engineer. Allergic to sleep(), obsessive about root causes. Every test owns its data and waits on conditions, not clocks.",
    },
    "testing-evidence-collector": {
        "role": "Evidence Collector",
        "goal": "Verify quality with visual evidence — screenshots, logs, test output",
        "backstory": "Skeptical QA specialist who requires visual proof. Screenshots don't lie. Default to finding issues — first implementations always have 3-5+ issues.",
    },
    "testing-performance-benchmarker": {
        "role": "Performance Benchmarker",
        "goal": "Measure and validate system performance under load",
        "backstory": "Performance testing specialist who benchmarks systems under realistic load. Identifies bottlenecks and validates SLAs.",
    },
    "testing-reality-checker": {
        "role": "Reality Checker",
        "goal": "Validate that plans and implementations are realistic and achievable",
        "backstory": "Pragmatic validator who checks if plans are realistic. Questions assumptions, identifies risks, and ensures feasibility before commitment.",
    },
    "testing-test-results-analyzer": {
        "role": "Test Results Analyzer",
        "goal": "Analyze test results and provide actionable insights",
        "backstory": "Analytical QA who digs into test results to find patterns, regressions, and improvement opportunities.",
    },
    "testing-tool-evaluator": {
        "role": "Tool Evaluator",
        "goal": "Evaluate and recommend tools, frameworks, and technologies",
        "backstory": "Technology assessment specialist who evaluates tools against project requirements. Objective, data-driven recommendations.",
    },
    "testing-workflow-optimizer": {
        "role": "Workflow Optimizer",
        "goal": "Optimize development workflows for efficiency and quality",
        "backstory": "Process improvement specialist who identifies bottlenecks and optimizes workflows. Focuses on reducing cycle time and improving quality.",
    },

    # ── Design ──
    "design-ux-architect": {
        "role": "UX Architect",
        "goal": "Design intuitive, accessible user experiences",
        "backstory": "UX architect who designs user-centered interfaces. Expert in information architecture, user flows, and accessibility (WCAG).",
    },
    "design-ux-researcher": {
        "role": "UX Researcher",
        "goal": "Conduct user research to inform design decisions",
        "backstory": "UX researcher who gathers user insights through interviews, surveys, and usability testing. Data-driven design advocate.",
    },
    "design-ui-designer": {
        "role": "UI Designer",
        "goal": "Create beautiful, consistent, and accessible user interfaces",
        "backstory": "UI designer who creates pixel-perfect interfaces. Expert in design systems, typography, color theory, and visual hierarchy.",
    },
    "design-brand-guardian": {
        "role": "Brand Guardian",
        "goal": "Ensure brand consistency across all touchpoints",
        "backstory": "Brand guardian who protects and enforces brand identity. Ensures visual and tonal consistency across all outputs.",
    },

    # ── Product ──
    "product-trend-researcher": {
        "role": "Trend Researcher",
        "goal": "Research market trends and competitive landscape",
        "backstory": "Market researcher who identifies trends, competitive moves, and opportunities. Data-driven and forward-looking.",
    },
    "product-feedback-synthesizer": {
        "role": "Feedback Synthesizer",
        "goal": "Synthesize user feedback into actionable product insights",
        "backstory": "Product insights specialist who distills user feedback into prioritized, actionable recommendations.",
    },
    "product-sprint-prioritizer": {
        "role": "Sprint Prioritizer",
        "goal": "Prioritize backlog items based on value, effort, and dependencies",
        "backstory": "Agile prioritization specialist who balances business value, technical effort, and dependencies to optimize sprint planning.",
    },
    "product-manager": {
        "role": "Product Manager",
        "goal": "Define product vision, strategy, and roadmap",
        "backstory": "Product manager who defines what to build and why. Balances user needs, business goals, and technical feasibility.",
    },

    # ── Project Management ──
    "project-management-studio-producer": {
        "role": "Studio Producer",
        "goal": "Coordinate project execution across teams and phases",
        "backstory": "Project coordinator who keeps teams aligned, tracks progress, and removes blockers. Ensures smooth execution.",
    },
    "project-manager-senior": {
        "role": "Senior Project Manager",
        "goal": "Manage complex projects from planning to delivery",
        "backstory": "Senior project manager with expertise in agile and waterfall methodologies. Risk management and stakeholder communication specialist.",
    },

    # ── Marketing ──
    "marketing-growth-hacker": {
        "role": "Growth Hacker",
        "goal": "Drive user acquisition and growth through creative strategies",
        "backstory": "Growth marketing specialist who experiments with channels and tactics to drive measurable user growth.",
    },
    "marketing-content-creator": {
        "role": "Content Creator",
        "goal": "Create compelling marketing content across channels",
        "backstory": "Content marketing specialist who creates engaging copy, blog posts, and marketing materials that convert.",
    },
    "marketing-social-media-strategist": {
        "role": "Social Media Strategist",
        "goal": "Develop and execute social media strategies",
        "backstory": "Social media strategist who builds brand presence across platforms. Data-driven content planning and community management.",
    },
    "marketing-twitter-engager": {
        "role": "Twitter Engager",
        "goal": "Build Twitter/X presence and engagement",
        "backstory": "Twitter/X specialist who grows following, drives engagement, and builds thought leadership on the platform.",
    },
    "marketing-tiktok-strategist": {
        "role": "TikTok Strategist",
        "goal": "Create TikTok content strategy for brand awareness",
        "backstory": "TikTok content strategist who creates viral-worthy content and builds brand presence on the platform.",
    },
    "marketing-instagram-curator": {
        "role": "Instagram Curator",
        "goal": "Curate Instagram content for brand storytelling",
        "backstory": "Instagram content curator who builds visual brand storytelling through feeds, stories, and reels.",
    },
    "marketing-reddit-community-builder": {
        "role": "Reddit Community Builder",
        "goal": "Build and engage Reddit communities around the brand",
        "backstory": "Reddit community manager who builds authentic engagement in relevant subreddits without being spammy.",
    },

    # ── Support ──
    "support-analytics-reporter": {
        "role": "Analytics Reporter",
        "goal": "Track, analyze, and report key metrics and KPIs",
        "backstory": "Data analyst who builds dashboards and reports. Turns raw data into actionable insights for decision-making.",
    },
    "support-executive-summary-generator": {
        "role": "Executive Summary Generator",
        "goal": "Create concise executive summaries of project status and outcomes",
        "backstory": "Executive communicator who distills complex project information into clear, actionable summaries for leadership.",
    },
    "support-finance-tracker": {
        "role": "Finance Tracker",
        "goal": "Track project costs, budget, and financial metrics",
        "backstory": "Financial analyst who monitors project budgets, tracks costs, and forecasts financial outcomes.",
    },
    "support-infrastructure-maintainer": {
        "role": "Infrastructure Maintainer",
        "goal": "Maintain and monitor production infrastructure",
        "backstory": "Infrastructure engineer who keeps systems running. Monitoring, alerting, incident response, and capacity planning.",
    },
    "support-legal-compliance-checker": {
        "role": "Legal Compliance Checker",
        "goal": "Ensure legal and regulatory compliance across the project",
        "backstory": "Compliance specialist who reviews projects for legal and regulatory requirements. GDPR, LGPD, SOC2, and industry-specific regulations.",
    },
    "support-support-responder": {
        "role": "Support Responder",
        "goal": "Provide user support and triage issues",
        "backstory": "Customer support specialist who handles user inquiries, triages issues, and ensures timely resolution.",
    },

    # ── Specialized ──
    "specialized-agents-orchestrator": {
        "role": "Agents Orchestrator",
        "goal": "Coordinate multiple specialized agents for complex tasks",
        "backstory": "Orchestration specialist who coordinates multiple AI agents to work together efficiently on complex, multi-step tasks.",
    },
}


def nexus_get_agent(slug: str):
    """Get a CrewAI Agent from the embedded NEXUS definitions."""
    from crewai import Agent
    _crew_llm = build_crew_llm()
    data = NEXUS_AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agent not found: {slug} — using defaults")
        return Agent(
            role=name,
            goal=f"Complete the assigned task with excellence as {name}",
            backstory=f"Specialized AI agent working as {name}.",
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
# PIPELINE NEXUS — fases
# ═══════════════════════════════════════════════════════════════════════════

NEXUS_PHASES = {
    "full": {
        "phase-0-discovery": {
            "name": "Discovery",
            "agents": [
                "product-trend-researcher",
                "product-feedback-synthesizer",
                "design-ux-researcher",
                "support-analytics-reporter",
                "support-legal-compliance-checker",
                "testing-tool-evaluator",
            ],
            "gate_keeper": "support-executive-summary-generator",
            "description": "Validate the opportunity before committing resources",
        },
        "phase-1-strategy": {
            "name": "Strategy",
            "agents": [
                "project-management-studio-producer",
                "design-brand-guardian",
                "support-finance-tracker",
                "design-ux-architect",
                "engineering-backend-architect",
                "engineering-ai-engineer",
                "project-manager-senior",
                "product-sprint-prioritizer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Define what to build, how, and what success looks like",
        },
        "phase-2-foundation": {
            "name": "Foundation",
            "agents": [
                "engineering-devops-automator",
                "support-infrastructure-maintainer",
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "design-ux-architect",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Build the technical and operational foundation",
        },
        "phase-3-build": {
            "name": "Build",
            "agents": [
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "engineering-ai-engineer",
                "engineering-mobile-app-builder",
                "engineering-senior-developer",
                "engineering-rapid-prototyper",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-automation-engineer",
                "testing-performance-benchmarker",
                "design-ui-designer",
                "design-brand-guardian",
            ],
            "gate_keeper": "specialized-agents-orchestrator",
            "description": "Implement features through Dev-QA loops",
        },
        "phase-4-hardening": {
            "name": "Hardening",
            "agents": [
                "testing-reality-checker",
                "testing-evidence-collector",
                "testing-performance-benchmarker",
                "testing-api-tester",
                "testing-test-results-analyzer",
                "support-legal-compliance-checker",
                "support-infrastructure-maintainer",
                "testing-workflow-optimizer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Final quality gauntlet before production",
        },
        "phase-5-launch": {
            "name": "Launch",
            "agents": [
                "marketing-growth-hacker",
                "marketing-content-creator",
                "marketing-social-media-strategist",
                "marketing-twitter-engager",
                "marketing-tiktok-strategist",
                "marketing-instagram-curator",
                "marketing-reddit-community-builder",
                "engineering-devops-automator",
                "support-infrastructure-maintainer",
                "support-support-responder",
                "support-analytics-reporter",
                "support-executive-summary-generator",
            ],
            "gate_keeper": "project-management-studio-producer",
            "description": "Coordinate go-to-market execution",
        },
        "phase-6-operate": {
            "name": "Operate",
            "agents": [
                "support-analytics-reporter",
                "support-infrastructure-maintainer",
                "support-support-responder",
                "engineering-devops-automator",
                "product-feedback-synthesizer",
                "product-sprint-prioritizer",
                "support-finance-tracker",
                "support-legal-compliance-checker",
                "support-executive-summary-generator",
            ],
            "gate_keeper": "project-management-studio-producer",
            "description": "Sustained operations with continuous improvement",
        },
    },
    "sprint": {
        "phase-1-strategy": {
            "name": "Strategy",
            "agents": [
                "project-manager-senior",
                "product-sprint-prioritizer",
                "design-ux-architect",
                "engineering-backend-architect",
                "design-brand-guardian",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Define architecture and sprint plan",
        },
        "phase-2-foundation": {
            "name": "Foundation",
            "agents": [
                "engineering-devops-automator",
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "design-ux-architect",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Scaffold the feature foundation",
        },
        "phase-3-build": {
            "name": "Build",
            "agents": [
                "engineering-frontend-developer",
                "engineering-backend-architect",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-automation-engineer",
            ],
            "gate_keeper": "specialized-agents-orchestrator",
            "description": "Implement the feature with Dev-QA loops",
        },
        "phase-4-hardening": {
            "name": "Hardening",
            "agents": [
                "testing-reality-checker",
                "testing-evidence-collector",
                "testing-api-tester",
                "testing-test-results-analyzer",
            ],
            "gate_keeper": "testing-reality-checker",
            "description": "Quality validation before merge",
        },
    },
    "micro": {
        "phase-3-build": {
            "name": "Build & Fix",
            "agents": [
                "engineering-backend-architect",
                "engineering-frontend-developer",
                "testing-api-tester",
                "testing-test-automation-engineer",
                "testing-evidence-collector",
            ],
            "gate_keeper": "testing-evidence-collector",
            "description": "Implement and validate the change",
        },
    },
}


def nexus_detect_mode(requirement: str) -> str:
    """Detect the NEXUS mode based on requirement scope."""
    req_lower = requirement.lower()

    full_keywords = [
        "construir", "criar do zero", "produto completo", "sistema completo",
        "aplicativo", "plataforma", "do zero", "build from scratch",
        "sistema de", "app de", "aplicacao", "aplicação",
    ]
    sprint_keywords = [
        "feature", "funcionalidade", "implementar", "adicionar", "criar um",
        "nova tela", "novo modulo", "novo módulo", "exportar", "importar",
        "relatorio", "relatório", "dashboard", "integracao", "integração",
    ]
    micro_keywords = [
        "corrigir", "bug", "erro", "fix", "ajuste", "ajustar", "mudar",
        "alterar", "trocar", "pequeno",
    ]

    full_score = sum(1 for kw in full_keywords if kw in req_lower)
    sprint_score = sum(1 for kw in sprint_keywords if kw in req_lower)
    micro_score = sum(1 for kw in micro_keywords if kw in req_lower)

    if full_score >= sprint_score and full_score >= micro_score:
        return "full"
    elif sprint_score >= micro_score:
        return "sprint"
    else:
        return "micro"


def nexus_build_phase_crew(phase_key: str, phase_def: dict, requirement: str, project_name: str):
    """Build a CrewAI crew for a single NEXUS phase."""
    from crewai import Task, Crew, Process

    agents = []
    tasks = []

    for slug in phase_def["agents"]:
        agents.append(nexus_get_agent(slug))

    gate_keeper = nexus_get_agent(phase_def["gate_keeper"])

    phase_task = Task(
        description=f"""
        PROJECT: {project_name}
        REQUIREMENT: {requirement}
        PHASE: {phase_def['name']} — {phase_def['description']}

        YOUR JOB:
        Execute this phase of the NEXUS pipeline. Each agent contributes their
        specialized expertise to produce the deliverables for this phase.

        Coordinate with each other. Produce concrete, actionable outputs.
        Document all decisions and rationale.

        When all agents have completed their work, produce a consolidated
        phase deliverable package.
        """,
        expected_output=f"Phase {phase_def['name']} deliverable package with all agent outputs consolidated",
        agent=agents[0],
    )

    gate_task = Task(
        description=f"""
        PROJECT: {project_name}
        PHASE: {phase_def['name']}

        YOUR JOB — QUALITY GATE:
        Review the phase deliverables from all agents.
        Verify that the phase objectives were met.

        Issue verdict: PASS or FAIL.

        If PASS: the project can advance to the next phase.
        If FAIL: provide specific issues that must be addressed before retry.

        Evidence required — no assertions without proof.
        """,
        expected_output=f"Quality gate verdict for Phase {phase_def['name']}: PASS/FAIL with evidence",
        agent=gate_keeper,
    )

    crew = Crew(
        agents=agents + [gate_keeper],
        tasks=[phase_task, gate_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


class NexusExecutor:
    """Executa o pipeline NEXUS nativamente (merge de cp-full-dev)."""

    def __init__(self, requirement: str, mode: str = "auto", start_phase: str = None,
                 project_name: str = None, output_dir: str = None,
                 kanban_task: str = None, python_cmd: str = None):
        self.requirement = requirement
        self.mode = mode if mode != "auto" else nexus_detect_mode(requirement)
        self.start_phase = start_phase
        self.project_name = project_name or requirement[:60].strip()
        self.output_dir = output_dir
        self.kanban_task = kanban_task
        self.python_cmd = python_cmd or sys.executable

    def run(self) -> dict:
        phases = NEXUS_PHASES.get(self.mode, NEXUS_PHASES["micro"])
        phase_keys = list(phases.keys())

        # Kanban: marca como doing no inicio
        if self.kanban_task:
            self._kanban_update_status("doing")

        if self.start_phase:
            if self.start_phase in phase_keys:
                idx = phase_keys.index(self.start_phase)
                phase_keys = phase_keys[idx:]
            else:
                print(f"[!] Fase nao encontrada: {self.start_phase}")
                print(f"    Fases disponiveis: {', '.join(phase_keys)}")
                return {"status": "failed", "error": f"Fase '{self.start_phase}' não encontrada"}

        print(f"\n{'='*60}")
        print(f"  NEXUS Pipeline — Modo: {self.mode.upper()} (nativo no orquestrador)")
        print(f"  Projeto: {self.project_name}")
        print(f"  Fases: {len(phase_keys)}")
        print(f"{'='*60}\n")

        total_agents = 0
        for i, pk in enumerate(phase_keys):
            phase = phases[pk]
            total_agents += len(phase["agents"])
            print(f"  Fase {i}: {phase['name']} ({len(phase['agents'])} agentes)")
            print(f"    Gate: {phase['gate_keeper']}")
            print(f"    {phase['description']}")
            print()

        print(f"  Total: {total_agents} agentes em {len(phase_keys)} fases\n")

        results = {}
        failed_phase = None
        for i, pk in enumerate(phase_keys):
            phase = phases[pk]
            print(f"\n{'='*60}")
            print(f"  FASE {i+1}/{len(phase_keys)}: {phase['name']}")
            print(f"  {phase['description']}")
            print(f"{'='*60}\n")

            try:
                require_llm()  # DT-08: falha cedo, com mensagem, se nao ha LLM
                crew = nexus_build_phase_crew(pk, phase, self.requirement, self.project_name)
                print(f"  [>] Executando {len(phase['agents'])} agentes...")
                result = crew.kickoff()
                results[pk] = {
                    "status": "completed",
                    "phase": phase["name"],
                    "result": str(result)[:500],
                }
                print(f"  [OK] Fase {phase['name']} concluida")
            except Exception as e:
                print(f"  [!!] Fase {phase['name']} falhou: {e}")
                results[pk] = {
                    "status": "failed",
                    "phase": phase["name"],
                    "error": str(e),
                }
                failed_phase = pk
                print("\n  A fase falhou. Corrija o erro e re-execute com --start-phase")
                break

        print(f"\n{'='*60}")
        print(f"  PIPELINE CONCLUIDO")
        print(f"{'='*60}\n")
        for pk, r in results.items():
            status_icon = "[OK]" if r["status"] == "completed" else "[!!]"
            print(f"  {status_icon} {r['phase']}: {r['status']}")

        completed = sum(1 for r in results.values() if r["status"] == "completed")
        print(f"\n  {completed}/{len(phase_keys)} fases concluidas")

        # Salva resultados
        if self.output_dir:
            out_dir = Path(self.output_dir)
        else:
            out_dir = ORQUESTRADOR_DIR / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = out_dir / f"nexus_{self.mode}_{timestamp}.json"
        output_file.write_text(json.dumps({
            "project": self.project_name,
            "requirement": self.requirement,
            "mode": self.mode,
            "timestamp": timestamp,
            "phases": results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Resultados salvos em: {output_file}")

        # Kanban: marca como done ou blocked ao final
        if self.kanban_task:
            if failed_phase:
                self._kanban_update_status("blocked")
            else:
                self._kanban_update_status("done")

        return {
            "status": "failed" if failed_phase else "completed",
            "mode": self.mode,
            "failed_phase": failed_phase,
            "completed": completed,
            "total": len(phase_keys),
            "output_file": str(output_file),
        }

    def _kanban_update_status(self, status: str):
        """Atualiza o status da task kanban via cp-agilista (best-effort)."""
        if not self.kanban_task:
            return
        agilista_run = SKILL_PATHS.get("agilista")
        if not agilista_run or not agilista_run.exists():
            return
        try:
            subprocess.run(
                [self.python_cmd, str(agilista_run),
                 "--task", self.kanban_task,
                 "--update-status", status],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# MODO AUTO — EXECUTOR DE PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

class PipelineExecutor:
    """Executa o pipeline real chamando as skills via subprocess."""

    def __init__(self, briefing: str, mode: str, start_phase: str = None,
                 output_dir: str = None, python_cmd: str = None,
                 kanban_task: str = None):
        self.briefing = briefing
        self.mode = mode
        self.start_phase = start_phase
        self.python_cmd = python_cmd or sys.executable
        self.kanban_task = kanban_task  # ID da task no kanban (cp-agilista)

        # Resolve diretório de artefatos
        if output_dir:
            self.artifacts_dir = Path(output_dir)
        else:
            self.artifacts_dir = ORQUESTRADOR_DIR / "outputs" / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Estado do pipeline
        self.artifacts = {}  # fase -> caminho do artefato
        self.gate_results = {}  # fase -> {"status": "PASS"/"FAIL"/"WARN", "detail": "..."}
        self.phase_outputs = {}  # fase -> texto completo da saída
        self.timing = {}  # fase -> segundos
        self.failed_phase = None

    def _get_skill_path(self, crew_key: str) -> Path:
        """Retorna o caminho do script run.py da skill."""
        return SKILL_PATHS.get(crew_key)

    def _get_artifact_path(self, crew_key: str) -> Path:
        """Retorna o caminho onde o artefato da fase será salvo."""
        return self.artifacts_dir / f"{crew_key}.md"

    def _get_previous_artifact(self, crew_key: str) -> str:
        """Retorna o conteúdo do artefato da fase anterior, se existir."""
        # Mapeia qual fase anterior alimenta esta
        prev_map = {
            "arquitetura": "requisitos",
            "implementacao": "arquitetura",
            "testes": "implementacao",
            "seguranca": "implementacao",
            "devops": "implementacao",
            "documentacao": "implementacao",
            "qualidade": None,  # recebe de todas
        }
        prev_key = prev_map.get(crew_key)
        if prev_key and prev_key in self.artifacts:
            path = self.artifacts[prev_key]
            if path and path.exists():
                return path.read_text(encoding="utf-8")[:2000]  # contexto limitado
        return ""

    def _build_cli_args(self, crew_key: str) -> list:
        """Monta os argumentos CLI para chamar a skill.

        Respeita o metadado `invoke` de cada crew:
          briefing_arg: "positional" (passa briefing como arg posicional),
                        "goal" (passa via --goal, ex.: cp-goal-loop),
                        "input" (passa via --input, ex.: fases do pipeline)
          output:       True se a skill aceita --output, False caso contrário
        """
        crew = CREWS[crew_key]
        skill_path = self._get_skill_path(crew_key)

        if not skill_path or not skill_path.exists():
            print(f"  ⚠️  Skill não encontrada: {crew['skill']} em {skill_path}")
            print(f"     Pulando fase {crew['name']}...")
            return None

        invoke = crew.get("invoke", {"briefing_arg": "input", "output": True})
        briefing_arg = invoke.get("briefing_arg", "input")
        supports_output = invoke.get("output", True)

        args = [str(self.python_cmd), str(skill_path)]

        # Briefing ou artefato anterior como input
        prev_artifact = self._get_previous_artifact(crew_key)
        if prev_artifact:
            # Salva contexto temporário e passa como --input
            ctx_file = self.artifacts_dir / f"_ctx_{crew_key}.txt"
            ctx_file.write_text(
                f"# Contexto para {crew['name']}\n\n"
                f"Briefing original: {self.briefing}\n\n"
                f"Artefato da fase anterior:\n{prev_artifact[:3000]}",
                encoding="utf-8"
            )
            args.extend(["--input", str(ctx_file)])
        else:
            # Primeira fase: passa o briefing conforme o modo de invocação
            if briefing_arg == "goal":
                args.extend(["--goal", self.briefing])
            elif briefing_arg == "daemon":
                # Agilista: inicia o daemon de polling (sempre lê do local)
                args.extend(["--daemon"])
            elif briefing_arg == "dir":
                # Inicializador-doc: usa o diretório atual (sem briefing posicional)
                args.extend(["--dir", str(Path.cwd())])
            elif briefing_arg == "positional":
                args.append(self.briefing)
            else:  # "input"
                args.append(self.briefing)

        # --output (apenas se a skill suportar)
        if supports_output:
            out_path = self._get_artifact_path(crew_key)
            args.extend(["--output", str(out_path)])

        return args

    @staticmethod
    def _count_keywords(keywords: list, text_upper: str) -> int:
        """Conta keywords casando por PALAVRA INTEIRA.

        BUG-04: com `kw in text`, a keyword de sucesso "OK" casava dentro de
        "TOKEN" e "BROKEN" — e "invalid API token" (o erro mais comum quando
        falta credencial) era classificado como PASS.
        """
        return sum(1 for kw in keywords
                   if re.search(r"\b" + re.escape(kw) + r"\b", text_upper))

    def _check_quality_gate(self, crew_key: str, output_text: str,
                            returncode: int = 0) -> dict:
        """Analisa a saída da skill e determina se o quality gate passou."""
        # BUG-03: exit code != 0 e FAIL incondicional. Antes, uma skill que
        # morria com traceback nao continha nenhuma fail_keyword, caia no ramo
        # default (WARN) e o pipeline seguia reportando sucesso.
        if returncode != 0:
            return {"status": "FAIL",
                    "detail": f"Skill terminou com exit code {returncode}"}

        output_upper = output_text.upper()

        # Palavras-chave de falha
        fail_keywords = ["FAIL", "FALHOU", "REPROVADO", "NEGADO", "BLOQUEADO",
                         "CRÍTICO", "CRITICAL", "VULNERABILIDADE CRÍTICA",
                         "TRACEBACK", "MODULENOTFOUNDERROR"]
        # Palavras-chave de warning
        warn_keywords = ["WARN", "RESSALVA", "ATENÇÃO", "PENDENTE", "ALERTA"]
        # Palavras-chave de sucesso
        pass_keywords = ["PASS", "APROVADO", "SUCESSO", "CONCLUÍDO", "OK",
                         "ZERO VULNERABILIDADES", "COBERTURA"]

        fail_score = self._count_keywords(fail_keywords, output_upper)
        warn_score = self._count_keywords(warn_keywords, output_upper)
        pass_score = self._count_keywords(pass_keywords, output_upper)

        if fail_score > pass_score:
            return {"status": "FAIL", "detail": "Palavras-chave de falha detectadas na saída"}
        elif warn_score > 0 and pass_score == 0:
            return {"status": "WARN", "detail": "Ressalvas detectadas, sem confirmação de sucesso"}
        elif pass_score > 0:
            return {"status": "PASS", "detail": "Indicadores de sucesso detectados"}
        else:
            return {"status": "WARN", "detail": "Não foi possível determinar o resultado — revise manualmente"}

    # Mapeia crew -> arquivo de disciplina em .context/docs/
    CONTEXT_DOC_MAP = {
        "requisitos": "01-requisitos.md",
        "arquitetura": "02-arquitetura.md",
        "implementacao": "02-arquitetura.md",
        "testes": "04-qualidade-qa.md",
        "seguranca": "03-seguranca-lgpd.md",
        "devops": "05-devops-operacoes.md",
        "documentacao": "04-qualidade-qa.md",
        "qualidade": "04-qualidade-qa.md",
        "bug-fix": "04-qualidade-qa.md",
        "competitive-analysis": "01-requisitos.md",
        "goal-loop": "05-devops-operacoes.md",
        "manutencao": "02-arquitetura.md",
        "agilista": "06-kanban.md",
    }

    def _document_to_context(self, crew_key: str, output_text: str):
        """Documenta o artefato da fase em .context/docs/<disciplina>.md.

        Toda skill cp-* documenta seus artefatos na estrutura .context/ (fonte
        de verdade do projeto). O arquivo de disciplina é criado/atualizado com
        a saída da fase.
        """
        doc_file = self.CONTEXT_DOC_MAP.get(crew_key)
        if not doc_file:
            return None
        # .context/ fica na raiz do projeto (cwd do orquestrador)
        context_dir = Path.cwd() / ".context" / "docs"
        context_dir.mkdir(parents=True, exist_ok=True)
        dest = context_dir / doc_file

        crew = CREWS[crew_key]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = (
            f"\n\n## Artefato — {crew['name']} ({now})\n\n"
            f"```\n{output_text[:4000]}\n```\n"
        )
        # Se o arquivo já existe, anexa; senão cria com cabeçalho
        if dest.exists():
            dest.write_text(dest.read_text(encoding="utf-8") + block, encoding="utf-8")
        else:
            dest.write_text(
                f"# {crew['name']}\n\n> Documento gerido pela skill `{crew['skill']}`.\n"
                + block,
                encoding="utf-8",
            )
        return dest

    def _kanban_update_status(self, status: str):
        """Atualiza o status da task kanban via cp-agilista.

        Só executa se `self.kanban_task` foi informado.
        """
        if not self.kanban_task:
            return
        agilista_run = SKILL_PATHS.get("agilista")
        if not agilista_run or not agilista_run.exists():
            return
        try:
            subprocess.run(
                [self.python_cmd, str(agilista_run),
                 "--task", self.kanban_task,
                 "--update-status", status],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass  # best-effort: nao quebra o pipeline se kanban falhar

    def run(self) -> dict:
        """Executa o pipeline completo."""
        modo_info = MODOS[self.mode]
        crew_keys = modo_info["crews"]

        # Filtra por start_phase
        if self.start_phase:
            if self.start_phase in crew_keys:
                idx = crew_keys.index(self.start_phase)
                crew_keys = crew_keys[idx:]
            else:
                print(f"❌ Fase '{self.start_phase}' não encontrada no modo '{self.mode}'")
                print(f"   Fases disponíveis: {', '.join(crew_keys)}")
                return {"status": "failed", "error": f"Fase '{self.start_phase}' não encontrada"}

        print(f"\n{'='*60}")
        print(f"  🚀 PIPELINE AUTO — {modo_info['name']}")
        print(f"  {modo_info['description']}")
        print(f"  📁 Artefatos: {self.artifacts_dir}")
        if self.kanban_task:
            print(f"  📋 Kanban task: {self.kanban_task}")
        print(f"{'='*60}\n")

        # Se tem kanban_task, marca como doing no inicio
        if self.kanban_task:
            self._kanban_update_status("doing")

        for i, ck in enumerate(crew_keys, 1):
            crew = CREWS[ck]
            print(f"\n{'─'*50}")
            print(f"  📌 FASE {i}/{len(crew_keys)}: {crew['name']}")
            print(f"  🛠️  Skill: {crew['skill']}")
            print(f"  🎯 Quality Gate: {crew['quality_gate']}")
            print(f"{'─'*50}\n")

            # Monta argumentos
            args = self._build_cli_args(ck)
            if args is None:
                self.gate_results[ck] = {"status": "SKIP", "detail": "Skill não encontrada"}
                continue

            print(f"  🔧 Executando: {' '.join(str(a) for a in args)}")
            print()

            # Executa
            start_time = time.time()
            try:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 min por fase
                    cwd=str(SKILLS_DIR),
                )
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed

                output = result.stdout + "\n" + result.stderr
                self.phase_outputs[ck] = output

                # Salva artefato
                out_path = self._get_artifact_path(ck)
                out_path.write_text(output, encoding="utf-8")
                self.artifacts[ck] = out_path

                # Documenta o artefato em .context/docs/ (fonte de verdade)
                self._document_to_context(ck, output)

                # Quality gate
                gate = self._check_quality_gate(ck, output, result.returncode)
                self.gate_results[ck] = gate

                print(f"  ⏱️  {elapsed:.1f}s | Quality Gate: {gate['status']}")
                if gate["status"] == "FAIL":
                    print(f"  ❌ FASE {crew['name']} REPROVADA!")
                    print(f"     Motivo: {gate['detail']}")
                    self.failed_phase = ck
                    break
                elif gate["status"] == "WARN":
                    print(f"  ⚠️  Fase aprovada com ressalvas: {gate['detail']}")
                else:
                    print(f"  ✅ Fase concluída com sucesso!")

                # Mostra preview da saída
                preview = output[:500].strip()
                if preview:
                    print(f"\n  📄 Preview:\n{preview}\n")

            except subprocess.TimeoutExpired:
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed
                self.gate_results[ck] = {"status": "FAIL", "detail": "Timeout após 10 minutos"}
                print(f"  ⏰ Timeout após {elapsed:.0f}s")
                self.failed_phase = ck
                break

            except Exception as e:
                elapsed = time.time() - start_time
                self.timing[ck] = elapsed
                self.gate_results[ck] = {"status": "FAIL", "detail": f"Erro: {e}"}
                print(f"  ❌ Erro: {e}")
                self.failed_phase = ck
                break

        # Atualiza status kanban ao final do pipeline
        if self.kanban_task:
            if self.failed_phase:
                self._kanban_update_status("blocked")
            else:
                self._kanban_update_status("done")

        # Relatório final
        return self._generate_report(crew_keys)

    def _generate_report(self, crew_keys: list) -> dict:
        """Gera o relatório final do pipeline."""
        total = len(crew_keys)
        passed = sum(1 for g in self.gate_results.values() if g["status"] == "PASS")
        warned = sum(1 for g in self.gate_results.values() if g["status"] == "WARN")
        failed = sum(1 for g in self.gate_results.values() if g["status"] == "FAIL")
        skipped = sum(1 for g in self.gate_results.values() if g["status"] == "SKIP")
        total_time = sum(self.timing.values())

        report = {
            "status": "failed" if self.failed_phase else "completed",
            "mode": self.mode,
            "total_phases": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "skipped": skipped,
            "total_time_seconds": total_time,
            "failed_phase": self.failed_phase,
            "phases": {},
            "artifacts_dir": str(self.artifacts_dir),
        }

        for ck in crew_keys:
            crew = CREWS[ck]
            report["phases"][ck] = {
                "name": crew["name"],
                "skill": crew["skill"],
                "gate": self.gate_results.get(ck, {"status": "UNKNOWN", "detail": ""}),
                "time_seconds": self.timing.get(ck, 0),
                "artifact": str(self.artifacts.get(ck, "")),
            }

        # Imprime relatório
        print(f"\n{'='*60}")
        print(f"  📊 RELATÓRIO FINAL DO PIPELINE")
        print(f"{'='*60}\n")

        if self.failed_phase:
            print(f"  ❌ Pipeline interrompido na fase: {CREWS[self.failed_phase]['name']}")
        else:
            print(f"  ✅ Pipeline concluído com sucesso!")

        print(f"\n  📊 Dashboard:")
        print(f"     Fases: {total} | ✅ {passed} | ⚠️  {warned} | ❌ {failed} | ⏭️  {skipped}")
        print(f"     ⏱️  Tempo total: {total_time:.1f}s ({total_time/60:.1f}min)")
        print(f"     📁 Artefatos: {self.artifacts_dir}")

        print(f"\n  📋 Detalhamento por fase:")
        for ck in crew_keys:
            crew = CREWS[ck]
            gate = self.gate_results.get(ck, {"status": "UNKNOWN", "detail": ""})
            icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️", "UNKNOWN": "❓"}
            t = self.timing.get(ck, 0)
            print(f"     {icon.get(gate['status'], '❓')} {crew['name']} ({t:.1f}s)")
            if gate["detail"]:
                print(f"        {gate['detail']}")

        # Salva relatório
        report_file = self.artifacts_dir / "pipeline_report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  📄 Relatório salvo: {report_file}")

        return report


# ═══════════════════════════════════════════════════════════════════════════
# MODO SIMULAÇÃO — CrewAI (original)
# ═══════════════════════════════════════════════════════════════════════════

def build_simulation_crew(briefing: str, mode: str, start_phase: str = None):
    """Build a CrewAI crew for pipeline simulation/planning."""
    from crewai import Agent, Task, Crew, Process

    # ── Agentes embutidos ──
    AGENTS = {
        "orquestrador-de-pipeline": {
            "role": "Orquestrador de Pipeline",
            "goal": "Coordenar a execução sequencial de todas as crews especializadas",
            "backstory": (
                "Maestro de orquestra de software com 15 anos coordenando pipelines complexos. "
                "Você conhece cada instrumento (crew) da fábrica de software e sabe exatamente "
                "quando cada um deve tocar. Planeja a sequência, aloca recursos, define deadlines "
                "e monitora o progresso. Seu lema: 'Um pipeline bem orquestrado é uma sinfonia.'"
            ),
        },
        "gestor-de-artefatos": {
            "role": "Gestor de Artefatos",
            "goal": "Garantir que os outputs de cada crew sejam versionados e entregues como inputs da próxima fase",
            "backstory": (
                "Bibliotecário de software meticuloso que organiza e versiona cada artefato. "
                "Implementa versionamento semântico: requisitos_v1.2, arquitetura_v1.0. "
                "Mantém matriz de rastreabilidade ligando requisito → código → teste → doc. "
                "Seu lema: 'Um artefato sem versão é um artefato perdido.'"
            ),
        },
        "tomador-de-decisao": {
            "role": "Tomador de Decisão",
            "goal": "Analisar quality gates e decidir avanço, pausa ou retrocesso",
            "backstory": (
                "Gerente de projeto com 20 anos entregando software crítico. "
                "Analisa cada quality gate: PASS → avança, WARN → avança com ressalvas, "
                "FAIL → bloqueia e determina retrocesso. "
                "Seu lema: 'Qualidade sem entrega é arte; entrega sem qualidade é lixo.'"
            ),
        },
        "relator-de-progresso": {
            "role": "Relator de Progresso",
            "goal": "Gerar relatórios de status, dashboards e resumos executivos",
            "backstory": (
                "PM que transforma progresso técnico em relatórios que stakeholders entendem. "
                "Gera dashboard de progresso, resumo executivo, relatório técnico e log de decisões. "
                "Seu lema: 'Um relatório que ninguém lê é pior que nenhum relatório.'"
            ),
        },
    }

    def get_agent(slug):
        _crew_llm = build_crew_llm()
        data = AGENTS.get(slug)
        if not data:
            return Agent(role=slug, goal="Completar a tarefa", backstory="Agente especializado.",
                         llm=_crew_llm,
                         verbose=True, allow_delegation=False)
        return Agent(role=data["role"], goal=data["goal"], backstory=data["backstory"],
                     llm=_crew_llm,
                     verbose=True, allow_delegation=False)

    orquestrador = get_agent("orquestrador-de-pipeline")
    gestor = get_agent("gestor-de-artefatos")
    tomador = get_agent("tomador-de-decisao")
    relator = get_agent("relator-de-progresso")

    modo_info = MODOS[mode]
    crew_keys = modo_info["crews"]

    if start_phase:
        if start_phase in crew_keys:
            idx = crew_keys.index(start_phase)
            crew_keys = crew_keys[idx:]
        else:
            print(f"  [!] Fase '{start_phase}' não encontrada no modo '{mode}'")
            sys.exit(1)

    crews_info = []
    for ck in crew_keys:
        crew = CREWS[ck]
        crews_info.append(f"  {ck}: {crew['name']} ({crew['skill']})")
        crews_info.append(f"    Descrição: {crew['description']}")
        crews_info.append(f"    Agentes: {', '.join(crew['agents'])}")
        crews_info.append(f"    Inputs: {', '.join(crew['inputs'])}")
        crews_info.append(f"    Outputs: {', '.join(crew['outputs'])}")
        crews_info.append(f"    Quality Gate: {crew['quality_gate']}")
        crews_info.append("")
    crews_text = "\n".join(crews_info)

    task_planejamento = Task(
        description=f"""
BRIEFING: {briefing}
MODO: {modo_info['name']} — {modo_info['description']}
FASES: {', '.join(crew_keys)}

PLANEJAMENTO:
1. Analise o briefing e identifique o escopo
2. Para cada fase: objetivos, duração estimada, dependências, critérios de aceitação
3. Crie cronograma sequencial com marcos
4. Identifique riscos do pipeline

CREWS DISPONÍVEIS:
{crews_text}
""",
        expected_output="Plano completo do pipeline com cronograma, fases e riscos",
        agent=orquestrador,
    )

    task_execucao = Task(
        description=f"""
BRIEFING: {briefing}
MODO: {modo_info['name']}
FASES: {', '.join(crew_keys)}

EXECUÇÃO FASEADA:
Para CADA fase, documente:
1. Início: fase, skill, agentes, inputs recebidos
2. Execução: o que cada agente produz, decisões, problemas
3. Artefatos gerados: nome, versão, formato
4. Passagem de artefatos para próxima fase
5. Quality gate: PASS/WARN/FAIL com evidências

CREWS:
{crews_text}
""",
        expected_output="Execução completa do pipeline com artefatos e quality gates",
        agent=orquestrador,
    )

    task_decisoes = Task(
        description=f"""
BRIEFING: {briefing}
FASES: {', '.join(crew_keys)}

DECISÕES DE QUALITY GATE:
Para cada fase, decida:
1. ✅ AVANÇAR: fase aprovada
2. ⚠️ AVANÇAR COM RESSALVAS: aprovado com pendências
3. 🔄 RETROCEDER: fase reprovada
4. ⏸️ PAUSAR: pipeline pausado

Justifique cada decisão com impacto no cronograma e risco assumido.
""",
        expected_output="Decisões de quality gate com justificativas",
        agent=tomador,
    )

    task_relatorio = Task(
        description=f"""
BRIEFING: {briefing}
FASES: {', '.join(crew_keys)}

RELATÓRIO FINAL:
1. Resumo executivo (1 parágrafo)
2. Dashboard: fases concluídas/andamento/pendentes, gates PASS/WARN/FAIL
3. Detalhamento por fase com status e artefatos
4. Matriz de rastreabilidade (requisito → código → teste → doc)
5. Log de decisões
6. Métricas: artefatos, agentes, gates aprovados
7. Recomendações finais
""",
        expected_output="Relatório final completo do pipeline",
        agent=relator,
    )

    crew = Crew(
        agents=[orquestrador, gestor, tomador, relator],
        tasks=[task_planejamento, task_execucao, task_decisoes, task_relatorio],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-orquestrador: Orquestrador da Fábrica de Software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python run.py "sistema de agendamento para clínicas"
  python run.py "sistema de agendamento" --auto
  python run.py "feature de relatório PDF" --mode sprint --auto
  python run.py "corrigir erro de login" --mode micro --auto
  python run.py "app financeiro" --mode security-audit --auto
  python run.py --input briefing.txt --auto
  python run.py "sistema de estoque" --start-phase implementacao --auto
  python run.py "sistema de agendamento" --dry-run

Skills complementares (modos):
  python run.py "o endpoint /login retorna 500" --mode bugfix --auto
  python run.py "SaaS de clínicas; concorrentes: Doctoralia" --mode competitive --auto
  python run.py "sistema de agendamento" --mode full-dev --auto
  python run.py "deploy em staging funcionando" --mode goal-loop --auto
  python run.py "refatorar módulo de pagamentos" --mode manutencao --auto
        """,
    )
    parser.add_argument("briefing", nargs="?", help="Briefing do cliente / descrição do projeto")
    parser.add_argument("--input", "-i", dest="input_file", help="Arquivo com o briefing")
    parser.add_argument("--mode", "-m", choices=list(MODOS.keys()), default="full",
                        help="Modo do pipeline (default: full)")
    parser.add_argument("--output", "-o", default=None, help="Diretório de saída para artefatos")
    parser.add_argument("--start-phase", default=None,
                        help="Começar de uma fase específica (ex: implementacao)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas mostra o plano do pipeline, sem executar")
    parser.add_argument("--auto", action="store_true",
                        help="Modo automático: executa as crews reais em sequência")
    parser.add_argument("--python", default=None,
                        help="Caminho do interpretador Python (default: mesmo deste script)")
    parser.add_argument("--kanban-task", default=None,
                        help="ID da task no kanban (cp-agilista). Atualiza status durante a execução")
    args = parser.parse_args()

    # ── Resolve briefing ──
    briefing = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ Arquivo não encontrado: {args.input_file}")
            sys.exit(1)
        briefing = input_path.read_text(encoding="utf-8")
    elif args.briefing:
        briefing = args.briefing
    else:
        parser.print_help()
        print("\n❌ Erro: forneça o briefing do projeto (argumento ou --input)")
        sys.exit(1)

    mode = args.mode
    modo_info = MODOS[mode]
    crew_keys = modo_info["crews"]

    if args.start_phase:
        if args.start_phase in crew_keys:
            idx = crew_keys.index(args.start_phase)
            crew_keys = crew_keys[idx:]
        else:
            print(f"❌ Fase '{args.start_phase}' não encontrada no modo '{mode}'")
            print(f"   Fases disponíveis: {', '.join(crew_keys)}")
            sys.exit(1)

    # ── HEADER ──
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║       cp-orquestrador — Orquestrador da Fábrica de Software ║
╚══════════════════════════════════════════════════════════════╝
""")
    print(f"📋 Briefing: {briefing[:120]}...")
    print(f"🔧 Modo: {modo_info['name']} — {modo_info['description']}")
    print(f"📂 Fases: {len(crew_keys)}")
    print(f"🚀 Modo: {'AUTO (execução real)' if args.auto else 'SIMULAÇÃO (CrewAI)'}")
    print()

    # ── Mostra plano ──
    print(f"{'='*60}")
    print(f"  PLANO DO PIPELINE")
    print(f"{'='*60}\n")

    # Modo full-dev: mostra as fases NEXUS nativas (merge de cp-full-dev)
    if mode == "full-dev":
        nexus_mode = nexus_detect_mode(briefing)
        phases = NEXUS_PHASES.get(nexus_mode, NEXUS_PHASES["micro"])
        phase_keys = list(phases.keys())
        total_agents = 0
        for i, pk in enumerate(phase_keys, 1):
            phase = phases[pk]
            n_agents = len(phase["agents"])
            total_agents += n_agents
            print(f"  Fase {i}: {phase['name']} ({n_agents} agentes)")
            print(f"    Gate: {phase['gate_keeper']}")
            print(f"    {phase['description']}")
            print()
        print(f"  Total: {total_agents} agentes em {len(phase_keys)} fases (NEXUS modo {nexus_mode})\n")
        # full-dev executa nativamente via NexusExecutor (modo --auto). Sem --auto,
        # apenas mostra o plano (não há crew CrewAI de simulação para o NEXUS).
        if not args.auto:
            print("🧪 Plano NEXUS exibido. Use --auto para executar o pipeline NEXUS nativo.\n")
            return

    total_agents = 0
    if mode != "full-dev":
        for i, ck in enumerate(crew_keys, 1):
            crew = CREWS[ck]
            n_agents = len(crew["agents"])
            total_agents += n_agents
            print(f"  Fase {i}: {crew['name']}")
            print(f"    Skill: {crew['skill']}")
            print(f"    Agentes: {n_agents} ({', '.join(crew['agents'])})")
            print(f"    Inputs: {', '.join(crew['inputs'])}")
            print(f"    Outputs: {', '.join(crew['outputs'])}")
            print(f"    Quality Gate: {crew['quality_gate']}")
            print()

        print(f"  Total: {total_agents} agentes em {len(crew_keys)} fases\n")

        if args.dry_run:
            print("🧪 DRY RUN — plano exibido. Remova --dry-run para executar.\n")
            return

    # ── MODO AUTO ──
    if args.auto:
        # Modo full-dev: executa o pipeline NEXUS nativamente (merge de cp-full-dev)
        if mode == "full-dev":
            nexus = NexusExecutor(
                requirement=briefing,
                mode="auto",
                start_phase=args.start_phase,
                output_dir=args.output,
                kanban_task=args.kanban_task,
                python_cmd=args.python,
            )
            report = nexus.run()
            if report["status"] == "failed":
                print(f"\n❌ Pipeline NEXUS falhou na fase: {report['failed_phase']}")
                print(f"   Corrija o problema e re-execute com --start-phase {report['failed_phase']}")
                sys.exit(1)
            else:
                print(f"\n✅ Pipeline NEXUS concluído com sucesso!")
            return

        executor = PipelineExecutor(
            briefing=briefing,
            mode=mode,
            start_phase=args.start_phase,
            output_dir=args.output,
            python_cmd=args.python,
            kanban_task=args.kanban_task,
        )
        report = executor.run()

        if report["status"] == "failed":
            print(f"\n❌ Pipeline falhou na fase: {CREWS[report['failed_phase']]['name']}")
            print(f"   Corrija o problema e re-execute com --start-phase {report['failed_phase']}")
            sys.exit(1)
        else:
            print(f"\n✅ Pipeline concluído com sucesso!")
        return

    # ── MODO SIMULAÇÃO (CrewAI) ──
    try:
        from crewai import Agent, Task, Crew, Process
    except ImportError:
        print("❌ crewai não instalado. Execute: pip install crewai")
        print("   Ou use --auto se preferir execução direta sem CrewAI.")
        sys.exit(3)  # codigo padronizado: 3 = crewai ausente (ver require_crewai)

    print("🚀 Montando crew de orquestração (simulação)...\n")
    crew = build_simulation_crew(briefing, mode, args.start_phase)

    print("🤖 Agentes na crew:")
    for agent in crew.agents:
        print(f"  - {agent.role}")
    print(f"\n📋 Tasks ({len(crew.tasks)}):")
    task_names = [
        "1. Planejamento do Pipeline",
        "2. Execução Faseada com Passagem de Artefatos",
        "3. Decisões de Quality Gate",
        "4. Relatório Final",
    ]
    for i, tn in enumerate(task_names, 1):
        agent_name = crew.tasks[i-1].agent.role if hasattr(crew.tasks[i-1], 'agent') and crew.tasks[i-1].agent else "?"
        print(f"  {tn} → {agent_name}")
    print()

    require_llm()  # DT-08: falha cedo, com mensagem, se nao ha LLM
    print("🚀 Executando simulação do pipeline...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n{'='*60}")
    print(f"  ✅ SIMULAÇÃO CONCLUÍDA")
    print(f"{'='*60}\n")
    print(result_str)

    # Salva
    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {out_file.resolve()}")
    else:
        output_dir = ORQUESTRADOR_DIR / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"simulacao_{mode}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()