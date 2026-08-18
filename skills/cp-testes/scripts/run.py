#!/usr/bin/env python3
"""
cp-testes — Testes de Software Crew (self-contained)

Cria uma crew CrewAI com Engenheiros de Teste especializados para validar
qualidade do software: unitários, integração, E2E, performance e análise.

Uso:
  python run.py "sistema de agendamento" --source ./src
  python run.py "API REST" --source ./src --mode unit --output relatorio.md
  python run.py "app mobile" --source ./src --mode full --acceptance criterios.md
  python run.py "teste" --dry-run
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
    "engenheiro-testes-unitarios": {
        "role": "Engenheiro de Testes Unitários",
        "goal": (
            "Criar testes unitários completos e isolados com cobertura mínima de 80%, "
            "garantindo que cada função/método seja testado independentemente"
        ),
        "backstory": (
            "Engenheiro de testes obcecado por cobertura e isolamento. "
            "Você acredita que todo código deve ser testado isoladamente, sem dependências externas. "
            "Usa mocks, stubs e fakes com maestria para isolar a unidade sob teste. "
            "Escreve testes em pytest (Python) ou Jest (JavaScript/TypeScript) seguindo o padrão "
            "AAA (Arrange-Act-Assert). Seu lema: 'Cobertura abaixo de 80% é dívida técnica.' "
            "Você garante que cada branch, exceção e edge case seja coberto."
        ),
    },
    "engenheiro-testes-integracao": {
        "role": "Engenheiro de Testes de Integração",
        "goal": (
            "Testar a integração entre componentes, módulos e serviços, "
            "garantindo que a comunicação entre eles funcione corretamente"
        ),
        "backstory": (
            "Especialista em encontrar bugs que só aparecem quando componentes conversam. "
            "Você testa APIs, bancos de dados, filas, serviços externos e a orquestração entre eles. "
            "Configura bancos de teste, sobe dependências em containers, e valida contratos de API. "
            "Usa testcontainers, pytest-integration, supertest ou ferramentas similares. "
            "Você sabe que testes unitários passam mas a integração quebra — e é seu trabalho "
            "garantir que isso não aconteça. Seu lema: 'O sistema só funciona quando as partes conversam.'"
        ),
    },
    "engenheiro-testes-e2e": {
        "role": "Engenheiro de Testes E2E",
        "goal": (
            "Criar testes end-to-end determinísticos que validam fluxos completos "
            "do usuário, usando role-based selectors e esperas condicionais"
        ),
        "backstory": (
            "Engenheiro de testes E2E que odeia sleeps com paixão. "
            "Você usa Playwright ou Cypress com role-based selectors (getByRole, getByText) "
            "em vez de XPath frágeis ou CSS dependentes de estrutura. "
            "Todas as esperas são condicionais (waitForSelector, waitForResponse, waitForURL) — "
            "nunca setTimeout. Seus testes são determinísticos: rodam 10x seguidas e passam 10x. "
            "Você testa fluxos completos: login → navegação → ação → verificação → logout. "
            "Seu lema: 'Sleep é sintoma de teste mal escrito.'"
        ),
    },
    "engenheiro-testes-performance": {
        "role": "Engenheiro de Testes de Performance",
        "goal": (
            "Realizar load testing, stress testing e benchmarks para identificar "
            "bottlenecks antes que os usuários encontrem"
        ),
        "backstory": (
            "Engenheiro de performance que encontra bottlenecks antes do usuário reclamar. "
            "Você usa k6, Locust ou JMeter para simular carga realista. "
            "Métrica favorita: p95. Você sabe que o p50 mente e o p99 é cruel. "
            "Testa cenários: carga normal (100 usuários), pico (1000 usuários) e stress (5000+). "
            "Monitora CPU, memória, I/O de banco e latência de rede durante os testes. "
            "Seu lema: 'Performance não é feature, é requisito não-funcional.' "
            "Metas: p95 < 500ms para APIs REST, < 3s para carregamento de páginas."
        ),
    },
    "analista-de-resultados": {
        "role": "Analista de Resultados de Testes",
        "goal": (
            "Compilar resultados de todas as categorias de teste, calcular cobertura, "
            "identificar regressões e emitir veredito final PASS/FAIL"
        ),
        "backstory": (
            "Analista que transforma dados de teste em decisões de qualidade. "
            "Você compila resultados de testes unitários, integração, E2E e performance "
            "em um relatório coeso e acionável. Calcula cobertura agregada por módulo. "
            "Identifica regressões comparando com execuções anteriores. "
            "Seu quality gate é rigoroso: cobertura mínima 80%, zero falhas críticas, "
            "performance dentro dos SLAs. Você emite PASS apenas quando TUDO está verde. "
            "Se FAIL, você lista exatamente o que precisa ser corrigido, priorizado por severidade. "
            "Seu lema: 'Dados de teste sem análise são apenas ruído.'"
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
    source_path: str = None,
    acceptance_criteria: str = None,
    mode: str = "full",
):
    """Build a CrewAI crew for software testing."""

    unitario = get_agent("engenheiro-testes-unitarios")
    integracao = get_agent("engenheiro-testes-integracao")
    e2e = get_agent("engenheiro-testes-e2e")
    performance = get_agent("engenheiro-testes-performance")
    analista = get_agent("analista-de-resultados")

    # Build context block
    context_parts = [f"DESCRIÇÃO DO SISTEMA:\n{descricao}"]
    if source_path:
        context_parts.append(f"\nDIRETÓRIO DO CÓDIGO FONTE: {source_path}")
    if acceptance_criteria:
        context_parts.append(f"\nCRITÉRIOS DE ACEITAÇÃO:\n{acceptance_criteria}")
    context = "\n".join(context_parts)

    # --- Task 1: Análise e Planejamento (Analista) ---
    task_analise = Task(
        description=f"""
        {context}

        SEU TRABALHO — ANÁLISE DE CÓDIGO E PLANEJAMENTO DE TESTES:

        Como Analista de Resultados, sua primeira tarefa é ANALISAR o sistema
        descrito e PLANEJAR a estratégia de testes.

        1. Analise a descrição do sistema e identifique:
           - Módulos/componentes principais
           - Fluxos críticos do usuário
           - APIs e endpoints
           - Dependências externas
           - Pontos de risco (autenticação, pagamento, dados sensíveis)

        2. Para cada módulo, determine:
           - Quais funções/métodos precisam de testes unitários
           - Quais integrações precisam de testes de integração
           - Quais fluxos completos precisam de testes E2E
           - Quais endpoints/cenários precisam de testes de performance

        3. Defina a estratégia de cobertura:
           - Meta de cobertura por módulo (mínimo 80%)
           - Prioridade de cada módulo (Crítico/Alto/Médio/Baixo)
           - Técnicas de teste (caixa branca, caixa preta, mutação)

        4. Estime o esforço de cada categoria de teste

        FORMATO DE SAÍDA:
        ## Plano de Testes
        - Módulos identificados: [lista]
        - Fluxos críticos: [lista]
        - Estratégia unitários: [descrição]
        - Estratégia integração: [descrição]
        - Estratégia E2E: [descrição]
        - Estratégia performance: [descrição]
        - Metas de cobertura: [tabela por módulo]
        - Esforço estimado: [por categoria]
        """,
        expected_output=(
            "Plano de testes completo com módulos, estratégias, "
            "metas de cobertura e estimativa de esforço"
        ),
        agent=analista,
    )

    # --- Task 2: Testes Unitários ---
    task_unitarios = Task(
        description=f"""
        {context}

        SEU TRABALHO — CRIAÇÃO DE TESTES UNITÁRIOS:

        Com base no plano de testes, crie testes unitários completos.

        1. Para cada função/método identificado:
           - Crie teste para fluxo feliz (happy path)
           - Crie teste para cada condição de erro
           - Crie teste para edge cases (valores limite, vazios, nulos)
           - Crie teste para exceções

        2. Siga o padrão AAA (Arrange-Act-Assert):
           - Arrange: prepare o cenário (mocks, inputs)
           - Act: execute a função sob teste
           - Assert: verifique o resultado esperado

        3. Use mocks para isolar a unidade:
           - Mock chamadas de banco de dados
           - Mock chamadas de API externas
           - Mock file system e rede

        4. Nomenclatura: test_[funcao]_[cenario]

        5. Para cada teste, documente:
           - O que está sendo testado
           - Pré-condições
           - Resultado esperado

        FORMATO DE SAÍDA:
        ## Testes Unitários
        - Framework: pytest / Jest
        - Total de testes criados: [N]
        - Cobertura estimada: [X]%
        - Lista de testes com descrição e resultado esperado
        - Código dos testes (pelo menos 5 exemplos completos)
        """,
        expected_output=(
            "Suite de testes unitários com cobertura mínima de 80%, "
            "incluindo código de exemplo e documentação"
        ),
        agent=unitario,
    )

    # --- Task 3: Testes de Integração ---
    task_integracao = Task(
        description=f"""
        {context}

        SEU TRABALHO — CRIAÇÃO DE TESTES DE INTEGRAÇÃO:

        Com base no plano de testes, crie testes de integração.

        1. Para cada ponto de integração identificado:
           - Teste de API REST (status codes, headers, body, schemas)
           - Teste de banco de dados (CRUD, transações, concorrência)
           - Teste de filas/mensageria (produzir/consumir, ordem, retry)
           - Teste de serviços externos (mockados ou em container)

        2. Cenários obrigatórios:
           - Integração bem-sucedida (fluxo completo)
           - Timeout e retry
           - Dados inválidos na interface
           - Autenticação/autorização entre serviços
           - Concorrência (requests simultâneos)

        3. Use testcontainers ou fixtures de banco real:
           - Suba banco de teste limpo
           - Popule com dados de seed
           - Execute operações e verifique estado

        4. Para APIs REST, valide:
           - Contrato OpenAPI/Swagger
           - Schemas de request/response
           - Códigos HTTP corretos (200, 201, 400, 401, 404, 500)
           - Headers (CORS, Content-Type, Auth)

        FORMATO DE SAÍDA:
        ## Testes de Integração
        - Pontos de integração testados: [lista]
        - Total de testes: [N]
        - Cobertura de integração: [X]%
        - Código dos testes (pelo menos 3 exemplos completos)
        - Resultados esperados por cenário
        """,
        expected_output=(
            "Suite de testes de integração cobrindo APIs, banco de dados, "
            "e comunicação entre serviços"
        ),
        agent=integracao,
    )

    # --- Task 4: Testes E2E ---
    task_e2e = Task(
        description=f"""
        {context}

        SEU TRABALHO — CRIAÇÃO DE TESTES E2E:

        Com base no plano de testes, crie testes end-to-end.

        1. Para cada fluxo crítico identificado:
           - Fluxo de login/autenticação
           - Fluxo principal do usuário (cadastro, consulta, ação)
           - Fluxo de erro (dados inválidos, 404, servidor off)
           - Fluxo de logout/expiração de sessão

        2. Regras obrigatórias:
           - NUNCA use sleep() ou setTimeout() — use esperas condicionais
           - Use role-based selectors: getByRole, getByLabel, getByText
           - Cada teste deve ser independente (setup/teardown próprio)
           - Testes devem ser determinísticos (rodar Nx e passar Nx)

        3. Estrutura de cada teste:
           - Setup: criar dados necessários (via API, não UI)
           - Navegar: ir para a página sob teste
           - Agir: interagir com a UI (cliques, inputs, submits)
           - Verificar: assertions no estado final da UI
           - Teardown: limpar dados criados

        4. Screenshots em caso de falha para debug

        FORMATO DE SAÍDA:
        ## Testes E2E
        - Fluxos testados: [lista]
        - Total de testes: [N]
        - Framework: Playwright / Cypress
        - Código dos testes (pelo menos 3 fluxos completos)
        - Estratégia de data cleanup
        """,
        expected_output=(
            "Suite de testes E2E determinísticos cobrindo fluxos críticos "
            "do usuário, sem sleeps, com role-based selectors"
        ),
        agent=e2e,
    )

    # --- Task 5: Testes de Performance ---
    task_performance = Task(
        description=f"""
        {context}

        SEU TRABALHO — TESTES DE PERFORMANCE:

        Com base no plano de testes, crie cenários de teste de performance.

        1. Cenários obrigatórios:
           - **Carga normal**: simular 100 usuários simultâneos por 5 minutos
           - **Pico**: simular 1000 usuários simultâneos por 2 minutos
           - **Stress**: aumentar gradualmente até 5000 usuários ou até o sistema quebrar
           - **Soak**: manter 500 usuários por 30 minutos (vazamento de memória)

        2. Métricas a coletar:
           - p50, p95, p99 de latência
           - Throughput (requests/segundo)
           - Taxa de erro (%)
           - CPU e memória do servidor
           - Conexões de banco de dados ativas

        3. SLAs recomendados:
           - p95 < 500ms para APIs REST
           - p95 < 3s para carregamento de páginas
           - Taxa de erro < 1% em carga normal
           - Throughput mínimo: 100 req/s

        4. Para cada endpoint crítico:
           - GET (leitura): cenário de consulta
           - POST (escrita): cenário de criação
           - PUT/PATCH (atualização): cenário de alteração
           - DELETE (remoção): cenário de exclusão

        FORMATO DE SAÍDA:
        ## Testes de Performance
        - Cenários: [carga normal, pico, stress, soak]
        - Endpoints testados: [lista]
        - Métricas esperadas: [tabela p50/p95/p99/throughput/erro]
        - SLAs definidos: [lista]
        - Código dos cenários (k6/Locust) — pelo menos 2 exemplos
        - Thresholds e alertas sugeridos
        """,
        expected_output=(
            "Suite de testes de performance com cenários de carga, pico, "
            "stress e soak, métricas e SLAs definidos"
        ),
        agent=performance,
    )

    # --- Task 6: Compilação e Relatório Final (Analista) ---
    task_relatorio = Task(
        description=f"""
        {context}

        SEU TRABALHO — COMPILAÇÃO E RELATÓRIO FINAL:

        Como Analista de Resultados, compile todos os resultados das fases
        anteriores e produza o relatório final de testes.

        1. Compile os resultados de cada categoria:
           - Testes Unitários: total, cobertura, pass/fail
           - Testes de Integração: total, cobertura, pass/fail
           - Testes E2E: total, fluxos cobertos, pass/fail
           - Testes de Performance: métricas, SLAs, pass/fail

        2. Calcule a cobertura agregada:
           - Cobertura total do sistema
           - Cobertura por módulo
           - Gap de cobertura (o que não foi testado)

        3. Identifique regressões:
           - Compare com execuções anteriores (se disponível)
           - Destaque novos failures
           - Destaque degradação de performance

        4. Quality Gate — emita veredito:
           - **PASS** se:
             - Cobertura >= 80% em todos os módulos
             - Zero falhas críticas
             - Performance dentro dos SLAs (p95 < 500ms API, < 3s página)
           - **FAIL** caso contrário, com lista priorizada do que corrigir

        5. Recomendações:
           - O que melhorar na próxima iteração
           - Riscos residuais
           - Sugestões de automação

        FORMATO DE SAÍDA:
        ## Relatório Final de Testes

        ### Resumo Executivo
        - Veredito: PASS / FAIL
        - Cobertura total: [X]%
        - Testes criados: [N] (unit: N, integração: N, E2E: N, perf: N)
        - Performance: p95 [X]ms / SLA [Y]ms

        ### Detalhamento por Categoria
        [tabela com resultados de cada categoria]

        ### Cobertura por Módulo
        [tabela módulo | cobertura | status]

        ### Regressões Identificadas
        [lista se houver]

        ### Quality Gate
        - Cobertura >= 80%: ✅ / ❌
        - Falhas críticas = 0: ✅ / ❌
        - Performance OK: ✅ / ❌
        - Veredito Final: PASS / FAIL

        ### Recomendações
        [lista priorizada]
        """,
        expected_output=(
            "Relatório final de testes completo com veredito PASS/FAIL, "
            "cobertura agregada, métricas de performance e recomendações"
        ),
        agent=analista,
    )

    # --- Build task list based on mode ---
    all_tasks = [task_analise]

    if mode in ("full", "unit"):
        all_tasks.append(task_unitarios)
    if mode in ("full", "integration"):
        all_tasks.append(task_integracao)
    if mode in ("full", "e2e"):
        all_tasks.append(task_e2e)
    if mode in ("full", "performance"):
        all_tasks.append(task_performance)

    all_tasks.append(task_relatorio)

    # --- Agents used in this run ---
    used_agents = [analista]
    if mode in ("full", "unit"):
        used_agents.append(unitario)
    if mode in ("full", "integration"):
        used_agents.append(integracao)
    if mode in ("full", "e2e"):
        used_agents.append(e2e)
    if mode in ("full", "performance"):
        used_agents.append(performance)

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
        description="cp-testes: Testes de Software Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python run.py \"sistema de agendamento\" --source ./src\n"
            "  python run.py \"API REST\" --source ./src --mode unit\n"
            "  python run.py \"app mobile\" --source ./src --mode full --output relatorio.md\n"
            "  python run.py \"teste\" --dry-run\n"
        ),
    )
    parser.add_argument(
        "descricao",
        nargs="?",
        help="Descrição do sistema a ser testado",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição do sistema (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--source", "-s",
        dest="source_path",
        default=None,
        help="Caminho do diretório do código fonte",
    )
    parser.add_argument(
        "--acceptance", "-a",
        dest="acceptance_file",
        default=None,
        help="Arquivo com critérios de aceitação",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o relatório de testes",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "unit", "integration", "e2e", "performance"],
        default="full",
        help="Modo de teste (default: full — todos os tipos)",
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
        print("\n❌ Erro: forneça a descrição do sistema (argumento ou --input)")
        sys.exit(1)

    # --- Resolve critérios de aceitação ---
    acceptance_criteria = None
    if args.acceptance_file:
        acceptance_criteria = Path(args.acceptance_file).read_text(encoding="utf-8")

    output_path = args.output
    mode = args.mode

    # Mode name mapping
    mode_names = {
        "full": "Completo (unit + integração + E2E + performance)",
        "unit": "Apenas Testes Unitários",
        "integration": "Apenas Testes de Integração",
        "e2e": "Apenas Testes E2E",
        "performance": "Apenas Testes de Performance",
    }

    print(f"\n📋 Sistema: {descricao[:120]}...")
    if args.source_path:
        print(f"📂 Código fonte: {args.source_path}")
    print(f"🔧 Modo: {mode_names.get(mode, mode)}")
    print(f"🤖 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(
        descricao=descricao,
        source_path=args.source_path,
        acceptance_criteria=acceptance_criteria,
        mode=mode,
    )

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            desc_short = task.description[:100].replace("\n", " ").strip()
            print(f"  {i}. {desc_short}...")
        print(f"\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de testes...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Relatório de Testes gerado!\n")
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
        out_file = output_dir / f"relatorio-testes_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()