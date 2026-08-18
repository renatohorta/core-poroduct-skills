#!/usr/bin/env python3
"""
cp-manutencao — Manutenção e Evolução de Software Crew (self-contained)

Cria uma crew CrewAI com 4 agentes especializados para manutenção e evolução
de software: diagnosticar bugs, implementar correções, refatorar código e
avaliar impacto de mudanças.

Uso:
  python run.py "o endpoint /login retorna 500 quando o email tem acento" --mode bug-fix
  python run.py "refatorar módulo de pagamentos" --mode refactor
  python run.py "melhorar performance da query de relatórios" --mode improvement
  python run.py "corrigir bug e refatorar lógica" --mode full
  python run.py --input relatorio_bug.md --mode bug-fix
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
    "analista-de-bugs": {
        "role": "Analista de Bugs",
        "goal": (
            "Realizar triagem, reprodução e diagnóstico completo de bugs, "
            "identificando a causa raiz com precisão cirúrgica"
        ),
        "backstory": (
            "Debugger experiente com mais de 15 anos de experiência "
            "em análise de sistemas complexos. Você é conhecido por encontrar "
            "a causa raiz enquanto outros estão ocupados tratando sintomas. "
            "Sua abordagem é metódica: primeiro reproduz o bug, depois isola "
            "as variáveis envolvidas, então rastreia a cadeia de chamadas até "
            "encontrar a origem exata do problema. "
            "Você analisa logs, stack traces, estados de banco de dados e "
            "fluxos de requisição com olhar clínico. "
            "Seu diagnóstico inclui: o que está quebrado, por que está quebrado, "
            "quando começou a quebrar, e qual o menor caminho para corrigir. "
            "Você documenta cada passo da investigação para que outros possam "
            "entender o raciocínio."
        ),
    },
    "desenvolvedor-de-correcao": {
        "role": "Desenvolvedor de Correção",
        "goal": (
            "Implementar correções mínimas, seguras e bem testadas para bugs "
            "identificados, sem introduzir efeitos colaterais"
        ),
        "backstory": (
            "Desenvolvedor cirúrgico que corrige exatamente o que está quebrado, "
            "nada mais. Você tem disciplina de ferro para não fazer refatorações "
            "ou melhorias no caminho — cada linha alterada tem um propósito claro "
            "e justificável. "
            "Sua filosofia: 'a menor mudança possível que resolve o problema'. "
            "Você sempre considera: esta correção pode quebrar outra coisa? "
            "Ela é consistente com o resto do código? Ela é testável? "
            "Antes de implementar, você entende completamente o diagnóstico "
            "do analista de bugs. Depois de implementar, você verifica se o "
            "bug foi realmente eliminado e se os testes existentes continuam "
            "passando. "
            "Você escreve código defensivo, com validação de bordas e tratamento "
            "de erros adequado, mas sem exageros."
        ),
    },
    "engenheiro-de-refatoracao": {
        "role": "Engenheiro de Refatoração",
        "goal": (
            "Melhorar a qualidade do código existente — legibilidade, "
            "performance, manutenibilidade — sem alterar comportamento externo"
        ),
        "backstory": (
            "Engenheiro de software que deixa o código mais limpo do que "
            "encontrou, sem introduzir bugs. Você é especialista em refatoração "
            "segura: extração de métodos, renomeação, simplificação de condicionais, "
            "substituição de herança por composição, aplicação de padrões de design "
            "quando apropriado. "
            "Você segue o princípio de Martin Fowler: 'refatoração é uma mudança "
            "no código que melhora sua estrutura sem alterar seu comportamento'. "
            "Cada refatoração que você faz é pequena, atômica e reversível. "
            "Você nunca refatora e adiciona funcionalidade no mesmo commit. "
            "Sua prioridade é: (1) não quebrar nada, (2) melhorar legibilidade, "
            "(3) reduzir complexidade, (4) melhorar performance. "
            "Você sempre valida que os testes existentes continuam passando "
            "após cada refatoração."
        ),
    },
    "analista-de-impacto": {
        "role": "Analista de Impacto",
        "goal": (
            "Avaliar o impacto de mudanças propostas no sistema, identificar "
            "regressões potenciais e garantir a qualidade da entrega final"
        ),
        "backstory": (
            "Analista que pensa em todas as consequências antes de uma mudança "
            "ser feita. Você tem uma mente sistêmica que enxerga o software como "
            "um ecossistema interconectado — mudar uma peça afeta muitas outras. "
            "Sua especialidade é mapear dependências, identificar acoplamentos "
            "ocultos e prever regressões antes que elas aconteçam. "
            "Você analisa: quais módulos são afetados? Quais fluxos de usuário "
            "podem quebrar? Quais testes de regressão precisam ser executados? "
            "Há riscos de segurança ou performance? A mudança é consistente com "
            "a arquitetura existente? "
            "Você é o quality gate final — cético por natureza, exigente por "
            "princípio. Seu veredito PASS ou FAIL é baseado em evidências "
            "concretas, não em suposições. "
            "Você documenta riscos, cenários de teste e recomendações para "
            "mitigação."
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
    output_dir: str = None,
):
    """
    Build a CrewAI crew for software maintenance.

    Args:
        descricao: Bug report / improvement request description
        mode: 'bug-fix', 'refactor', 'improvement', or 'full'
        output_dir: Directory to save output files
    """
    agents = {}
    tasks = []

    # --- Agent: Analista de Bugs ---
    agents["analista"] = get_agent("analista-de-bugs")

    # --- Agent: Desenvolvedor de Correção ---
    agents["corretor"] = get_agent("desenvolvedor-de-correcao")

    # --- Agent: Engenheiro de Refatoração ---
    agents["refatorador"] = get_agent("engenheiro-de-refatoracao")

    # --- Agent: Analista de Impacto ---
    agents["impacto"] = get_agent("analista-de-impacto")

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Análise e Diagnóstico (Analista de Bugs)
    # Executada em todos os modos exceto 'refactor' e 'improvement'
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("bug-fix", "full"):
        task_diagnostico = Task(
            description=f"""
            DESCRIÇÃO DO PROBLEMA:
            {descricao}

            SEU TRABALHO — ANÁLISE E DIAGNÓSTICO:

            Você é o Analista de Bugs. Investigue este problema a fundo:

            1. **Reproduza o bug mentalmente**: Qual o cenário exato que dispara o erro?
            2. **Analise a causa raiz**: Não pare no sintoma — encontre a origem.
            3. **Documente o diagnóstico**:
               - Comportamento esperado vs. comportamento atual
               - Condições para reproduzir o bug
               - Causa raiz identificada (arquivo, função, linha)
               - Cadeia de chamadas que leva ao erro
               - Impacto estimado (quantos usuários afetados, severidade)
            4. **Sugira abordagens de correção**: Liste 1-3 possíveis correções
               com prós e contras de cada uma

            Formato do relatório:
            ```
            ## Diagnóstico de Bug

            ### Comportamento Esperado
            ...

            ### Comportamento Atual
            ...

            ### Passos para Reproduzir
            1. ...
            2. ...

            ### Causa Raiz
            - Arquivo: ...
            - Função: ...
            - Explicação: ...

            ### Impacto
            - Severidade: 🔴 Crítica / 🟠 Alta / 🟡 Média / 🔵 Baixa
            - Usuários afetados: ...
            - ...

            ### Abordagens de Correção Sugeridas
            1. ... (recomendada)
            2. ...
            ```
            """,
            expected_output=(
                "Relatório de diagnóstico completo com causa raiz identificada, "
                "passos para reproduzir, impacto estimado e sugestões de correção."
            ),
            agent=agents["analista"],
        )
        tasks.append(task_diagnostico)

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Análise de Impacto (Analista de Impacto)
    # Executada em todos os modos
    # ─────────────────────────────────────────────────────────────────────
    task_impacto = Task(
        description=f"""
        DESCRIÇÃO DO PROBLEMA:
        {descricao}

        SEU TRABALHO — ANÁLISE DE IMPACTO:

        Você é o Analista de Impacto. Avalie as consequências das mudanças
        propostas antes que elas sejam implementadas:

        1. **Mapeie dependências**: Quais módulos, serviços e funcionalidades
           estão conectados à área que será modificada?

        2. **Identifique riscos**:
           - Regressões potenciais (o que pode quebrar?)
           - Riscos de segurança (a mudança expõe vulnerabilidades?)
           - Riscos de performance (a mudança degrada performance?)
           - Riscos de consistência (a mudança é coerente com o resto do sistema?)

        3. **Liste cenários de teste de regressão**:
           - Testes existentes que devem continuar passando
           - Novos cenários que precisam ser testados
           - Edge cases que merecem atenção especial

        4. **Recomendações**:
           - A mudança deve ser feita? Por quê?
           - Precauções a serem tomadas durante a implementação
           - Ordem sugerida de implementação (se houver múltiplas mudanças)

        Formato do relatório:
        ```
        ## Análise de Impacto

        ### Dependências Identificadas
        - Módulo X → depende de Y → afeta Z
        ...

        ### Riscos Identificados
        - 🔴 Crítico: ...
        - 🟠 Alto: ...
        - 🟡 Médio: ...
        - 🔵 Baixo: ...

        ### Cenários de Teste de Regressão
        1. ...
        2. ...

        ### Recomendações
        - Ação recomendada: ...
        - Precauções: ...
        ```
        """,
        expected_output=(
            "Relatório de análise de impacto com dependências mapeadas, "
            "riscos identificados, cenários de teste de regressão e recomendações."
        ),
        agent=agents["impacto"],
    )
    tasks.append(task_impacto)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3a: Correção (Dev Correção) — modo bug-fix ou full
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("bug-fix", "full"):
        task_correcao = Task(
            description=f"""
            DESCRIÇÃO DO PROBLEMA:
            {descricao}

            SEU TRABALHO — IMPLEMENTAR CORREÇÃO:

            Você é o Desenvolvedor de Correção. Com base no diagnóstico do
            Analista de Bugs e na análise de impacto, implemente a correção:

            1. **Implemente a correção mínima**: Apenas o necessário para
               eliminar o bug. Nada de refatorações, melhorias ou mudanças
               não relacionadas.

            2. **Siga as boas práticas**:
               - Código defensivo: valide entradas, trate bordas
               - Tratamento de erros consistente com o resto do código
               - Nomes descritivos e código legível
               - Comentários apenas onde a lógica não é óbvia

            3. **Documente as alterações**:
               - Arquivos modificados com paths exatos
               - Linhas alteradas (de/para)
               - Justificativa de cada mudança
               - Por que esta abordagem foi escolhida

            4. **Verifique**:
               - O bug foi realmente eliminado?
               - Os testes existentes continuam passando?
               - Não há efeitos colaterais visíveis?

            IMPORTANTE:
            - Corrija exatamente o que está quebrado, nada mais
            - Não introduza novas funcionalidades
            - Não refatore código não relacionado
            - Se a correção for complexa, explique o raciocínio

            Formato do relatório:
            ```
            ## Correção Implementada

            ### Arquivos Modificados
            - `caminho/arquivo.py`: [descrição da mudança]
              - Linha X: `código antigo` → `código novo`
              - Motivo: ...

            ### Justificativa
            ...

            ### Verificação
            - Bug eliminado: ✅ / ❌
            - Testes existentes passam: ✅ / ❌
            - Efeitos colaterais: Nenhum / [descrever]
            ```
            """,
            expected_output=(
                "Código corrigido com documentação das alterações: arquivos "
                "modificados, linhas alteradas, justificativa e verificação."
            ),
            agent=agents["corretor"],
        )
        tasks.append(task_correcao)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3b: Refatoração (Eng. Refatoração) — modo refactor, improvement ou full
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("refactor", "improvement", "full"):
        task_refatoracao = Task(
            description=f"""
            DESCRIÇÃO DO PROBLEMA:
            {descricao}

            SEU TRABALHO — REFATORAÇÃO / MELHORIA:

            Você é o Engenheiro de Refatoração. Com base na análise de impacto,
            melhore o código existente sem alterar seu comportamento externo:

            1. **Identifique pontos de melhoria**:
               - Código duplicado → extraia para função/método
               - Complexidade alta → simplifique condicionais
               - Nomes ruins → renomeie para ser descritivo
               - Funções longas → extraia métodos
               - Acoplamento forte → aplique padrões de design
               - Performance ruim → otimize sem mudar API

            2. **Implemente as refatorações**:
               - Uma mudança de cada vez (passos atômicos)
               - Cada passo preserva o comportamento
               - Testes existentes devem passar após cada passo

            3. **Documente as alterações**:
               - O que mudou e por quê
               - Padrão de design aplicado (se aplicável)
               - Benefício esperado (legibilidade, performance, manutenibilidade)
               - Riscos mitigados

            IMPORTANTE:
            - NÃO altere comportamento externo (API, contratos, output)
            - NÃO adicione novas funcionalidades
            - NÃO remova funcionalidades existentes
            - Cada refatoração deve ser pequena e verificável
            - Se a mudança for arriscada, destaque o risco

            Formato do relatório:
            ```
            ## Refatoração / Melhoria

            ### Mudanças Realizadas
            1. **Extração de método** em `arquivo.py`:
               - O que: extraído validação de email para método separado
               - Por que: estava duplicado em 3 lugares
               - Benefício: redução de duplicação, testabilidade

            2. **Renomeação** em `arquivo.py`:
               - `calcular()` → `calcular_frete_com_desconto()`
               - Por que: nome original era genérico demais
               - Benefício: legibilidade

            ### Benefícios
            - Legibilidade: ...
            - Manutenibilidade: ...
            - Performance: ...

            ### Verificação
            - Comportamento preservado: ✅
            - Testes existentes passam: ✅
            ```
            """,
            expected_output=(
                "Código refatorado com documentação das mudanças: o que mudou, "
                "por que mudou, benefícios e verificação de comportamento preservado."
            ),
            agent=agents["refatorador"],
        )
        tasks.append(task_refatoracao)

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Testes de Regressão + Quality Gate (Analista de Bugs + Analista de Impacto)
    # ─────────────────────────────────────────────────────────────────────
    task_regressao = Task(
        description=f"""
        DESCRIÇÃO DO PROBLEMA:
        {descricao}

        SEU TRABALHO — TESTES DE REGRESSÃO E QUALITY GATE:

        Você é o Analista de Impacto (quality gate final). Valide se a
        correção/refatoração foi bem-sucedida e se não há regressões:

        1. **Valide a correção/refatoração**:
           - O bug foi realmente corrigido? (se aplicável)
           - O comportamento foi preservado? (se refatoração)
           - A mudança é consistente com a arquitetura do sistema?

        2. **Execute testes de regressão mentalmente**:
           - Testes existentes: todos devem passar
           - Cenários de borda: o que acontece com entradas inesperadas?
           - Cenários de concorrência: a mudança é thread-safe?
           - Cenários de falha: o que acontece se um serviço externo falhar?

        3. **Verifique a qualidade do código**:
           - A correção é mínima? (sem mudanças não relacionadas)
           - A refatoração preservou comportamento? (se aplicável)
           - Há testes para o cenário corrigido?
           - O código está limpo e legível?

        4. **Emita o veredito final**:

        ```
        ## Quality Gate — Veredito Final

        ### ✅ Itens Verificados
        - Diagnóstico completo: [OK/ISSUES]
        - Análise de impacto realizada: [OK/ISSUES]
        - Correção implementada: [OK/ISSUES/NA]
        - Refatoração realizada: [OK/ISSUES/NA]
        - Comportamento preservado: [OK/ISSUES/NA]
        - Testes de regressão: [OK/ISSUES]

        ### 🔴 Problemas Encontrados
        ...

        ### 📋 Veredito Final
        ## ✅ PASS / ❌ FAIL

        ### Recomendações
        ...
        ```
        """,
        expected_output=(
            "Relatório de testes de regressão com verificação completa e "
            "veredito final PASS/FAIL com evidências."
        ),
        agent=agents["impacto"],
    )
    tasks.append(task_regressao)

    # --- Monta lista de agentes (apenas os usados) ---
    agent_list = []
    if mode in ("bug-fix", "full"):
        agent_list.append(agents["analista"])
    agent_list.append(agents["impacto"])
    if mode in ("bug-fix", "full"):
        agent_list.append(agents["corretor"])
    if mode in ("refactor", "improvement", "full"):
        agent_list.append(agents["refatorador"])

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
        description="cp-manutencao: Manutenção e Evolução de Software Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run.py "o endpoint /login retorna 500 quando o email tem acento" --mode bug-fix
  python run.py "refatorar módulo de pagamentos para usar Strategy Pattern" --mode refactor
  python run.py "melhorar performance da query de relatórios" --mode improvement
  python run.py "corrigir bug no cálculo de frete e refatorar lógica de descontos" --mode full
  python run.py --input relatorio_bug.md --mode bug-fix --output ./correcoes
  python run.py "teste" --dry-run
        """,
    )
    parser.add_argument(
        "descricao",
        nargs="?",
        help="Descrição do bug / solicitação de melhoria / refatoração",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição do problema (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["bug-fix", "refactor", "improvement", "full"],
        default="full",
        help="Modo de operação (default: full = pipeline completo)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Diretório de saída para salvar relatórios",
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
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ Arquivo não encontrado: {args.input_file}")
            sys.exit(1)
        descricao = input_path.read_text(encoding="utf-8")
    elif args.descricao:
        descricao = args.descricao
    else:
        parser.print_help()
        print("\n❌ Erro: forneça a descrição do problema (argumento ou --input)")
        sys.exit(1)

    output_dir = args.output

    # --- Mapa de modos ---
    mode_label = {
        "bug-fix": "Correção de Bug",
        "refactor": "Refatoração",
        "improvement": "Melhoria",
        "full": "Pipeline Completo (Diagnóstico → Impacto → Correção/Refatoração → Testes)",
    }

    print(f"\n📋 Descrição: {descricao[:120]}...")
    print(f"🔧 Modo: {mode_label.get(args.mode, args.mode)}")
    print(f"📂 Agentes: embutidos (self-contained)")
    print()

    crew = build_crew(descricao, args.mode, output_dir)

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

    print("🚀 Executando crew de manutenção...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Manutenção concluída!\n")
    print(result_str)

    # --- Save output ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        report_file = out_path / "relatorio_manutencao.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {report_file.resolve()}")
    else:
        # Save to default location
        output_path = Path(__file__).resolve().parent.parent / "outputs"
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"manutencao_{timestamp}.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Relatório salvo em: {report_file.resolve()}")


if __name__ == "__main__":
    main()