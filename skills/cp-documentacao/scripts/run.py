#!/usr/bin/env python3
"""
cp-documentacao — Documentação de Software Crew (self-contained)

Cria uma crew CrewAI com agentes especializados para gerar documentação
técnica, de API, de usuário e diagramas de software.

Uso:
  python run.py "API de agendamento para clínicas"
  python run.py --input descricao.txt --output docs/completa.md
  python run.py "API REST de pedidos" --mode tech
  python run.py "sistema de e-commerce" --mode diagrams --dry-run
"""

import argparse
import sys
import json
import os
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
# AGENTES EMBUTIDOS (self-contained)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "redator-tecnico": {
        "role": "Redator Técnico",
        "goal": (
            "Analisar o que precisa ser documentado e produzir documentação "
            "técnica e de API clara, completa e útil para desenvolvedores"
        ),
        "backstory": (
            "Redator técnico sênior com mais de 12 anos de experiência em "
            "documentação de software. Você transforma código complexo, "
            "arquiteturas intrincadas e APIs cheias de detalhes em "
            "documentação clara, precisa e acionável. "
            "Você entende tanto de tecnologia quanto de comunicação — "
            "sabe explicar conceitos complexos sem simplificar demais. "
            "Seus READMEs são referência, suas docs de API são tão boas "
            "que desenvolvedores não precisam ler o código fonte. "
            "Você documenta: arquitetura, componentes, fluxos de dados, "
            "decisões técnicas, endpoints, schemas, autenticação, "
            "exemplos de requisição/resposta, códigos de erro e boas práticas."
        ),
    },
    "redator-de-usuario": {
        "role": "Redator de Usuário",
        "goal": (
            "Produzir manuais, guias, FAQs e tutoriais que qualquer "
            "usuário final consiga entender e seguir"
        ),
        "backstory": (
            "Redator especializado em documentação para o usuário final. "
            "Você tem o dom raro de traduzir jargão técnico em linguagem "
            "simples e acessível. Seu lema: 'Se o usuário precisa de um "
            "tutorial para entender o tutorial, você falhou.' "
            "Você escreve guias de instalação passo a passo, manuais de "
            "uso com exemplos práticos, FAQs que realmente respondem "
            "as perguntas que os usuários fazem, e tutoriais que "
            "funcionam na primeira tentativa. "
            "Você sempre inclui: pré-requisitos, instruções claras, "
            "exemplos do mundo real, solução de problemas comuns e "
            "glossário de termos."
        ),
    },
    "diagramador": {
        "role": "Diagramador",
        "goal": (
            "Criar diagramas, fluxogramas e visuais que comunicam "
            "arquitetura e fluxos de forma clara e intuitiva"
        ),
        "backstory": (
            "Designer técnico especializado em comunicação visual. "
            "Você sabe que um bom diagrama vale mais que mil palavras "
            "de documentação. Você cria diagramas em Mermaid e PlantUML "
            "que são autoexplicativos, bonitos e precisos. "
            "Você produz: diagramas de arquitetura do sistema, "
            "diagramas de sequência para fluxos de API, "
            "diagramas entidade-relacionamento para o banco de dados, "
            "fluxogramas de processos de negócio, "
            "diagramas de componentes e implantação. "
            "Cada diagrama que você cria tem: título, legenda quando "
            "necessário, cores consistentes, e anotações explicativas. "
            "Seus diagramas são tão bons que viram referência no projeto."
        ),
    },
    "revisor-de-documentacao": {
        "role": "Revisor de Documentação",
        "goal": (
            "Revisar toda a documentação para garantir clareza, "
            "completude, consistência e correção ortográfica"
        ),
        "backstory": (
            "Revisor detalhista e implacável com mais de 15 anos de "
            "experiência em documentação técnica. Você não deixa passar "
            "nenhum erro de português, informação faltando, "
            "inconsistência entre seções, ou ambiguidade. "
            "Você verifica: ortografia e gramática, clareza e "
            "objetividade, completude (nada ficou de fora?), "
            "consistência (termos usados da mesma forma em todo o "
            "documento?), exemplos funcionais, links e referências "
            "cruzadas, tom e voz adequados ao público-alvo. "
            "Seu veredito é PASS ou FAIL. Se FAIL, você lista "
            "exatamente o que precisa ser corrigido. "
            "Você é exigente mas justo — documentação de qualidade "
            "é um direito de quem usa o software."
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

def build_crew(descricao: str, mode: str = "full", output_path: str = None):
    """Build a CrewAI crew for software documentation."""

    redator_tecnico = get_agent("redator-tecnico")
    redator_usuario = get_agent("redator-de-usuario")
    diagramador = get_agent("diagramador")
    revisor = get_agent("revisor-de-documentacao")

    # --- Task 1: Análise (sempre presente) ---
    analise = Task(
        description=f"""
        DESCRIÇÃO DO QUE DOCUMENTAR:
        {descricao}

        SEU TRABALHO — ANÁLISE DO ESCOPO DE DOCUMENTAÇÃO:
        1. Analise a descrição fornecida e identifique:
           - O que é o software/sistema/API
           - Público-alvo da documentação (desenvolvedores, usuários finais, ambos)
           - Tecnologias envolvidas
           - Funcionalidades principais
           - Endpoints/APIs (se aplicável)
           - Fluxos de dados
        2. Defina o escopo da documentação necessária
        3. Identifique seções obrigatórias
        4. Liste suposições e informações que precisam de confirmação

        FORMATO DE SAÍDA:
        ## Análise de Escopo de Documentação
        - Software/Sistema: [descrição]
        - Público-alvo: [quem]
        - Tecnologias: [lista]
        - Funcionalidades: [lista]
        - Seções de documentação necessárias: [lista]
        - Suposições: [lista]
        - Informações faltantes: [lista]
        """,
        expected_output=(
            "Análise completa do escopo de documentação: software, "
            "público-alvo, tecnologias, funcionalidades, seções necessárias, "
            "suposições e informações faltantes"
        ),
        agent=redator_tecnico,
    )

    tasks = [analise]

    # --- Task 2: Documentação Técnica e de API ---
    if mode in ("full", "tech", "api"):
        doc_tecnica = Task(
            description=f"""
            DESCRIÇÃO DO QUE DOCUMENTAR:
            {descricao}

            SEU TRABALHO — DOCUMENTAÇÃO TÉCNICA E DE API:
            Com base na análise de escopo, produza a documentação técnica completa:

            1. **README** — Visão geral do projeto, propósito, status, como contribuir
            2. **Arquitetura** — Descrição da arquitetura, componentes, padrões usados
            3. **Tecnologias** — Stack tecnológica com versões
            4. **Estrutura do Projeto** — Organização de diretórios e módulos
            5. **Configuração** — Variáveis de ambiente, dependências, setup
            6. **Instalação e Execução** — Passo a passo para rodar o projeto
            7. **Testes** — Como executar e interpretar os testes

            Se aplicável (modo full ou api), inclua também:
            8. **Documentação de API** — Para cada endpoint:
               - Método HTTP e URL
               - Descrição do que faz
               - Parâmetros (path, query, body)
               - Headers (autenticação, content-type)
               - Exemplo de requisição (curl)
               - Exemplo de resposta (JSON)
               - Códigos de erro possíveis
               - Rate limiting (se aplicável)

            Escreva em português claro e objetivo. Use markdown.
            Inclua blocos de código com syntax highlighting.
            """,
            expected_output=(
                "Documentação técnica completa: README, arquitetura, "
                "tecnologias, estrutura, configuração, instalação, testes "
                "e documentação de API (quando aplicável)"
            ),
            agent=redator_tecnico,
        )
        tasks.append(doc_tecnica)

    # --- Task 3: Documentação de Usuário ---
    if mode in ("full", "user"):
        doc_usuario = Task(
            description=f"""
            DESCRIÇÃO DO QUE DOCUMENTAR:
            {descricao}

            SEU TRABALHO — DOCUMENTAÇÃO DE USUÁRIO:
            Com base na análise de escopo e documentação técnica, produza
            a documentação voltada para o usuário final:

            1. **Guia de Início Rápido** — O mínimo que o usuário precisa
               saber para começar a usar em 5 minutos
            2. **Manual do Usuário** — Funcionalidades principais explicadas
               passo a passo com exemplos práticos
            3. **FAQ** — Perguntas frequentes com respostas claras e diretas
            4. **Solução de Problemas** — Problemas comuns e como resolver
            5. **Glossário** — Termos técnicos explicados em linguagem simples

            Regras:
            - Linguagem simples e acessível (evite jargão técnico)
            - Exemplos do mundo real que o usuário reconhece
            - Passos numerados para ações sequenciais
            - Screenshots descritas em texto (ex: "Clique no botão 'Salvar'")
            - Tom amigável e paciente
            - Cada seção deve ser independente (o usuário pode pular seções)

            Escreva em português claro. Use markdown.
            """,
            expected_output=(
                "Documentação de usuário completa: guia de início rápido, "
                "manual do usuário, FAQ, solução de problemas e glossário"
            ),
            agent=redator_usuario,
        )
        tasks.append(doc_usuario)

    # --- Task 4: Diagramas ---
    if mode in ("full", "diagrams"):
        diagramas = Task(
            description=f"""
            DESCRIÇÃO DO QUE DOCUMENTAR:
            {descricao}

            SEU TRABALHO — DIAGRAMAS E VISUAIS:
            Com base na análise de escopo e na documentação produzida, crie
            diagramas que comunicam visualmente a arquitetura e os fluxos:

            Crie diagramas usando Mermaid (formato markdown com blocos ```mermaid):

            1. **Diagrama de Arquitetura** — Visão geral dos componentes
               do sistema e como se comunicam (graph TD ou C4 diagram)
            2. **Diagrama de Sequência** — Fluxo principal de uma operação
               típica (sequenceDiagram)
            3. **Diagrama Entidade-Relacionamento** — Principais entidades
               e seus relacionamentos (erDiagram)
            4. **Fluxograma de Processo** — Fluxo de uso do sistema
               pelo usuário (flowchart)
            5. **Diagrama de Implantação** — Como o sistema é implantado
               (se aplicável)

            Para cada diagrama, inclua:
            - Título descritivo
            - O código Mermaid dentro de bloco ```mermaid
            - Breve explicação do que o diagrama mostra
            - Legenda quando necessário

            Se o sistema tiver muitos componentes, foque nos principais.
            Qualidade > quantidade.
            """,
            expected_output=(
                "Conjunto de diagramas Mermaid: arquitetura, sequência, "
                "entidade-relacionamento, fluxograma e implantação, "
                "cada um com título e explicação"
            ),
            agent=diagramador,
        )
        tasks.append(diagramas)

    # --- Task 5: Revisão (sempre presente) ---
    revisao = Task(
        description=f"""
        DESCRIÇÃO DO QUE DOCUMENTAR:
        {descricao}

        SEU TRABALHO — REVISÃO FINAL DA DOCUMENTAÇÃO:
        Revise toda a documentação produzida e verifique:

        1. **Ortografia e Gramática** — Erros de português?
        2. **Clareza** — Cada seção é clara e objetiva?
        3. **Completude** — Algo importante ficou de fora?
        4. **Consistência** — Termos usados da mesma forma em todo o documento?
        5. **Tom e Voz** — Adequado ao público-alvo de cada seção?
        6. **Exemplos** — Os exemplos estão corretos e funcionam?
        7. **Links e Referências** — Referências cruzadas estão corretas?
        8. **Diagramas** — Estão claros e bem explicados?

        Para cada problema encontrado, documente:
        - O problema específico (com localização aproximada)
        - Por que é um problema
        - Sugestão de correção

        Emita um veredito: PASS ou FAIL.
        Se PASS: a documentação está pronta para publicação.
        Se FAIL: liste exatamente o que precisa ser corrigido antes da aprovação.
        """,
        expected_output=(
            "Relatório de revisão: problemas encontrados (se houver), "
            "sugestões de correção, e veredito PASS/FAIL"
        ),
        agent=revisor,
    )
    tasks.append(revisao)

    # --- Crew ---
    crew = Crew(
        agents=[redator_tecnico, redator_usuario, diagramador, revisor],
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
        description="cp-documentacao: Documentação de Software Crew (self-contained)",
    )
    parser.add_argument(
        "descricao",
        nargs="?",
        help="Descrição do que documentar (software, API, sistema)",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar a documentação completa",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "tech", "user", "api", "diagrams"],
        default="full",
        help=(
            "Modo de documentação: "
            "full (completa, padrão), "
            "tech (técnica + API), "
            "user (usuário), "
            "api (apenas API), "
            "diagrams (apenas diagramas)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    # --- Resolve descrição ---
    descricao = None
    if args.input_file:
        descricao = Path(args.input_file).read_text(encoding="utf-8")
    elif args.descricao:
        descricao = args.descricao
    else:
        parser.print_help()
        print("\n❌ Erro: forneça a descrição do que documentar (argumento ou --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    mode_names = {
        "full": "Documentação Completa",
        "tech": "Documentação Técnica e de API",
        "user": "Documentação de Usuário",
        "api": "Documentação de API",
        "diagrams": "Diagramas e Visuais",
    }

    print(f"\n📋 Descrição: {descricao[:120]}...")
    print(f"📂 Modo: {mode_names.get(mode, mode)}")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(descricao, mode, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for slug, data in AGENTS.items():
            print(f"  - {data['role']}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            print(f"  {i}. {task.description[:80]}...")
        print("\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de documentação...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Documentação gerada!\n")
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
        mode_suffix = mode if mode != "full" else "completa"
        out_file = output_dir / f"documentacao_{mode_suffix}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()