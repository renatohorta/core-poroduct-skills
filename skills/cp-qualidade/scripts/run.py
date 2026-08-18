#!/usr/bin/env python3
"""
cp-qualidade — Garantia da Qualidade de Software Crew (self-contained)

Cria uma crew CrewAI com 4 agentes especializados para auditar processos,
medir métricas de qualidade, propor melhorias contínuas e validar artefatos.

Uso:
  python run.py "sistema de agendamento de consultas"
  python run.py "API de pagamentos" --mode audit
  python run.py --input descricao.md --output relatorio-qualidade.md
  python run.py "teste" --dry-run
"""

import argparse
import sys
import json
import os
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
    "auditor-de-qualidade": {
        "role": "Auditor de Qualidade",
        "goal": (
            "Revisar se os processos de software estão sendo seguidos corretamente, "
            "verificar artefatos obrigatórios, identificar desvios de processo "
            "e garantir conformidade com padrões estabelecidos"
        ),
        "backstory": (
            "Auditor de qualidade rigoroso com mais de 15 anos de experiência "
            "em auditoria de processos de software. Você segue checklists à risca "
            "e não aceita atalhos ou 'jeitinhos'. "
            "Você conhece CMMI, ISO 9001, ISO 25010 e boas práticas de engenharia "
            "de software como a palma da sua mão. "
            "Cada desvio de processo que você encontra é documentado com evidências, "
            "impacto e severidade. Você não se deixa convencer por desculpas — "
            "se o processo não foi seguido, está documentado. "
            "Seu lema: 'Processo não é burocracia, é garantia de qualidade.' "
            "Você verifica: planejamento, requisitos, design, implementação, "
            "testes, deploy, documentação e monitoramento."
        ),
    },
    "analista-de-metricas": {
        "role": "Analista de Métricas",
        "goal": (
            "Coletar, analisar e interpretar métricas de qualidade de software "
            "para transformar dados brutos em insights acionáveis para o time"
        ),
        "backstory": (
            "Analista de dados especializado em engenharia de software. "
            "Você transforma números em histórias que o time entende. "
            "Métricas que você analisa: cobertura de testes (linha, branch, mutação), "
            "densidade de bugs, débito técnico (tempo estimado para pagar), "
            "velocity do time, lead time, cycle time, MTTR, MTBF, "
            "complexidade ciclomática, acoplamento, coesão, e duplicação de código. "
            "Você não apenas calcula métricas — você as contextualiza: "
            "'cobertura de 85% é boa, mas se os 15% não testados são o core do sistema, é risco.' "
            "Você gera dashboards mentais com tendências (últimas 4 sprints) "
            "e alertas quando métricas saem dos thresholds aceitáveis. "
            "Seu lema: 'O que não é medido não pode ser melhorado.' "
            "Você sempre pergunta: 'Essa métrica está melhorando ou piorando ao longo do tempo?'"
        ),
    },
    "engenheiro-melhoria-continua": {
        "role": "Engenheiro de Melhoria Contínua",
        "goal": (
            "Propor e implementar melhorias no processo de desenvolvimento "
            "com base em dados de auditoria e métricas, aplicando princípios "
            "de Kaizen, Lean e melhoria contínua"
        ),
        "backstory": (
            "Engenheiro de processos que aplica Kaizen e Lean em times de software "
            "há mais de 10 anos. Você enxerga desperdício onde outros veem 'jeito de fazer'. "
            "Para você, todo processo tem gargalos esperando para ser eliminados. "
            "Você usa o ciclo PDCA (Plan-Do-Check-Act) e a abordagem DMAIC "
            "(Define-Measure-Analyze-Improve-Control) para estruturar melhorias. "
            "Você classifica desperdícios em 7 categorias Lean: "
            "espera, retrabalho, superprodução, movimento, transporte, "
            "superprocessamento e inventário. "
            "Cada melhoria que você propõe tem: problema identificado, "
            "causa raiz, solução proposta, esforço estimado, impacto esperado "
            "e métrica para verificar se a melhoria funcionou. "
            "Seu lema: 'Melhorar 1% a cada sprint é melhor que esperar pela solução perfeita.' "
            "Você prioriza melhorias por impacto vs. esforço (matriz de priorização)."
        ),
    },
    "validador-de-artefatos": {
        "role": "Validador de Artefatos",
        "goal": (
            "Verificar se todos os artefatos obrigatórios do ciclo de desenvolvimento "
            "existem, estão completos, atualizados e em conformidade com os templates "
            "e padrões estabelecidos"
        ),
        "backstory": (
            "QA de processo que não deixa passar documentação faltando. "
            "Você é o guardião dos artefatos — se não está documentado, não foi feito. "
            "Você verifica cada artefato obrigatório do ciclo de vida: "
            "documento de visão, especificação de requisitos, arquitetura, "
            "diagramas UML, casos de uso, protótipos, plano de testes, "
            "relatório de testes, manual de deploy, README, CHANGELOG, "
            "e documentação de API. "
            "Para cada artefato, você verifica: existe? está completo? "
            "está atualizado? segue o template? foi aprovado pelos stakeholders? "
            "tem versão e data? está acessível ao time? "
            "Você não aceita 'vou fazer depois' — se o artefato é obrigatório "
            "para a fase, ele precisa estar pronto antes de avançar. "
            "Seu lema: 'Documentação não é opcional — é o que separa projeto de gambiarra.' "
            "Você emite um checklist detalhado com status: ✅ Completo, ⚠️ Incompleto, ❌ Ausente."
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

def build_crew(
    descricao: str,
    mode: str = "full",
):
    """
    Build a CrewAI crew for software quality assurance.

    Args:
        descricao: Description of the project/system being audited
        mode: 'audit', 'metrics', 'improvement', or 'full'
    """
    auditor = get_agent("auditor-de-qualidade")
    analista = get_agent("analista-de-metricas")
    melhoria = get_agent("engenheiro-melhoria-continua")
    validador = get_agent("validador-de-artefatos")

    context = f"DESCRIÇÃO DO PROJETO/SISTEMA:\n{descricao}"

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Auditoria de Processo (Auditor)
    # ─────────────────────────────────────────────────────────────────────
    task_auditoria = Task(
        description=f"""
        {context}

        SEU TRABALHO — AUDITORIA DE PROCESSO:

        Como Auditor de Qualidade, sua missão é revisar se os processos de
        software estão sendo seguidos corretamente.

        1. **Verificação de Processos Obrigatórios:**
           - Planejamento: cronograma existe? riscos mapeados? recursos alocados?
           - Requisitos: especificação funcional? critérios de aceitação? rastreabilidade?
           - Design: arquitetura documentada? decisões técnicas registradas? padrões definidos?
           - Implementação: code review obrigatório? padrões de código? commits semânticos?
           - Testes: plano de testes? cobertura mínima? testes automatizados?
           - Deploy: pipeline CI/CD? rollback plan? health checks?
           - Monitoramento: logs? alertas? dashboards? SLAs/SLOs definidos?

        2. **Identificação de Desvios:**
           - Para cada processo não seguido, documente:
             - Qual processo foi desviado
             - O que deveria ter sido feito
             - O que foi feito no lugar
             - Impacto do desvio (Crítico/Alto/Médio/Baixo)
             - Evidência do desvio

        3. **Análise de Conformidade:**
           - Percentual de processos seguidos vs. não seguidos
           - Padrões de desvio (sempre pulam a mesma etapa?)
           - Riscos associados aos desvios encontrados

        FORMATO DE SAÍDA:
        ## Relatório de Auditoria de Processo

        ### Processos Verificados
        | Processo | Status | Evidência | Impacto |
        |----------|--------|-----------|---------|
        | Planejamento | ✅/⚠️/❌ | ... | ... |
        | Requisitos | ✅/⚠️/❌ | ... | ... |
        | ... | ... | ... | ... |

        ### Desvios Identificados
        - [Severidade] Processo: descrição do desvio
        - ...

        ### Conformidade Geral
        - Processos seguidos: X/Y (X%)
        - Riscos identificados: [lista]
        - Veredito da Auditoria: ✅ Conforme / ⚠️ Não Conforme
        """,
        expected_output=(
            "Relatório de auditoria de processo completo com verificação de "
            "processos obrigatórios, desvios identificados e veredito de conformidade"
        ),
        agent=auditor,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Validação de Artefatos (Validador)
    # ─────────────────────────────────────────────────────────────────────
    task_validacao = Task(
        description=f"""
        {context}

        SEU TRABALHO — VALIDAÇÃO DE ARTEFATOS:

        Como Validador de Artefatos, sua missão é verificar se todos os
        artefatos obrigatórios existem e estão completos.

        1. **Artefatos Obrigatórios por Fase:**

           **Planejamento:**
           - Documento de Visão do Produto
           - Cronograma do Projeto
           - Matriz de Riscos
           - Termo de Abertura

           **Requisitos:**
           - Especificação de Requisitos Funcionais
           - Especificação de Requisitos Não-Funcionais
           - Casos de Uso / Histórias de Usuário
           - Critérios de Aceitação
           - Protótipos / Wireframes

           **Design/Arquitetura:**
           - Documento de Arquitetura (ADR)
           - Diagramas UML (classes, sequência, estados)
           - Modelo de Dados (DER)
           - Contratos de API (OpenAPI/Swagger)

           **Implementação:**
           - Código Fonte (com versionamento)
           - README do projeto
           - Guia de Contribuição
           - CHANGELOG

           **Testes:**
           - Plano de Testes
           - Casos de Teste
           - Relatório de Testes
           - Relatório de Cobertura

           **Deploy/Operação:**
           - Manual de Deploy
           - Runbook de Operação
           - Plano de Rollback
           - Documentação de Infraestrutura

        2. **Critérios de Validação para Cada Artefato:**
           - ✅ Existe: o arquivo/documento existe
           - ✅ Completo: todas as seções obrigatórias estão preenchidas
           - ✅ Atualizado: reflete o estado atual do projeto
           - ✅ Aprovado: teve revisão/aprovação dos stakeholders
           - ✅ Acessível: está disponível para todo o time

        3. **Checklist Final:**
           - Total de artefatos obrigatórios: N
           - Completos: N (%)
           - Incompletos: N (%)
           - Ausentes: N (%)

        FORMATO DE SAÍDA:
        ## Relatório de Validação de Artefatos

        ### Checklist de Artefatos
        | Artefato | Fase | Existe | Completo | Atualizado | Status |
        |----------|------|--------|----------|------------|--------|
        | Documento de Visão | Planejamento | ✅ | ✅ | ✅ | ✅ |
        | ... | ... | ... | ... | ... | ... |

        ### Artefatos Ausentes (Crítico)
        - [lista com impacto]

        ### Artefatos Incompletos (Atenção)
        - [lista com o que falta]

        ### Resumo
        - Total: N | Completos: N | Incompletos: N | Ausentes: N
        - Conformidade: X%
        - Veredito: ✅ Aprovado / ❌ Reprovado
        """,
        expected_output=(
            "Checklist completo de validação de artefatos com status por "
            "artefato, análise de completude e veredito de aprovação"
        ),
        agent=validador,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 3: Análise de Métricas (Analista de Métricas)
    # ─────────────────────────────────────────────────────────────────────
    task_metricas = Task(
        description=f"""
        {context}

        SEU TRABALHO — ANÁLISE DE MÉTRICAS:

        Como Analista de Métricas, sua missão é coletar, analisar e interpretar
        métricas de qualidade do software.

        1. **Métricas a Analisar:**

           **Qualidade do Código:**
           - Cobertura de testes (linha, branch, mutação)
           - Complexidade ciclomática média
           - Densidade de bugs (bugs/KLOC)
           - Débito técnico estimado (horas/dias para pagar)
           - Duplicação de código (%)
           - Acoplamento e coesão

           **Processo:**
           - Velocity do time (pontos por sprint)
           - Lead time (da ideia ao deploy)
           - Cycle time (do desenvolvimento ao deploy)
           - Taxa de retrabalho (%)
           - MTTR (Mean Time to Recover)
           - MTBF (Mean Time Between Failures)

           **Produto:**
           - Bugs abertos vs. fechados
           - Bugs por severidade (Crítico/Alto/Médio/Baixo)
           - Tempo médio de resolução de bugs
           - Issues abertas vs. fechadas
           - Satisfação do usuário (NPS/CSAT)

        2. **Análise e Interpretação:**
           - Para cada métrica, informe:
             - Valor atual
             - Threshold aceitável
             - Tendência (melhorando/piorando/estável)
             - Comparação com período anterior
           - Identifique correlações entre métricas
             - Ex: 'Queda de cobertura + aumento de bugs em produção'
           - Destaque métricas fora do threshold

        3. **Insights e Alertas:**
           - Top 3 métricas que precisam de atenção imediata
           - Métricas que melhoraram (reforçar práticas)
           - Riscos baseados em tendências

        FORMATO DE SAÍDA:
        ## Relatório de Análise de Métricas

        ### Métricas de Qualidade de Código
        | Métrica | Valor | Threshold | Status | Tendência |
        |---------|-------|-----------|--------|-----------|
        | Cobertura | 72% | >= 80% | ❌ | 📉 piorando |
        | ... | ... | ... | ... | ... |

        ### Métricas de Processo
        | Métrica | Valor | Threshold | Status | Tendência |
        |---------|-------|-----------|--------|-----------|

        ### Métricas de Produto
        | Métrica | Valor | Threshold | Status | Tendência |
        |---------|-------|-----------|--------|-----------|

        ### Insights
        - 🔴 Alerta: [métrica] está [X%] acima/abaixo do threshold
        - 🟡 Atenção: [métrica] está piorando há [N] sprints
        - 🟢 Positivo: [métrica] melhorou [X%] desde a última medição

        ### Correlações Identificadas
        - [correlação 1]
        - [correlação 2]

        ### Recomendações Baseadas em Dados
        - [recomendação 1]
        - [recomendação 2]
        """,
        expected_output=(
            "Relatório de análise de métricas completo com tabelas de métricas, "
            "insights, correlações e recomendações baseadas em dados"
        ),
        agent=analista,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Propostas de Melhoria (Eng. Melhoria Contínua)
    # ─────────────────────────────────────────────────────────────────────
    task_melhoria = Task(
        description=f"""
        {context}

        SEU TRABALHO — PROPOSTAS DE MELHORIA CONTÍNUA:

        Como Engenheiro de Melhoria Contínua, sua missão é propor melhorias
        no processo com base nos resultados da auditoria, validação de artefatos
        e análise de métricas.

        1. **Análise de Causa Raiz:**
           Para cada problema identificado na auditoria e nas métricas:
           - Qual é a causa raiz? (use 5 Porquês ou Diagrama de Ishikawa)
           - O problema é pontual ou sistêmico?
           - Quem/qual área é afetada?

        2. **Classificação de Desperdícios (Lean):**
           - **Espera:** time esperando code review, deploy, aprovação
           - **Retrabalho:** bugs que voltam, requisitos mal entendidos
           - **Superprodução:** features que ninguém pediu, documentação excessiva
           - **Movimento:** contexto switching, reuniões desnecessárias
           - **Transporte:** handoffs entre times, mudanças de prioridade
           - **Superprocessamento:** burocracia, approval chains longas
           - **Inventário:** backlog gigante, branches abertas há meses

        3. **Propostas de Melhoria (mínimo 5):**
           Para cada proposta:
           - **Problema:** qual dor está sendo resolvida
           - **Causa Raiz:** por que o problema existe
           - **Solução:** o que fazer para resolver
           - **Esforço:** 🔵 Baixo / 🟡 Médio / 🔴 Alto
           - **Impacto:** 🔵 Baixo / 🟡 Médio / 🔴 Alto
           - **Prioridade:** (Impacto / Esforço)
           - **Métrica de Sucesso:** como saber se a melhoria funcionou
           - **Prazo Sugerido:** curto (1 sprint), médio (2-4 sprints), longo (5+)

        4. **Matriz de Priorização:**
           - Organize as melhorias em uma matriz Impacto vs. Esforço
           - Quick Wins (Alto Impacto, Baixo Esforço) — faça agora
           - Grandes Projetos (Alto Impacto, Alto Esforço) — planeje
           - Preenchimento (Baixo Impacto, Baixo Esforço) — faça quando der
           - Descartáveis (Baixo Impacto, Alto Esforço) — evite

        5. **Plano de Ação (Próximos 30 Dias):**
           - O que fazer na sprint 1
           - O que fazer na sprint 2
           - Como medir o progresso

        FORMATO DE SAÍDA:
        ## Relatório de Melhoria Contínua

        ### Análise de Causa Raiz
        - Problema: [descrição]
        - 5 Porquês: [1] → [2] → [3] → [4] → [5]
        - Causa Raiz: [conclusão]

        ### Desperdícios Identificados
        | Tipo | Onde | Impacto |
        |------|------|---------|
        | Espera | Code review leva 3 dias | Alto |
        | ... | ... | ... |

        ### Propostas de Melhoria
        | # | Problema | Solução | Esforço | Impacto | Prioridade |
        |---|----------|---------|---------|---------|------------|
        | 1 | ... | ... | 🔵 | 🔴 | Alta |
        | ... | ... | ... | ... | ... | ... |

        ### Matriz de Priorização
        - **Quick Wins (Alto Impacto, Baixo Esforço):**
          - [melhoria 1] — faça agora
          - [melhoria 2] — faça agora
        - **Grandes Projetos (Alto Impacto, Alto Esforço):**
          - [melhoria 3] — planeje
        - **Preenchimento (Baixo Impacto, Baixo Esforço):**
          - [melhoria 4] — faça quando der
        - **Descartáveis (Baixo Impacto, Alto Esforço):**
          - [melhoria 5] — evite

        ### Plano de Ação — Próximos 30 Dias
        - Sprint 1: [ações]
        - Sprint 2: [ações]
        - Métricas de progresso: [como medir]
        """,
        expected_output=(
            "Relatório de melhoria contínua completo com análise de causa raiz, "
            "desperdícios identificados, propostas priorizadas e plano de ação"
        ),
        agent=melhoria,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 5: Quality Gate — Relatório Final (todos os agentes)
    # ─────────────────────────────────────────────────────────────────────
    task_quality_gate = Task(
        description=f"""
        {context}

        SEU TRABALHO — QUALITY GATE E RELATÓRIO FINAL:

        Compile todos os resultados das fases anteriores e produza o relatório
        final de qualidade com veredito PASS/FAIL.

        1. **Compile os Resultados:**

           **Auditoria de Processo:**
           - Processos seguidos: X%
           - Desvios encontrados: N (Críticos: N, Altos: N, Médios: N, Baixos: N)
           - Veredito da auditoria

           **Validação de Artefatos:**
           - Artefatos completos: X%
           - Artefatos ausentes: N
           - Veredito da validação

           **Análise de Métricas:**
           - Métricas dentro do threshold: X%
           - Alertas ativos: N
           - Tendências: [resumo]

           **Melhoria Contínua:**
           - Quick Wins identificados: N
           - Melhorias propostas: N
           - Plano de ação: [resumo]

        2. **Quality Gate — Critérios:**
           - **PASS** se TODOS os critérios forem atendidos:
             - Processos seguidos: 100%
             - Artefatos completos: 100%
             - Cobertura de testes: >= 80%
             - Débito técnico: < 20%
             - Bugs críticos em produção: 0
             - Velocity dentro da média histórica
           - **FAIL** se QUALQUER critério não for atendido

        3. **Recomendações Finais:**
           - O que precisa ser resolvido URGENTE (antes da próxima release)
           - O que precisa ser resolvido em 30 dias
           - O que colocar no backlog de melhoria contínua
           - Riscos residuais assumidos

        FORMATO DE SAÍDA:
        ## Relatório Final de Qualidade

        ### Resumo Executivo
        - Projeto: [nome]
        - Data da auditoria: [data]
        - Veredito Final: ✅ PASS / ❌ FAIL
        - Conformidade Geral: X%

        ### Resultados por Dimensão
        | Dimensão | Resultado | Status |
        |----------|-----------|--------|
        | Auditoria de Processo | X% conforme | ✅/❌ |
        | Validação de Artefatos | X% completo | ✅/❌ |
        | Métricas de Qualidade | X% dentro do threshold | ✅/❌ |
        | Melhoria Contínua | N propostas | ✅/❌ |

        ### Quality Gate
        - Processos 100% seguidos: ✅ / ❌
        - Artefatos 100% completos: ✅ / ❌
        - Cobertura >= 80%: ✅ / ❌
        - Débito técnico < 20%: ✅ / ❌
        - Bugs críticos = 0: ✅ / ❌
        - Velocity OK: ✅ / ❌
        - **Veredito Final: PASS / FAIL**

        ### Ações Urgentes (Antes da Próxima Release)
        - [ação 1]
        - [ação 2]

        ### Ações em 30 Dias
        - [ação 1]
        - [ação 2]

        ### Backlog de Melhoria Contínua
        - [item 1]
        - [item 2]

        ### Riscos Residuais
        - [risco 1]
        - [risco 2]

        ### Recomendações Finais
        - [recomendação 1]
        - [recomendação 2]
        """,
        expected_output=(
            "Relatório final de qualidade completo com veredito PASS/FAIL, "
            "compilação de todas as dimensões, ações urgentes e recomendações"
        ),
        agent=auditor,
    )

    # --- Build task list based on mode ---
    all_tasks = []
    used_agents = []

    if mode in ("full", "audit"):
        all_tasks.append(task_auditoria)
        all_tasks.append(task_validacao)
        used_agents.extend([auditor, validador])

    if mode in ("full", "metrics"):
        all_tasks.append(task_metricas)
        used_agents.append(analista)

    if mode in ("full", "improvement"):
        all_tasks.append(task_melhoria)
        used_agents.append(melhoria)

    # Quality gate always runs
    all_tasks.append(task_quality_gate)
    if auditor not in used_agents:
        used_agents.append(auditor)

    # --- Crew ---
    crew = Crew(
        agents=used_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-qualidade: Garantia da Qualidade de Software Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python run.py \"sistema de agendamento de consultas\"\n"
            "  python run.py \"API de pagamentos\" --mode audit\n"
            "  python run.py --input descricao.md --output relatorio-qualidade.md\n"
            "  python run.py \"teste\" --dry-run\n"
        ),
    )
    parser.add_argument(
        "descricao",
        nargs="?",
        help="Descrição do projeto/sistema a ser auditado",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição do projeto (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o relatório de qualidade",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "audit", "metrics", "improvement"],
        default="full",
        help="Modo de execução (default: full — auditoria + métricas + melhoria)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: mensagem acionavel em vez de traceback

    # --- Resolve descrição ---
    descricao = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ Arquivo não encontrado: {args.input_file}")
            sys.exit(1)
        descricao = input_path.read_text(encoding="utf-8")
    elif args.descricao:
        descricao = args.descricao
    else:
        parser.print_help()
        print("\n❌ Erro: forneça a descrição do projeto (argumento ou --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    # Mode name mapping
    mode_names = {
        "full": "Completo (auditoria + métricas + melhoria)",
        "audit": "Apenas Auditoria de Processo e Artefatos",
        "metrics": "Apenas Análise de Métricas",
        "improvement": "Apenas Propostas de Melhoria",
    }

    print(f"\n📋 Projeto: {descricao[:120]}...")
    print(f"🔧 Modo: {mode_names.get(mode, mode)}")
    print(f"🤖 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(
        descricao=descricao,
        mode=mode,
    )

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            agent_name = task.agent.role if hasattr(task, 'agent') and task.agent else "?"
            desc_short = task.description[:100].replace("\n", " ").strip()
            print(f"  {i}. {desc_short}... → {agent_name}")
        print(f"\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de garantia de qualidade...\n")
    require_llm()  # DT-08: falha cedo, com mensagem, se nao ha LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Relatório de Qualidade gerado!\n")
    print(result_str)

    # --- Save output ---
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")
    else:
        # Save to default location
        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"relatorio-qualidade_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()