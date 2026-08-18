#!/usr/bin/env python3
"""
cp-competitive-analysis — Análise Competitiva Crew (self-contained)

Cria uma crew CrewAI com agentes especializados para analisar concorrentes,
comparar produtos, features, preços, posicionamento e estratégias de mercado,
gerando relatórios completos de inteligência competitiva.

Uso:
  python run.py "SaaS de gestão de clínicas; concorrentes: Doctoralia, Zenklub"
  python run.py --context "nosso produto X" --output analise-competitiva.md
  python run.py --input contexto.txt
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from crewai import Agent, Task, Crew, Process
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import build_crew_llm

# ═══════════════════════════════════════════════════════════════════════════
# AGENTES EMBUTIDOS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "analista-de-mercado": {
        "role": "Analista de Mercado",
        "goal": "Definir o escopo da análise, mapear o mercado, seu tamanho, crescimento e dinâmica competitiva",
        "backstory": (
            "Analista de mercado experiente com mais de 10 anos em pesquisa de mercado e "
            "inteligência competitiva. Você é especialista em definir mercados, estimar "
            "tamanho e crescimento, identificar tendências e descrever a dinâmica "
            "competitiva de um setor. Você separa fatos de opiniões e sempre distingue "
            "o que é dado verificado do que é estimativa. Seu lema: 'Um mercado mal "
            "definido gera uma análise competitiva inútil.'"
        ),
    },
    "analista-de-competidores": {
        "role": "Analista de Competidores",
        "goal": "Perfilar cada concorrente: overview, produto, forças, fraquezas e estratégia",
        "backstory": (
            "Analista de competidores detalhista e metódico. Você constrói perfis completos "
            "de cada concorrente: fundação, sede, equipe, financiamento, mercado-alvo, "
            "portfólio de produtos, forças, fraquezas e abordagem de go-to-market. "
            "Você usa frameworks como a análise de Porter (objetivos, estratégia, "
            "suposições, capacidades) para prever o comportamento competitivo. "
            "Você é imparcial: não exagera forças nem minimiza fraquezas."
        ),
    },
    "analista-de-pricing": {
        "role": "Analista de Pricing e Posicionamento",
        "goal": "Comparar preços, tiers, posicionamento e construir o mapa de posicionamento competitivo",
        "backstory": (
            "Especialista em pricing e posicionamento de mercado. Você compara planos e "
            "tiers de preço (entry, mid-tier, enterprise), identifica estratégias de "
            "precificação (cost leader, premium, value) e posiciona cada concorrente "
            "em um mapa de posicionamento (preço vs. inovação, foco estreito vs. amplo). "
            "Você entende que preço é só um vetor do posicionamento e que a percepção "
            "de valor importa tanto quanto o número."
        ),
    },
    "estrategista": {
        "role": "Estrategista Competitivo",
        "goal": "Sintetizar SWOT, vantagens competitivas, recomendações estratégicas e battle cards",
        "backstory": (
            "Estrategista competitivo sênior com formação em estratégia de negócios. "
            "Você transforma dados de mercado, perfis de concorrentes e análise de "
            "pricing em insights acionáveis: SWOT, vantagens competitivas, recomendações "
            "de curto e médio prazo, respostas competitivas a vigiar e battle cards "
            "para equipes de vendas. Você é pragmático e orientado a ação — cada "
            "recomendação deve ser executável. Você emite o veredito final de "
            "completude do relatório (PASS/FAIL)."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
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

def build_crew(context: str, output_path: str = None):
    """Build a CrewAI crew for competitive analysis."""

    analista_mercado = get_agent("analista-de-mercado")
    analista_competidores = get_agent("analista-de-competidores")
    analista_pricing = get_agent("analista-de-pricing")
    estrategista = get_agent("estrategista")

    # --- Task 1: Escopo e Mercado ---
    mercado = Task(
        description=f"""
        CONTEXTO DA ANÁLISE:
        {context}

        SEU TRABALHO — DEFINIÇÃO DE ESCOPO E MERCADO:
        1. Defina claramente o mercado/segmento sendo analisado
        2. Identifique os concorrentes a analisar (os nomeados no contexto, ou proponha
           critérios e uma lista candidata se nenhum foi citado)
        3. Estime o tamanho do mercado e a taxa de crescimento (CAGR), marcando claramente
           o que é estimativa
        4. Liste as principais tendências do setor
        5. Descreva a dinâmica competitiva geral (concentração, barreiras, diferenciação)

        FORMATO DE SAÍDA:
        ## Market Overview
        - Definição de mercado: [qual]
        - Concorrentes identificados: [lista]
        - Tamanho e crescimento: [estimativas, marcadas como tal]
        - Tendências: [lista]
        - Dinâmica competitiva: [descrição]
        """,
        expected_output="Definição de escopo, lista de concorrentes, tamanho/crescimento de mercado, tendências e dinâmica competitiva",
        agent=analista_mercado,
    )

    # --- Task 2: Perfis de Competidores ---
    perfis = Task(
        description=f"""
        CONTEXTO DA ANÁLISE:
        {context}

        SEU TRABALHO — PERFIS DE COMPETIDORES:
        Para CADA concorrente identificado, produza um perfil completo:

        1. **Company Overview**: fundação, sede, funcionários, financiamento/receita, mercado-alvo
        2. **Product/Service Overview**: principais ofertas
        3. **Strengths**: 3+ forças
        4. **Weaknesses**: 3+ fraquezas
        5. **Strategy**: como competem, abordagem de go-to-market

        Use o framework de Porter (objetivos futuros, estratégia atual, suposições,
        capacidades) para inferir o perfil de resposta competitiva de cada um.

        FORMATO DE SAÍDA (para cada concorrente):
        ### Competidor: [Nome]
        #### Company Overview
        | Atributo | Detalhe |
        #### Product/Service Overview
        #### Strengths
        #### Weaknesses
        #### Strategy
        """,
        expected_output="Perfis completos de cada concorrente com overview, produto, forças, fraquezas e estratégia",
        agent=analista_competidores,
    )

    # --- Task 3: Pricing e Posicionamento ---
    pricing = Task(
        description=f"""
        CONTEXTO DA ANÁLISE:
        {context}

        SEU TRABALHO — PRICING E POSICIONAMENTO:
        Com base nos perfis de concorrentes:

        1. **Matriz de Features**: compare as principais features/capacidades entre
           [sua empresa] e cada concorrente (✅ forte, ⚠️ parcial, ❌ ausente)
        2. **Comparação de Pricing**: organize os planos/tiers (entry/free, mid-tier,
           enterprise) de cada concorrente lado a lado
        3. **Insights de Pricing**: identifique a estratégia de cada um (cost leader,
           premium, value) e o que isso revela
        4. **Mapa de Posicionamento**: posicione cada concorrente em um mapa
           (ex: preço alto/baixo vs. inovação alta/baixa, ou foco estreito/amplo)

        FORMATO DE SAÍDA:
        ## Feature Comparison
        | Feature | [Sua empresa] | [Comp 1] | [Comp 2] | [Comp 3] |
        ## Pricing Comparison
        | Tier | [Sua empresa] | [Comp 1] | [Comp 2] | [Comp 3] |
        ## Positioning Map
        [descrição textual do mapa de posicionamento]
        ## Pricing Insights
        """,
        expected_output="Matriz de features, comparação de pricing, insights de pricing e mapa de posicionamento",
        agent=analista_pricing,
    )

    # --- Task 4: Estratégia e Battle Cards ---
    estrategia = Task(
        description=f"""
        CONTEXTO DA ANÁLISE:
        {context}

        SEU TRABALHO — SÍNTESE ESTRATÉGICA:
        Com base em todo o material produzido (mercado, perfis, pricing/posicionamento):

        1. **Executive Summary**: 3-4 frases com os principais achados e implicações
           estratégicas + 3 key takeaways
        2. **SWOT**: forças, fraquezas, oportunidades e ameaças da [sua empresa]
        3. **Vantagens Competitivas**: suas vantagens vs. cada concorrente, e onde
           cada concorrente se destaca
        4. **Recomendações Estratégicas**: ações imediatas, estratégia de médio prazo,
           e respostas competitivas a vigiar
        5. **Battle Cards**: para cada concorrente — quando aparecem, pitch deles,
           nossa resposta, diferenciais-chave, temas de vitória e tratamento de objeções

        Por fim, emita o **veredito de completude**: PASS ou FAIL.
        Se FAIL, liste o que falta para o relatório ser considerado completo.

        FORMATO DE SAÍDA:
        ## Executive Summary
        ## SWOT Summary
        ## Competitive Advantages
        ## Strategic Recommendations
        ## Battle Cards
        ## Quality Gate: PASS/FAIL
        """,
        expected_output="Relatório estratégico completo: executive summary, SWOT, vantagens, recomendações, battle cards e veredito PASS/FAIL",
        agent=estrategista,
    )

    # --- Crew ---
    crew = Crew(
        agents=[analista_mercado, analista_competidores, analista_pricing, estrategista],
        tasks=[mercado, perfis, pricing, estrategia],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-competitive-analysis: Análise Competitiva Crew (self-contained)",
    )
    parser.add_argument(
        "context",
        nargs="?",
        help="Contexto da análise: sua empresa/produto, concorrentes, indústria, escopo",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com o contexto (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o relatório de análise competitiva",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    # --- Resolve contexto ---
    context = None
    if args.input_file:
        context = Path(args.input_file).read_text(encoding="utf-8")
    elif args.context:
        context = args.context
    else:
        parser.print_help()
        print("\n❌ Erro: forneça o contexto da análise (argumento ou --input)")
        sys.exit(1)

    output_path = args.output

    print(f"\n📋 Contexto: {context[:120]}...")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(context, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de análise competitiva...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Relatório de Análise Competitiva gerado!\n")
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
        out_file = output_dir / f"analise-competitiva_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()