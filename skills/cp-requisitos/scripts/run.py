#!/usr/bin/env python3
"""
cp-requisitos — Engenharia de Requisitos Crew (self-contained)

Cria uma crew CrewAI com agentes especializados para elicitar, analisar,
especificar e validar requisitos de software.

Uso:
  python run.py "sistema de agendamento para clínicas"
  python run.py --briefing "preciso de um app para gerenciar estoque" --output requisitos.md
  python run.py --input briefing.txt
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from crewai import Agent, Task, Crew, Process

# ═══════════════════════════════════════════════════════════════════════════
# AGENTES EMBUTIDOS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "analista-de-negocios": {
        "role": "Analista de Negócios",
        "goal": "Descobrir, documentar e validar regras de negócio com stakeholders",
        "backstory": (
            "Analista de negócios experiente com mais de 10 anos em projetos de software. "
            "Você é especialista em entrevistar stakeholders, descobrir regras de negócio "
            "implícitas, e traduzir necessidades de negócio em requisitos claros. "
            "Você pergunta 'por quê?' até chegar na real necessidade. "
            "Sabe diferenciar o que o cliente PEDE do que ele PRECISA."
        ),
    },
    "especificador-de-requisitos": {
        "role": "Especificador de Requisitos",
        "goal": "Redigir user stories, casos de uso e critérios de aceitação claros e testáveis",
        "backstory": (
            "Especialista em especificação de requisitos com formação em engenharia de software. "
            "Você transforma descobertas do analista de negócios em artefatos formais: "
            "user stories no formato 'Como [papel], quero [funcionalidade] para [benefício]', "
            "casos de uso com fluxo principal e alternativos, e critérios de aceitação "
            "no formato BDD (Dado/Quando/Então). "
            "Seus requisitos são tão claros que desenvolvedores raramente precisam de esclarecimento."
        ),
    },
    "validador-de-requisitos": {
        "role": "Validador de Requisitos",
        "goal": "Verificar consistência, completude, viabilidade e rastreabilidade dos requisitos",
        "backstory": (
            "Validador de requisitos rigoroso e detalhista. Você verifica se cada requisito é: "
            "específico, mensurável, alcançável, relevante e temporal (SMART). "
            "Você caça inconsistências, ambiguidades, requisitos conflitantes e lacunas. "
            "Seu lema: 'Um requisito ambíguo é uma bomba relógio no orçamento do projeto.' "
            "Você não aprova nada sem rastreabilidade bidirecional."
        ),
    },
    "product-owner-proxy": {
        "role": "Product Owner (Proxy)",
        "goal": "Priorizar requisitos e garantir alinhamento com a visão do produto e valor de negócio",
        "backstory": (
            "Product Owner experiente que representa os interesses do cliente e do negócio. "
            "Você prioriza requisitos com base em valor de negócio, urgência e dependências. "
            "Usa técnicas como MoSCoW (Must/Should/Could/Won't) e Value vs Effort. "
            "Você garante que cada requisito entregue gere valor real para o usuário e para o negócio. "
            "Sabe dizer 'não' para requisitos que não agregam valor."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    data = AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agente não encontrado: {slug} — usando fallback genérico")
        return Agent(
            role=name,
            goal=f"Completar a tarefa com excelência como {name}",
            backstory=f"Agente especializado atuando como {name}.",
            verbose=True,
            allow_delegation=False,
        )
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        verbose=True,
        allow_delegation=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Crew builder
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, output_path: str = None):
    """Build a CrewAI crew for requirements engineering."""

    analista = get_agent("analista-de-negocios")
    especificador = get_agent("especificador-de-requisitos")
    validador = get_agent("validador-de-requisitos")
    po = get_agent("product-owner-proxy")

    # --- Task 1: Elicitação ---
    elicitacao = Task(
        description=f"""
        BRIEFING DO CLIENTE:
        {briefing}

        SEU TRABALHO — ELICITAÇÃO DE REQUISITOS:
        1. Analise o briefing e identifique o domínio do problema
        2. Questione suposições implícitas no briefing
        3. Identifique os stakeholders envolvidos
        4. Liste as necessidades de negócio (NÃO soluções técnicas)
        5. Identifique regras de negócio que podem estar implícitas
        6. Documente suposições e riscos

        FORMATO DE SAÍDA:
        ## Análise de Negócio
        - Domínio: [qual domínio]
        - Stakeholders: [quem são]
        - Necessidades identificadas: [lista]
        - Regras de negócio: [lista]
        - Suposições: [lista]
        - Riscos: [lista]
        """,
        expected_output="Análise de negócio completa com stakeholders, necessidades, regras, suposições e riscos",
        agent=analista,
    )

    # --- Task 2: Especificação ---
    especificacao = Task(
        description=f"""
        BRIEFING DO CLIENTE:
        {briefing}

        SEU TRABALHO — ESPECIFICAÇÃO DE REQUISITOS:
        Com base na análise de negócio realizada, produza:

        1. **Épicos e Features** — agrupamento de funcionalidades
        2. **User Stories** — no formato "Como [papel], quero [funcionalidade] para [benefício]"
        3. **Critérios de Aceitação** — no formato BDD (Dado/Quando/Então)
        4. **Casos de Uso** — fluxo principal + fluxos alternativos para cada user story
        5. **Regras de Negócio** — formais e testáveis
        6. **Requisitos Não-Funcionais** — performance, segurança, usabilidade, etc.

        Seja específico. Cada user story deve ser implementável em 1-3 dias.
        """,
        expected_output="Documento de requisitos completo: épicos, user stories, critérios de aceitação, casos de uso, regras de negócio e requisitos não-funcionais",
        agent=especificador,
    )

    # --- Task 3: Validação ---
    validacao = Task(
        description=f"""
        BRIEFING DO CLIENTE:
        {briefing}

        SEU TRABALHO — VALIDAÇÃO DE REQUISITOS:
        Revise o documento de requisitos produzido e verifique:

        1. **Completude**: Todos os cenários importantes estão cobertos?
        2. **Consistência**: Há requisitos conflitantes?
        3. **Clareza**: Cada requisito é específico e sem ambiguidade?
        4. **Testabilidade**: Cada critério de aceitação é verificável?
        5. **Rastreabilidade**: Cada requisito está ligado a uma necessidade de negócio?
        6. **Viabilidade**: Os requisitos são tecnicamente viáveis?

        Para cada problema encontrado, documente:
        - O problema específico
        - Por que é um problema
        - Sugestão de correção

        Emita um veredito: PASS ou FAIL.
        Se FAIL, liste o que precisa ser corrigido.
        """,
        expected_output="Relatório de validação: problemas encontrados (se houver), sugestões de correção, e veredito PASS/FAIL",
        agent=validador,
    )

    # --- Task 4: Priorização ---
    priorizacao = Task(
        description=f"""
        BRIEFING DO CLIENTE:
        {briefing}

        SEU TRABALHO — PRIORIZAÇÃO:
        Com base no documento de requisitos validado:

        1. Classifique cada requisito usando MoSCoW:
           - **Must Have**: Essencial para o MVP
           - **Should Have**: Importante, mas não crítico para o MVP
           - **Could Have**: Desejável, pode esperar
           - **Won't Have**: Fora de escopo por agora

        2. Para os Must Have, estime esforço relativo (Pequeno/Médio/Grande)

        3. Defina uma sugestão de MVP (mínimo conjunto viável)

        4. Identifique dependências entre requisitos

        Justifique cada decisão de priorização com base em valor de negócio.
        """,
        expected_output="Backlog priorizado (MoSCoW), sugestão de MVP, dependências entre requisitos, e justificativas de valor de negócio",
        agent=po,
    )

    # --- Crew ---
    crew = Crew(
        agents=[analista, especificador, validador, po],
        tasks=[elicitacao, especificacao, validacao, priorizacao],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-requisitos: Engenharia de Requisitos Crew (self-contained)",
    )
    parser.add_argument(
        "briefing",
        nargs="?",
        help="Briefing do cliente / descrição do problema",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com o briefing (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o documento de requisitos",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    # --- Resolve briefing ---
    briefing = None
    if args.input_file:
        briefing = Path(args.input_file).read_text(encoding="utf-8")
    elif args.briefing:
        briefing = args.briefing
    else:
        parser.print_help()
        print("\n❌ Erro: forneça o briefing do cliente (argumento ou --input)")
        sys.exit(1)

    output_path = args.output

    print(f"\n📋 Briefing: {briefing[:120]}...")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(briefing, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de requisitos...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Documento de Requisitos gerado!\n")
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
        out_file = output_dir / f"requisitos_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()
