#!/usr/bin/env python3
"""
cp-implementacao — Implementação de Software Crew (self-contained)

Cria uma crew CrewAI com 5 agentes especializados para implementar,
revisar e integrar código de software.

Uso:
  python run.py "implementar CRUD de usuários com autenticação JWT"
  python run.py "criar endpoint de relatórios" --type backend
  python run.py "tela de login com validação" --type frontend
  python run.py "sistema de agendamento" --type full
  python run.py --input especificacao.md --output ./implementacao
  python run.py "teste" --dry-run
"""

import argparse
import sys
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
    "desenvolvedor-backend": {
        "role": "Desenvolvedor Backend",
        "goal": (
            "Implementar APIs REST/GraphQL, lógica de negócio, modelos de dados, "
            "migrações de banco, autenticação, autorização e endpoints performáticos"
        ),
        "backstory": (
            "Engenheiro de backend sênior com mais de 12 anos de experiência "
            "em sistemas distribuídos, APIs RESTful, GraphQL, bancos relacionais "
            "e NoSQL. Você é obcecado por código limpo, testável e performático. "
            "Sempre pensa em edge cases, validação de entrada, tratamento de erros "
            "e segurança antes de escrever uma linha de código. "
            "Você segue princípios SOLID, DRY e KISS. "
            "Suas APIs são documentadas, versionadas e seguem padrões RESTful. "
            "Você não entrega código sem testes unitários."
        ),
    },
    "desenvolvedor-frontend": {
        "role": "Desenvolvedor Frontend",
        "goal": (
            "Implementar interfaces de usuário responsivas, acessíveis e performáticas "
            "com integração completa à API"
        ),
        "backstory": (
            "Engenheiro frontend especializado em React, TypeScript, Tailwind CSS "
            "e frameworks modernos. Você cria componentes reutilizáveis, gerencia "
            "estado com eficiência (React Query, Zustand, Redux), e implementa "
            "animações suaves e transições naturais. "
            "Você é obcecado por acessibilidade (WCAG 2.1 AA/AAA), performance "
            "Core Web Vitals, e experiência do usuário. "
            "Cada componente que você cria tem estados de loading, empty, error "
            "e edge case cobertos. Você integra frontend com API usando contratos "
            "tipados e trata erros de rede graciosamente."
        ),
    },
    "desenvolvedor-mobile": {
        "role": "Desenvolvedor Mobile",
        "goal": (
            "Implementar aplicativos mobile nativos/cross-platform com React Native "
            "ou Flutter, com performance, navegação fluida e integração com API"
        ),
        "backstory": (
            "Engenheiro mobile sênior especializado em React Native e Flutter. "
            "Você constrói apps que parecem nativos, com animações a 60fps, "
            "navegação intuitiva e gerenciamento de estado eficiente. "
            "Você pensa em: consumo de bateria, uso de dados, telas pequenas, "
            "toque versus clique, gestos nativos, e offline-first. "
            "Cada tela que você cria considera loading states, pull-to-refresh, "
            "tratamento de erro amigável e empty states. "
            "Você integra com APIs REST usando contratos tipados e gerencia "
            "cache local para experiência offline."
        ),
    },
    "revisor-de-codigo": {
        "role": "Revisor de Código",
        "goal": (
            "Revisar todo o código implementado: verificar padrões, boas práticas, "
            "segurança, performance, legibilidade e coesão arquitetural"
        ),
        "backstory": (
            "Engenheiro de software sênior que já revisou milhares de pull requests "
            "em dezenas de projetos. Você tem um olhar clínico para: "
            "código morto, complexidade ciclomática alta, vazamento de abstração, "
            "acoplamento excessivo, falta de coesão, e más práticas de segurança. "
            "Você não aprova código que: não tem testes, tem magic numbers, "
            "tratamento genérico de exceções, ou lógica duplicada. "
            "Seu feedback é construtivo, específico e acionável — você sempre "
            "sugere COMO melhorar, não apenas aponta o problema. "
            "Você emite um relatório detalhado com: problemas encontrados, "
            "severidade (baixa/média/alta/crítica), e sugestões de correção."
        ),
    },
    "integrador": {
        "role": "Integrador",
        "goal": (
            "Garantir que backend, frontend e mobile funcionam juntos: validar "
            "contratos de API, fluxos de ponta a ponta e consistência dos dados"
        ),
        "backstory": (
            "Engenheiro de integração experiente que garante que todas as peças "
            "do sistema se encaixam perfeitamente. Você verifica: "
            "se os contratos de API são respeitados (status codes, formatos de "
            "resposta, headers), se o frontend consome os dados corretamente, "
            "se o mobile trata os mesmos cenários, e se não há quebras entre "
            "as camadas. "
            "Você executa testes de integração mentalmente, validando fluxos "
            "completos: do clique do usuário até o banco de dados e volta. "
            "Seu lema: 'Se não funciona integrado, não funciona.' "
            "Você emite veredito PASS ou FAIL com evidências específicas."
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
    especificacao: str,
    tipo: str = "full",
    output_dir: str = None,
):
    """
    Build a CrewAI crew for software implementation.

    Args:
        especificacao: Technical specification / feature description
        tipo: 'backend', 'frontend', 'mobile', or 'full'
        output_dir: Directory to save output files
    """
    agents = {}
    tasks = []

    # --- Agent: Desenvolvedor Backend ---
    agents["backend"] = get_agent("desenvolvedor-backend")

    # --- Agent: Desenvolvedor Frontend ---
    agents["frontend"] = get_agent("desenvolvedor-frontend")

    # --- Agent: Desenvolvedor Mobile (opcional) ---
    agents["mobile"] = get_agent("desenvolvedor-mobile")

    # --- Agent: Revisor de Código ---
    agents["revisor"] = get_agent("revisor-de-codigo")

    # --- Agent: Integrador ---
    agents["integrador"] = get_agent("integrador")

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Implementação Backend
    # ─────────────────────────────────────────────────────────────────────
    if tipo in ("backend", "full"):
        task_backend = Task(
            description=f"""
            ESPECIFICAÇÃO TÉCNICA:
            {especificacao}

            SEU TRABALHO — IMPLEMENTAÇÃO BACKEND:

            1. Analise a especificação e identifique os endpoints, modelos e regras de negócio
            2. Implemente:
               - Modelos de dados e migrações
               - Endpoints REST/GraphQL com validação de entrada
               - Lógica de negócio com tratamento de erros
               - Autenticação/autorização quando aplicável
               - Testes unitários para a lógica implementada
            3. Documente os contratos de API (método, path, request/response)
            4. Siga boas práticas: SOLID, DRY, KISS, tratamento de erros consistente

            IMPORTANTE:
            - Código limpo e bem estruturado
            - Validação de entrada em todos os endpoints
            - Tratamento de erros com status codes apropriados
            - Logs para debug em produção
            - Testes unitários obrigatórios
            """,
            expected_output=(
                "Código backend implementado: modelos, endpoints, lógica de negócio, "
                "testes unitários. Contratos de API documentados."
            ),
            agent=agents["backend"],
        )
        tasks.append(task_backend)

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Implementação Frontend
    # ─────────────────────────────────────────────────────────────────────
    if tipo in ("frontend", "full"):
        task_frontend = Task(
            description=f"""
            ESPECIFICAÇÃO TÉCNICA:
            {especificacao}

            SEU TRABALHO — IMPLEMENTAÇÃO FRONTEND:

            1. Analise a especificação e os contratos de API
            2. Implemente:
               - Componentes React/Vue/Angular com TypeScript
               - Estados: loading, empty, error, sucesso
               - Integração com API (React Query, SWR, ou fetch)
               - Navegação entre telas
               - Formulários com validação
               - Design responsivo e acessível (WCAG)
            3. Trate todos os estados de UI:
               - Loading: skeleton/spinner
               - Empty: mensagem amigável + call to action
               - Error: mensagem + botão de retry
               - Sucesso: feedback visual

            IMPORTANTE:
            - Acessibilidade (aria-labels, roles, focus management)
            - Performance (code splitting, lazy loading)
            - Tratamento de erros de rede
            - Feedback visual para todas as ações do usuário
            """,
            expected_output=(
                "Código frontend implementado: componentes, telas, integração com API, "
                "estados de UI, acessibilidade."
            ),
            agent=agents["frontend"],
        )
        tasks.append(task_frontend)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3: Implementação Mobile (opcional)
    # ─────────────────────────────────────────────────────────────────────
    if tipo in ("mobile", "full"):
        task_mobile = Task(
            description=f"""
            ESPECIFICAÇÃO TÉCNICA:
            {especificacao}

            SEU TRABALHO — IMPLEMENTAÇÃO MOBILE:

            1. Analise a especificação e os contratos de API
            2. Implemente (React Native ou Flutter):
               - Telas com navegação fluida
               - Componentes nativos otimizados
               - Integração com API REST
               - Estados: loading, empty, error, sucesso
               - Gestos e animações nativas
               - Cache offline-first quando aplicável
            3. Considere:
               - Performance em dispositivos de baixo custo
               - Consumo de bateria e dados
               - Telas de diferentes tamanhos
               - Modo offline

            IMPORTANTE:
            - Navegação intuitiva (stack, tab, drawer)
            - Pull-to-refresh em listas
            - Tratamento de erro amigável
            - Empty states com ilustrações
            """,
            expected_output=(
                "Código mobile implementado: telas, navegação, integração com API, "
                "estados de UI, cache offline."
            ),
            agent=agents["mobile"],
        )
        tasks.append(task_mobile)

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Code Review
    # ─────────────────────────────────────────────────────────────────────
    task_review = Task(
        description=f"""
        ESPECIFICAÇÃO TÉCNICA:
        {especificacao}

        SEU TRABALHO — CODE REVIEW:

        Revise TODO o código implementado (backend, frontend e/ou mobile) e avalie:

        1. **Padrões e boas práticas**: O código segue convenções do framework/linguagem?
        2. **Segurança**: Há vulnerabilidades? (SQL injection, XSS, CSRF, dados sensíveis expostos)
        3. **Performance**: Há gargalos? (N+1 queries, renderizações desnecessárias, bundle grande)
        4. **Legibilidade**: O código é claro? Nomes de variáveis/funções são descritivos?
        5. **Manutenibilidade**: Há código duplicado? Complexidade desnecessária?
        6. **Testes**: Os testes cobrem os cenários importantes?
        7. **Tratamento de erros**: Todos os erros são tratados adequadamente?

        Para cada problema encontrado, informe:
        - Localização (arquivo, linha aproximada)
        - Severidade: 🔴 Crítica / 🟠 Alta / 🟡 Média / 🔵 Baixa
        - Descrição do problema
        - Sugestão de correção

        Formato do relatório:
        ```
        ## Relatório de Code Review

        ### 🔴 Problemas Críticos
        ...

        ### 🟠 Problemas Altos
        ...

        ### 🟡 Problemas Médios
        ...

        ### 🔵 Problemas Baixos
        ...

        ### ✅ Pontos Positivos
        ...

        ### 📊 Resumo
        - Total de problemas: N
        - Críticos: N | Altos: N | Médios: N | Baixos: N
        - Veredito: APROVADO / REPROVADO
        ```
        """,
        expected_output=(
            "Relatório de code review completo com problemas categorizados por severidade, "
            "sugestões de correção e veredito final."
        ),
        agent=agents["revisor"],
    )
    tasks.append(task_review)

    # ─────────────────────────────────────────────────────────────────────
    # Task 5: Integração e Validação
    # ─────────────────────────────────────────────────────────────────────
    task_integracao = Task(
        description=f"""
        ESPECIFICAÇÃO TÉCNICA:
        {especificacao}

        SEU TRABALHO — INTEGRAÇÃO E VALIDAÇÃO:

        Você é o último quality gate. Verifique se tudo funciona junto:

        1. **Contratos de API**: Backend expõe o que o frontend/mobile espera?
           - Status codes corretos (200, 201, 400, 401, 404, 500)?
           - Formato de resposta consistente?
           - Headers de autenticação compatíveis?

        2. **Fluxos de ponta a ponta**:
           - Usuário faz ação no frontend → chamada à API → resposta → UI atualizada
           - Erros da API são tratados na UI?
           - Loading states aparecem enquanto a requisição ocorre?

        3. **Consistência**:
           - Nomes de campos são consistentes entre backend e frontend?
           - Tipos de dados são compatíveis?
           - Paginação, filtros e ordenação funcionam igual em todas as camadas?

        4. **Validação duplicada**:
           - Validação no frontend E no backend?
           - Mensagens de erro são consistentes?

        Emita o veredito final:

        ```
        ## Relatório de Integração

        ### ✅ Itens Verificados
        - Contratos de API: [OK/ISSUES]
        - Fluxos E2E: [OK/ISSUES]
        - Consistência: [OK/ISSUES]
        - Validação: [OK/ISSUES]

        ### 🔴 Problemas de Integração
        ...

        ### 📋 Veredito Final
        ## PASS ✅ / FAIL ❌

        ### Recomendações
        ...
        ```
        """,
        expected_output=(
            "Relatório de integração completo com verificação de contratos, fluxos E2E, "
            "consistência e veredito final PASS/FAIL."
        ),
        agent=agents["integrador"],
    )
    tasks.append(task_integracao)

    # --- Monta lista de agentes (apenas os usados) ---
    agent_list = []
    if tipo in ("backend", "full"):
        agent_list.append(agents["backend"])
    if tipo in ("frontend", "full"):
        agent_list.append(agents["frontend"])
    if tipo in ("mobile", "full"):
        agent_list.append(agents["mobile"])
    agent_list.append(agents["revisor"])
    agent_list.append(agents["integrador"])

    # --- Crew ---
    crew = Crew(
        agents=agent_list,
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
        description="cp-implementacao: Implementação de Software Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run.py "implementar CRUD de usuários com autenticação JWT"
  python run.py "criar endpoint de relatórios" --type backend
  python run.py "tela de login com validação" --type frontend
  python run.py "app mobile de catálogo" --type mobile
  python run.py "sistema de agendamento" --type full
  python run.py --input especificacao.md --output ./implementacao
  python run.py "teste" --dry-run
        """,
    )
    parser.add_argument(
        "especificacao",
        nargs="?",
        help="Especificação técnica do que implementar",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a especificação técnica (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["backend", "frontend", "mobile", "full"],
        default="full",
        help="Tipo de implementação (default: full = backend + frontend + mobile)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Diretório de saída para salvar o código e relatórios",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas monta a crew e mostra os agentes, sem executar",
    )
    args = parser.parse_args()

    # --- Resolve especificação ---
    especificacao = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ Arquivo não encontrado: {args.input_file}")
            sys.exit(1)
        especificacao = input_path.read_text(encoding="utf-8")
    elif args.especificacao:
        especificacao = args.especificacao
    else:
        parser.print_help()
        print("\n❌ Erro: forneça a especificação técnica (argumento ou --input)")
        sys.exit(1)

    output_dir = args.output

    # --- Mapa de tipos ---
    tipo_label = {
        "backend": "Backend",
        "frontend": "Frontend",
        "mobile": "Mobile",
        "full": "Full Stack (Backend + Frontend + Mobile)",
    }

    print(f"\n📋 Especificação: {especificacao[:120]}...")
    print(f"🔧 Tipo: {tipo_label.get(args.type, args.type)}")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(especificacao, args.type, output_dir)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            agent_name = task.agent.role if hasattr(task, 'agent') and task.agent else "?"
            print(f"  {i}. {task.description[:80]}... → {agent_name}")
        print("\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de implementação...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Implementação concluída!\n")
    print(result_str)

    # --- Save output ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        report_file = out_path / "relatorio_implementacao.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {report_file.resolve()}")
    else:
        # Save to default location
        output_path = Path(__file__).resolve().parent.parent / "outputs"
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"implementacao_{timestamp}.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {report_file.resolve()}")


if __name__ == "__main__":
    main()