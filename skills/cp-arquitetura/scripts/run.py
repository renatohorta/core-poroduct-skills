#!/usr/bin/env python3
"""
cp-arquitetura — Arquitetura e Design de Software Crew (self-contained)

Cria uma crew CrewAI com agentes especializados para definir arquitetura,
modelar dados, desenhar APIs, projetar UX e validar decisões técnicas.

Uso:
  python run.py "sistema de agendamento para clínicas"
  python run.py --briefing "preciso de um app para gerenciar estoque" --output arquitetura.md
  python run.py --input requisitos.md
"""

import argparse
import sys
import json
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
    "arquiteto-de-software": {
        "role": "Arquiteto de Software",
        "goal": "Definir a arquitetura do sistema, padrões, estilos arquiteturais e documentar decisões em ADRs",
        "backstory": (
            "Arquiteto de software sênior com mais de 15 anos de experiência em projetos de todos os portes. "
            "Você já viu sistemas nascerem, crescerem e morrerem por más decisões arquiteturais. "
            "Domina estilos como monolito, microsserviços, modular monolith, event-driven architecture, "
            "e hexagonal architecture. Você sabe que não existe bala de prata — cada decisão tem trade-offs. "
            "Documenta cada decisão como ADR (Architecture Decision Record) com contexto, decisão e consequências. "
            "Pensa em escalabilidade, manutenibilidade, acoplamento e coesão antes de escrever uma linha de código."
        ),
    },
    "arquiteto-de-dados": {
        "role": "Arquiteto de Dados",
        "goal": "Modelar o banco de dados, definir schema, relacionamentos, índices e estratégia de migração",
        "backstory": (
            "DBA e arquiteto de dados com vasta experiência em modelagem relacional e NoSQL. "
            "Você pensa em performance e consistência desde o primeiro schema. "
            "Conhece normalização, desnormalização estratégica, índices compostos, particionamento, "
            "e estratégias de migração (zero-downtime, blue-green). "
            "Sabe quando usar SQL vs NoSQL, quando denormalizar por performance, "
            "e como modelar dados para suportar consultas futuras sem reescrever o schema. "
            "Seu lema: 'Um schema bem modelado economiza meses de refatoração.'"
        ),
    },
    "arquiteto-de-api": {
        "role": "Arquiteto de API",
        "goal": "Desenhar contratos de API REST/GraphQL, especificar endpoints, payloads, versionamento e segurança",
        "backstory": (
            "Especialista em design de APIs que já integrou dezenas de sistemas ao longo da carreira. "
            "Você domina REST, GraphQL, gRPC e WebSockets. "
            "Projeta APIs pensando em consistência, versionamento semântico, paginação, "
            "rate limiting, autenticação e documentação (OpenAPI/Swagger). "
            "Sabe que uma boa API é intuitiva — o consumidor não precisa ler documentação para adivinhar o endpoint. "
            "Defende contratos fortes com validação rigorosa e mensagens de erro claras. "
            "Seu mantra: 'API design é UX para desenvolvedores.'"
        ),
    },
    "ux-architect": {
        "role": "UX Architect",
        "goal": "Desenhar fluxos de usuário, jornadas, protótipos de navegação e validar a experiência antes do código",
        "backstory": (
            "Arquiteto de experiência do usuário que pensa na jornada antes do código. "
            "Você mapeia fluxos completos (user flows), identifica pontos de atrito, "
            "e desenha protótipos de navegação que guiam o desenvolvimento. "
            "Trabalha com conceitos como jornada do usuário, telas, estados (loading, empty, error, edge cases), "
            "e princípios de usabilidade (heurísticas de Nielsen). "
            "Sabe que uma experiência ruim pode matar um produto tecnicamente perfeito. "
            "Seu objetivo: garantir que a arquitetura suporte a experiência, não o contrário."
        ),
    },
    "revisor-tecnico": {
        "role": "Revisor Técnico",
        "goal": "Validar decisões arquiteturais, identificar riscos, apontar inconsistências e sugerir alternativas",
        "backstory": (
            "Engenheiro de software sênior cético que questiona todas as decisões. "
            "Você já viu arquiteturas bonitas no papel falharem na prática. "
            "Analisa cada decisão com lupa: escalabilidade, custo operacional, complexidade acidental, "
            "time-to-market, dívida técnica, e alinhamento com os requisitos. "
            "Não aceita 'sempre fizemos assim' como justificativa. "
            "Seu trabalho não é aprovar cegamente — é garantir que o time tenha considerado "
            "os riscos e trade-offs antes de implementar. "
            "Emita PASS apenas se a arquitetura for sólida, documentada e justificada."
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

def build_crew(briefing: str, output_path: str = None):
    """Build a CrewAI crew for software architecture and design."""

    arquiteto = get_agent("arquiteto-de-software")
    dados = get_agent("arquiteto-de-dados")
    api = get_agent("arquiteto-de-api")
    ux = get_agent("ux-architect")
    revisor = get_agent("revisor-tecnico")

    # --- Task 1: Análise de requisitos e definição de arquitetura ---
    task_arquitetura = Task(
        description=f"""
        BRIEFING / REQUISITOS DO SISTEMA:
        {briefing}

        SEU TRABALHO — DEFINIÇÃO DE ARQUITETURA:

        Com base nos requisitos fornecidos, produza:

        1. **Análise de Requisitos Arquiteturais**
           - Requisitos funcionais críticos que impactam a arquitetura
           - Requisitos não-funcionais (performance, escalabilidade, segurança, disponibilidade)
           - Restrições técnicas e de negócio

        2. **Decisão Arquitetural (ADR 001)**
           - Contexto: por que essa decisão é necessária
           - Decisão: estilo arquitetural escolhido (monolito, microsserviços, modular monolith, etc.)
           - Consequências: prós, contras, trade-offs
           - Alternativas consideradas e por que foram descartadas

        3. **Diagrama C4 — Nível 1 (Contexto)**
           - Descreva o sistema e seus usuários/atores externos
           - Relacionamentos entre o sistema e o mundo externo

        4. **Diagrama C4 — Nível 2 (Containers)**
           - Quais containers/aplicações compõem o sistema
           - Responsabilidades de cada container
           - Comunicação entre containers (protocolos, síncrono/assíncrono)

        5. **Padrões Arquiteturais**
           - Padrões escolhidos (ex: CQRS, Event Sourcing, Saga, Repository, etc.)
           - Justificativa para cada padrão

        6. **ADR 002: Tecnologias**
           - Stack principal (linguagem, framework, banco, message broker, etc.)
           - Justificativa para cada escolha tecnológica

        Formato: markdown com seções claras. Cada ADR deve seguir o formato:
        ## ADR-N: Título
        - **Contexto**: ...
        - **Decisão**: ...
        - **Consequências**: ...
        - **Alternativas**: ...
        """,
        expected_output="Documento de arquitetura: análise de requisitos arquiteturais, ADRs, diagrama C4 níveis 1-2, padrões e stack tecnológica",
        agent=arquiteto,
    )

    # --- Task 2: Modelagem de dados ---
    task_dados = Task(
        description=f"""
        BRIEFING / REQUISITOS DO SISTEMA:
        {briefing}

        SEU TRABALHO — MODELAGEM DE DADOS:

        Com base na arquitetura definida, produza:

        1. **Modelo Conceitual**
           - Entidades principais do domínio
           - Relacionamentos entre entidades (1:N, N:N, 1:1)
           - Cardinalidades

        2. **Modelo Lógico (Schema)**
           - Tabelas/coleções com colunas/campos
           - Tipos de dados
           - Chaves primárias e estrangeiras
           - Índices recomendados (simples e compostos)
           - Constraints e regras de integridade

        3. **Estratégia de Armazenamento**
           - SQL vs NoSQL: justificativa
           - Se relacional: diagrama entidade-relacionamento (textual)
           - Se NoSQL: documento/agregado, padrões de acesso
           - Estratégia de particionamento (se aplicável)

        4. **Migrações**
           - Estratégia de migração (zero-downtime?)
           - Versionamento de schema
           - Rollback plan

        5. **Considerações de Performance**
           - Índices mais importantes
           - Consultas críticas e como otimizá-las
           - Estratégia de cache (se aplicável)

        Formato: markdown com tabelas para entidades e índices.
        """,
        expected_output="Modelo de dados completo: entidades, schema, índices, estratégia de armazenamento e migração",
        agent=dados,
    )

    # --- Task 3: Design de API ---
    task_api = Task(
        description=f"""
        BRIEFING / REQUISITOS DO SISTEMA:
        {briefing}

        SEU TRABALHO — DESIGN DE API:

        Com base na arquitetura e no modelo de dados definidos, produza:

        1. **Estratégia de API**
           - REST, GraphQL, gRPC ou híbrido? Justificativa
           - Versionamento (URL, header, ou semântico)
           - Formato de resposta padrão

        2. **Contratos de API**
           Para cada endpoint/operação:
           - Método HTTP e path
           - Parâmetros (query, path, body)
           - Request payload (exemplo)
           - Response payload (exemplo)
           - Códigos de status (200, 201, 400, 404, 500, etc.)
           - Autenticação/autorização necessária

        3. **Tratamento de Erros**
           - Formato de erro padronizado
           - Códigos de erro de negócio
           - Mensagens amigáveis

        4. **Paginação, Filtros e Ordenação**
           - Estratégia de paginação (cursor vs offset)
           - Padrão de filtros
           - Padrão de ordenação

        5. **Segurança**
           - Autenticação (JWT, OAuth2, API Key?)
           - Rate limiting
           - Validação de entrada
           - Proteção contra ataques comuns

        6. **Documentação**
           - OpenAPI/Swagger: descrição dos schemas
           - Exemplos de requisição e resposta para cada endpoint

        Formato: markdown com exemplos JSON para payloads.
        """,
        expected_output="Contratos de API completos: endpoints, payloads, erros, paginação, segurança e documentação OpenAPI",
        agent=api,
    )

    # --- Task 4: Design de UX/Fluxos ---
    task_ux = Task(
        description=f"""
        BRIEFING / REQUISITOS DO SISTEMA:
        {briefing}

        SEU TRABALHO — DESIGN DE UX / FLUXOS DE USUÁRIO:

        Com base na arquitetura, dados e APIs definidos, produza:

        1. **Personas / Perfis de Usuário**
           - Quem são os usuários do sistema
           - Objetivos de cada perfil
           - Nível de conhecimento técnico

        2. **User Flows (Fluxos de Usuário)**
           Para cada funcionalidade principal:
           - Fluxo feliz (happy path)
           - Fluxos alternativos
           - Fluxos de erro
           - Pontos de decisão

        3. **Mapa de Navegação**
           - Telas/views principais
           - Transições entre telas
           - Hierarquia de navegação

        4. **Estados de Interface**
           - Estado inicial / vazio (empty state)
           - Estado de carregamento (loading state)
           - Estado de erro (error state)
           - Estado de sucesso
           - Casos de borda (edge cases)

        5. **Recomendações de UX**
           - Heurísticas de usabilidade aplicáveis
           - Padrões de interação recomendados
           - Acessibilidade (WCAG)
           - Responsividade / mobile-first

        Formato: markdown com fluxos descritos textualmente (pseudo-fluxograma).
        """,
        expected_output="Documento de UX: personas, user flows, mapa de navegação, estados de interface e recomendações de usabilidade",
        agent=ux,
    )

    # --- Task 5: Revisão e validação técnica ---
    task_revisao = Task(
        description=f"""
        BRIEFING / REQUISITOS DO SISTEMA:
        {briefing}

        SEU TRABALHO — REVISÃO TÉCNICA E VALIDAÇÃO ARQUITETURAL:

        Revise TODO o documento de arquitetura produzido (arquitetura, dados, APIs, UX)
        e avalie os seguintes aspectos:

        1. **Consistência Interna**
           - A arquitetura definida é consistente com os requisitos?
           - O modelo de dados suporta as APIs desenhadas?
           - As APIs suportam os fluxos de UX projetados?
           - Há contradições entre as decisões?

        2. **Análise de Riscos**
           - Riscos técnicos identificados
           - Riscos de escalabilidade
           - Riscos de custo operacional
           - Riscos de time-to-market
           - Riscos de dívida técnica futura

        3. **Avaliação de Trade-offs**
           - Para cada decisão arquitetural, os trade-offs foram bem documentados?
           - Há alternativas que deveriam ter sido consideradas?
           - A decisão tomada é a melhor para o contexto?

        4. **Pontos de Atenção**
           - O que pode dar errado na implementação?
           - O que precisa ser validado com protótipo/PoC antes de implementar?
           - Sugestões de melhoria

        5. **Veredito Final**
           - **PASS**: A arquitetura está sólida, documentada e pronta para implementação
           - **FAIL**: A arquitetura precisa de correções antes de seguir
           - Se FAIL, liste explicitamente o que precisa ser corrigido e por quê

        Seja rigoroso. Um FAIL agora é melhor que uma crise em produção.
        """,
        expected_output="Relatório de revisão técnica: análise de riscos, trade-offs, pontos de atenção e veredito PASS/FAIL",
        agent=revisor,
    )

    # --- Crew ---
    crew = Crew(
        agents=[arquiteto, dados, api, ux, revisor],
        tasks=[task_arquitetura, task_dados, task_api, task_ux, task_revisao],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-arquitetura: Arquitetura e Design de Software Crew (self-contained)",
    )
    parser.add_argument(
        "briefing",
        nargs="?",
        help="Briefing do cliente / descrição do problema / requisitos do sistema",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com o briefing (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o documento de arquitetura",
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
        print("\n❌ Erro: forneça o briefing do sistema (argumento ou --input)")
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

    print("🚀 Executando crew de arquitetura e design...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Documento de Arquitetura gerado!\n")
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
        out_file = output_dir / f"arquitetura_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()