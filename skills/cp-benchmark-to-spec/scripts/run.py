#!/usr/bin/env python3
"""
cp-benchmark-to-spec — Benchmark para Especificação Técnica (self-contained)

Transforma um produto de referência em documentação técnica completa e replicável.
Recebe insumos (URLs, pesquisa web, screenshots), faz crawler da documentação,
extrai o design system das telas e gera a especificação RUP + gestão de projeto.

Uso:
  python run.py "produto: Attio; URL: https://attio.com/help/reference"
  python run.py --context "produto X" --output ./spec
  python run.py --input contexto.txt
"""

import argparse
import sys
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
# AGENTES EMBUTIDOS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "analista-de-documentacao": {
        "role": "Analista de Documentação",
        "goal": "Fazer crawler da documentação do produto de referência e extrair o conteúdo-fonte completo",
        "backstory": (
            "Analista de documentação experiente em engenharia reversa de produtos. "
            "Você sabe extrair o máximo de informação de documentações públicas, "
            "arquivos llms.txt e páginas web. Você identifica a estrutura do produto "
            "(módulos, features, integrações) e organiza o conteúdo-fonte de forma "
            "que um especificador técnico possa trabalhar. Você prioriza eficiência: "
            "se o produto oferece um arquivo llms.txt/llms-full.txt, você o usa em "
            "vez de raspar página por página. Seu lema: 'Documentação boa é a que "
            "pode ser reconstruída.'"
        ),
    },
    "analista-de-design": {
        "role": "Analista de Design",
        "goal": "Analisar screenshots do produto e extrair o design system completo (cores, tipografia, componentes)",
        "backstory": (
            "Analista de design com olho clínico para design systems. Você extrai de "
            "screenshots os tokens de UI: paleta de cores (hex), tipografia (fontes, "
            "tamanhos, pesos), espaçamentos, bordas, raios, sombras, ícones, botões, "
            "inputs, tabelas, badges. Você consolida as análises de poucas telas-chave "
            "em vez de analisar imagem por imagem, evitando loops. Você marca valores "
            "estimados como tal e recomenda validar contra o CSS real. Seu lema: "
            "'Consistência visual é o que faz um produto parecer profissional.'"
        ),
    },
    "especificador-tecnico": {
        "role": "Especificador Técnico",
        "goal": "Gerar a especificação RUP completa (4 fases) a partir do conteúdo-fonte, referenciando sem duplicar",
        "backstory": (
            "Especificador técnico sênior com domínio de arquitetura de software. "
            "Você transforma conteúdo-fonte de um produto de referência em documentação "
            "técnica completa e replicável: visão, atores, requisitos, glossário, "
            "arquitetura, casos de uso, schema, especificações por módulo, API, "
            "frontend, testes, deploy e treinamento. Você organiza por fases RUP "
            "(Inception, Elaboration, Construction, Transition) e garante que cada "
            "documento referencie os demais sem duplicar conteúdo. Você emite o "
            "veredito final de completude (PASS/FAIL)."
        ),
    },
    "gestor-de-projeto": {
        "role": "Gestor de Projeto",
        "goal": "Gerar épicos, histórias, tasks e roadmap referenciando a especificação técnica",
        "backstory": (
            "Gestor de projeto experiente em transformar especificações técnicas em "
            "planos de execução. Você cria épicos (EP), histórias (HS) e tasks (TSK) "
            "que referenciam os documentos técnicos sem duplicar conteúdo. Você define "
            "o roadmap de entregas com fases e marcos, e garante a rastreabilidade "
            "Épico → História → Task → Caso de Uso → Requisito → Especificação. "
            "Seu lema: 'Um bom plano é aquele que o time consegue executar.'"
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
    """Build a CrewAI crew for benchmark-to-spec."""

    analista_doc = get_agent("analista-de-documentacao")
    analista_design = get_agent("analista-de-design")
    especificador = get_agent("especificador-tecnico")
    gestor = get_agent("gestor-de-projeto")

    # --- Task 1: Crawler da documentação ---
    crawler = Task(
        description=f"""
        CONTEXTO (INSUMOS DO PRODUTO DE REFERÊNCIA):
        {context}

        SEU TRABALHO — CRAWLER DA DOCUMENTAÇÃO:
        1. Identifique o produto de referência e suas URLs de documentação
        2. Se o produto oferecer um arquivo llms.txt/llms-full.txt, use-o (é o mais eficiente)
        3. Caso contrário, navegue nas páginas de documentação e extraia o texto
        4. Mapeie a estrutura do produto: módulos, features, integrações, conceitos-chave
        5. Organize o conteúdo-fonte de forma que um especificador técnico possa trabalhar

        FORMATO DE SAÍDA:
        ## Produto de Referência
        - Nome, categoria, posicionamento
        ## Estrutura do Produto
        - Módulos/features principais
        ## Conceitos-chave
        - Terminologia do domínio
        ## Conteúdo-fonte
        - Resumo do que foi extraído e onde está
        """,
        expected_output="Produto identificado, estrutura mapeada, conceitos-chave e conteúdo-fonte organizado",
        agent=analista_doc,
    )

    # --- Task 2: Design System ---
    design = Task(
        description=f"""
        CONTEXTO (INSUMOS DO PRODUTO DE REFERÊNCIA):
        {context}

        SEU TRABALHO — DESIGN SYSTEM:
        Com base nos screenshots do produto (se fornecidos) e no conteúdo-fonte:

        1. **Paleta de cores** — cores de marca, neutras, semânticas (hex)
        2. **Tipografia** — fontes, tamanhos, pesos, hierarquia
        3. **Espaçamento** — grid base, aplicações
        4. **Bordas e raios** — valores por componente
        5. **Sombras** — níveis de elevação
        6. **Ícones** — estilo, tamanhos
        7. **Componentes** — botões, inputs, tabelas, badges, cards, sidebar, topbar
        8. **Micro-interações** — transições, hovers

        Consolide a análise de poucas telas-chave. Marque valores estimados como tal.

        FORMATO DE SAÍDA:
        ## Design System
        - Paleta de cores (tokens)
        - Tipografia (escala)
        - Espaçamento, bordas, raios, sombras
        - Componentes de UI
        - Micro-interações
        """,
        expected_output="Design system completo com tokens de cor, tipografia, espaçamento, componentes e micro-interações",
        agent=analista_design,
    )

    # --- Task 3: Especificação RUP ---
    spec = Task(
        description=f"""
        CONTEXTO (INSUMOS DO PRODUTO DE REFERÊNCIA):
        {context}

        SEU TRABALHO — ESPECIFICAÇÃO RUP COMPLETA:
        Com base no conteúdo-fonte e no design system, gere a especificação técnica
        completa para o time reconstruir o produto. Organize por fases RUP:

        **Fase 1 — Inception (`01-inception/`):**
        - `00-visao-do-produto.md` — visão, problema, solução, público-alvo, diferenciais
        - `01-atores.md` — atores e papéis
        - `02-requisitos-gerais.md` — requisitos funcionais (RF) e não funcionais (RNF)
        - `03-glossario.md` — terminologia do domínio

        **Fase 2 — Elaboration (`02-elaboration/`):**
        - `04-arquitetura-de-sistema.md` — arquitetura (backend/frontend/banco)
        - `casos-de-uso/` — casos de uso detalhados por domínio

        **Fase 3 — Construction (`03-construction/`):**
        - `schema/` — modelo de dados PostgreSQL + migrations
        - `especificacao/` — detalhamento técnico por módulo
        - `api/` — especificação REST + WebSocket
        - `frontend/` — componentes React, páginas, tipos

        **Fase 4 — Transition (`04-transition/`):**
        - `05-plano-de-testes.md` — testes por nível
        - `06-deploy-e-infra.md` — deploy, CI/CD, infraestrutura
        - `07-treinamento.md` — treinamento

        **Design System (raiz):**
        - `design-system.md` — especificação de UI/UX

        REGRAS:
        - Cada documento referencia os demais, NÃO duplica conteúdo
        - Use PT-BR para documentação de produto; códigos/payloads em inglês
        - Marque itens não documentados na fonte como "não documentado na fonte"
        - Stack alvo: Django REST + React/Vite/TS + PostgreSQL + Redis + Celery

        Por fim, emita o **veredito de completude**: PASS ou FAIL.
        Se FAIL, liste o que falta.

        FORMATO DE SAÍDA:
        ## Especificação RUP
        - Fase 1: Inception (documentos)
        - Fase 2: Elaboration (documentos)
        - Fase 3: Construction (documentos)
        - Fase 4: Transition (documentos)
        - Design System
        ## Quality Gate: PASS/FAIL
        """,
        expected_output="Especificação RUP completa (4 fases) + design system, com veredito PASS/FAIL",
        agent=especificador,
    )

    # --- Task 4: Gestão de Projeto ---
    projeto = Task(
        description=f"""
        CONTEXTO (INSUMOS DO PRODUTO DE REFERÊNCIA):
        {context}

        SEU TRABALHO — GESTÃO DE PROJETO:
        Com base na especificação RUP, gere a gestão de projeto em `05-project-management/`:

        - `README.md` — visão geral, convenções de ID, mapeamento épico→UC→docs
        - `01-epicos.md` — épicos (EP-XX) por domínio, com referências técnicas
        - `02-historias.md` — histórias (HS) com critérios de aceite vinculados aos casos de uso
        - `03-tasks.md` — tasks (TSK) com referências técnicas de implementação
        - `04-roadmap.md` — fases de entrega, dependências e marcos

        REGRAS:
        - Cada épico/história/task referencia os documentos técnicos, NÃO duplica
        - Rastreabilidade: Épico → História → Task → Caso de Uso → Requisito → Especificação
        - Use PT-BR

        FORMATO DE SAÍDA:
        ## Gestão de Projeto
        - Épicos (EP-XX)
        - Histórias (HS-XX)
        - Tasks (TSK-XX)
        - Roadmap (fases e marcos)
        """,
        expected_output="Gestão de projeto completa: épicos, histórias, tasks e roadmap referenciando a spec",
        agent=gestor,
    )

    # --- Crew ---
    crew = Crew(
        agents=[analista_doc, analista_design, especificador, gestor],
        tasks=[crawler, design, spec, projeto],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-benchmark-to-spec: Benchmark para Especificação Técnica (self-contained)",
    )
    parser.add_argument(
        "context",
        nargs="?",
        help="Insumos do produto de referência: URLs, pesquisa, screenshots, pedido",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com o contexto (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Pasta de saída para salvar a especificação (default: doc_dev/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: mensagem acionavel em vez de traceback

    # --- Resolve contexto ---
    context = None
    if args.input_file:
        context = Path(args.input_file).read_text(encoding="utf-8")
    elif args.context:
        context = args.context
    else:
        parser.print_help()
        print("\n❌ Erro: forneça o contexto (argumento ou --input)")
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

    print("🚀 Executando crew de benchmark-to-spec...\n")
    require_llm()  # DT-08: falha cedo, com mensagem, se nao ha LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Especificação Técnica gerada!\n")
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
        out_file = output_dir / f"benchmark-to-spec_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()
