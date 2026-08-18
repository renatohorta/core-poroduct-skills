#!/usr/bin/env python3
"""
cp-seguranca — Segurança de Software Crew (self-contained)

Cria uma crew CrewAI com agentes especializados para analisar vulnerabilidades,
testar invasões, verificar compliance e corrigir falhas de segurança.

Uso:
  python run.py "sistema de login com JWT"
  python run.py --mode pentest "API REST com upload de arquivos"
  python run.py --input src/app.py --output relatorio.md
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
    "analista-de-seguranca": {
        "role": "Analista de Segurança",
        "goal": "Revisar código e arquitetura contra OWASP Top 10 e identificar vulnerabilidades críticas",
        "backstory": (
            "Engenheiro de segurança sênior com mais de 15 anos de experiência em segurança de software. "
            "Você é especialista em OWASP Top 10, análise estática de código, modelagem de ameaças "
            "e revisão de arquitetura de segurança. Você encontra vulnerabilidades onde ninguém mais "
            "olha — em validação de entrada, controle de acesso, criptografia, configuração insegura, "
            "e muito mais. Seu olhar clínico para falhas de segurança já preveniu centenas de breaches. "
            "Você não apenas aponta problemas, mas explica o impacto real de cada vulnerabilidade "
            "e sugere correções específicas. Seu lema: 'Segurança não é um recurso, é uma propriedade do sistema.'"
        ),
    },
    "penetration-tester": {
        "role": "Penetration Tester",
        "goal": "Executar testes de invasão automatizados para identificar vetores de ataque exploráveis",
        "backstory": (
            "Pentester ético certificado (OSCP, CEH) que pensa como atacante para proteger o sistema. "
            "Você tem experiência em testes de invasão em aplicações web, APIs, infraestrutura em nuvem "
            "e redes. Você conhece as táticas, técnicas e procedimentos (TTPs) dos atacantes reais. "
            "Você testa: injeção SQL, XSS, CSRF, SSRF, IDOR, LFI/RFI, desserialização insegura, "
            "broken authentication, path traversal, e muito mais. Você documenta cada ataque com "
            "passos reproduzíveis, prova de conceito (PoC) e classificação de severidade. "
            "Seu objetivo: quebrar o sistema antes dos criminosos o fazerem."
        ),
    },
    "especialista-em-compliance": {
        "role": "Especialista em Compliance",
        "goal": "Verificar conformidade com LGPD, GDPR, SOC2, ISO 27001 e regulamentações aplicáveis",
        "backstory": (
            "Compliance officer experiente que conhece todas as regulamentações de proteção de dados "
            "e segurança da informação. Você é especialista em LGPD (Lei Geral de Proteção de Dados "
            "do Brasil), GDPR (General Data Protection Regulation da União Europeia), SOC2 (Service "
            "Organization Control), ISO 27001 (Sistema de Gestão de Segurança da Informação) e "
            "PCI-DSS (Padrão de Segurança para Dados de Cartão de Crédito). Você verifica se o "
            "sistema está em conformidade com cada regulamentação aplicável, identifica gaps "
            "e recomenda ações corretivas. Você conhece os artigos, seções e controles específicos "
            "de cada norma. Seu lema: 'Conformidade não é opcional — é lei.'"
        ),
    },
    "engenheiro-de-correcao": {
        "role": "Engenheiro de Correção",
        "goal": "Implementar correções de vulnerabilidades encontradas sem introduzir novas falhas",
        "backstory": (
            "Desenvolvedor security-focused com vasta experiência em correção de vulnerabilidades. "
            "Você é especialista em implementar correções seguras sem introduzir novas falhas ou "
            "quebrar funcionalidades existentes. Você conhece as práticas de codificação segura: "
            "prepared statements, output encoding, CSP, validação de entrada no backend, "
            "autenticação segura, gerenciamento de sessão, criptografia adequada, e muito mais. "
            "Para cada vulnerabilidade encontrada, você implementa a correção mais adequada "
            "considerando o contexto do sistema, performance e manutenibilidade. "
            "Você documenta cada correção explicando o que mudou e por que a abordagem é segura. "
            "Seu lema: 'Corrigir uma vulnerabilidade sem criar duas novas.'"
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
    """Build a CrewAI crew for security analysis based on mode."""

    analista = get_agent("analista-de-seguranca")
    pentester = get_agent("penetration-tester")
    compliance = get_agent("especialista-em-compliance")
    engenheiro = get_agent("engenheiro-de-correcao")

    tasks = []

    # ── Task 1: Análise de Segurança (sempre presente) ──
    task_analise = Task(
        description=f"""\
DESCRIÇÃO DO SISTEMA:
{descricao}

SEU TRABALHO — ANÁLISE DE SEGURANÇA DE CÓDIGO E ARQUITETURA:

Analise o sistema descrito contra as seguintes categorias do OWASP Top 10:

1. **A01: Broken Access Control** — Controles de acesso ausentes ou falhos
2. **A02: Cryptographic Failures** — Falhas criptográficas (dados sensíveis expostos)
3. **A03: Injection** — SQL, NoSQL, OS Command, LDAP injection
4. **A04: Insecure Design** — Falhas de design que levam a vulnerabilidades
5. **A05: Security Misconfiguration** — Configurações inseguras
6. **A06: Vulnerable and Outdated Components** — Componentes com vulnerabilidades conhecidas
7. **A07: Identification and Authentication Failures** — Falhas de autenticação
8. **A08: Software and Data Integrity Failures** — Falhas de integridade
9. **A09: Security Logging and Monitoring Failures** — Falhas de logging e monitoramento
10. **A10: Server-Side Request Forgery (SSRF)** — SSRF

Para cada vulnerabilidade identificada, documente:
- **Categoria OWASP**: qual das 10 categorias
- **Localização**: onde no sistema a vulnerabilidade se manifesta
- **Descrição**: explique a vulnerabilidade em detalhes
- **Impacto**: qual o dano potencial (crítico, alto, médio, baixo)
- **Probabilidade**: qual a chance de exploração (alta, média, baixa)
- **CVE relacionado**: se aplicável, mencione CVEs conhecidos
- **Recomendação**: como corrigir a vulnerabilidade

FORMATO DE SAÍDA:
## Relatório de Análise de Segurança
### Resumo Executivo
- Total de vulnerabilidades encontradas: [N]
- Críticas: [N] | Altas: [N] | Médias: [N] | Baixas: [N]
- Risco geral: [Crítico/Alto/Médio/Baixo]

### Vulnerabilidades Detalhadas
[Para cada vulnerabilidade, usar o formato acima]

### Recomendações Prioritárias
[Lista das 3-5 correções mais importantes]
""",
        expected_output="Relatório de análise de segurança com vulnerabilidades categorizadas por OWASP Top 10, impacto e recomendações",
        agent=analista,
    )
    tasks.append(task_analise)

    # ── Task 2: Testes de Penetração (se mode for pentest ou full) ──
    if mode in ("pentest", "full"):
        task_pentest = Task(
            description=f"""\
DESCRIÇÃO DO SISTEMA:
{descricao}

SEU TRABALHO — TESTES DE PENETRAÇÃO AUTOMATIZADOS:

Com base na análise de segurança realizada, execute testes de penetração simulados
contra o sistema descrito. Para cada vetor de ataque testado, documente:

1. **Injeção SQL / NoSQL**:
   - Tente identificar pontos de entrada onde dados do usuário são processados
   - Descreva payloads que poderiam ser usados
   - Resultado esperado do ataque

2. **Cross-Site Scripting (XSS)**:
   - Identifique pontos onde input do usuário é refletido ou armazenado
   - Classifique como Reflected, Stored ou DOM-based
   - Descreva payloads e impacto

3. **Cross-Site Request Forgery (CSRF)**:
   - Verifique se há proteção CSRF em operações sensíveis
   - Descreva como um ataque poderia ser executado

4. **IDOR (Insecure Direct Object References)**:
   - Identifique endpoints que expõem IDs de objetos
   - Descreva como acessar recursos não autorizados

5. **Broken Authentication**:
   - Teste cenários de session fixation, session hijacking
   - Verifique políticas de senha, rate limiting, MFA

6. **SSRF (Server-Side Request Forgery)**:
   - Identifique funcionalidades que fazem requisições a URLs fornecidas pelo usuário

7. **File Upload Vulnerabilities**:
   - Se houver upload, teste: tipo de arquivo, tamanho, path traversal, double extension

8. **Security Misconfiguration**:
   - Verifique: headers de segurança (CSP, HSTS, X-Frame-Options), CORS, debug endpoints

Para cada ataque, forneça:
- **Vetor**: qual tipo de ataque
- **Alvo**: endpoint ou funcionalidade específica
- **Payload**: descrição do payload ou técnica usada
- **Severidade**: Crítico/Alto/Médio/Baixo
- **PoC**: Passo a passo reproduzível do ataque
- **Resultado Esperado**: o que aconteceria se o ataque fosse bem-sucedido
""",
            expected_output="Relatório de testes de penetração com vetores de ataque, payloads, severidade e provas de conceito",
            agent=pentester,
        )
        tasks.append(task_pentest)

    # ── Task 3: Compliance (se mode for compliance ou full) ──
    if mode in ("compliance", "full"):
        task_compliance = Task(
            description=f"""\
DESCRIÇÃO DO SISTEMA:
{descricao}

SEU TRABALHO — VERIFICAÇÃO DE COMPLIANCE:

Com base na análise de segurança e testes de penetração realizados, verifique
a conformidade do sistema com as seguintes regulamentações:

### 1. LGPD (Lei Geral de Proteção de Dados — Brasil)
Verifique:
- **Art. 7º**: Base legal para tratamento de dados pessoais
- **Art. 9º**: Direito de acesso do titular
- **Art. 11**: Tratamento de dados sensíveis
- **Art. 15-18**: Direitos dos titulares (acesso, correção, exclusão, portabilidade)
- **Art. 46**: Medidas de segurança técnicas e administrativas
- **Art. 48**: Comunicação de incidentes à ANPD

### 2. GDPR (General Data Protection Regulation — UE)
Verifique:
- **Art. 5**: Princípios (licitude, finalidade, minimização, exatidão, armazenamento, integridade)
- **Art. 7**: Condições para consentimento
- **Art. 17**: Direito ao apagamento ("right to be forgotten")
- **Art. 25**: Privacy by Design e Privacy by Default
- **Art. 32**: Segurança do processamento
- **Art. 33-34**: Notificação de violação de dados

### 3. SOC2 (Service Organization Control)
Verifique os critérios Trust Service:
- **Security**: Proteção contra acesso não autorizado
- **Availability**: Disponibilidade do sistema
- **Processing Integrity**: Processamento autorizado e preciso
- **Confidentiality**: Proteção de informações confidenciais
- **Privacy**: Coleta, uso, retenção e descarte de dados pessoais

### 4. ISO 27001
Verifique os controles dos Anexos A:
- A.9: Controle de acesso
- A.10: Criptografia
- A.12: Segurança operacional
- A.14: Aquisição, desenvolvimento e manutenção de sistemas
- A.18: Conformidade

Para cada regulamentação, documente:
- **Status**: Conforme / Não Conforme / Parcialmente Conforme
- **Gaps**: O que está faltando para estar em conformidade
- **Ações Corretivas**: O que precisa ser implementado
- **Prioridade**: Alta/Média/Baixa
- **Prazo Sugerido**: Imediato / Curto prazo / Médio prazo / Longo prazo
""",
            expected_output="Relatório de compliance com status de conformidade para LGPD, GDPR, SOC2 e ISO 27001, gaps e ações corretivas",
            agent=compliance,
        )
        tasks.append(task_compliance)

    # ── Task 4: Correção de Vulnerabilidades (sempre presente no full) ──
    if mode == "full":
        task_correcao = Task(
            description=f"""\
DESCRIÇÃO DO SISTEMA:
{descricao}

SEU TRABALHO — CORREÇÃO DE VULNERABILIDADES:

Com base nas vulnerabilidades identificadas na análise de segurança, testes de
penetração e gaps de compliance, implemente correções para cada vulnerabilidade.

Para cada correção, documente:

1. **Vulnerabilidade**: qual vulnerabilidade está sendo corrigida
2. **Categoria OWASP**: classificação OWASP
3. **Severidade Original**: qual era a severidade antes da correção
4. **Abordagem de Correção**: explique a estratégia usada
5. **Código/Configuração**: descreva as mudanças necessárias no código ou configuração
6. **Validação**: como verificar se a correção é eficaz
7. **Efeitos Colaterais**: possíveis impactos em funcionalidades existentes
8. **Severidade Pós-Correção**: qual a severidade após a correção (deve ser Baixa ou N/A)

Princípios de codificação segura a seguir:
- **Defense in Depth**: múltiplas camadas de proteção
- **Least Privilege**: mínimo privilégio necessário
- **Fail Secure**: falhar de forma segura, não insegura
- **Input Validation**: validar sempre no backend, nunca confiar no frontend
- **Output Encoding**: codificar saída para evitar XSS
- **Parameterized Queries**: usar prepared statements para evitar injection
- **Secure Cryptography**: usar algoritmos e modos seguros (não MD5, SHA1, ECB)
- **Secure Session Management**: tokens seguros, httpOnly, secure flags
- **CSP**: Content Security Policy para mitigar XSS
- **Rate Limiting**: proteger contra brute force e DoS
""",
            expected_output="Plano de correção de vulnerabilidades com abordagens, código/configuração e validação para cada falha",
            agent=engenheiro,
        )
        tasks.append(task_correcao)

    # ── Task 5: Quality Gate — Re-análise pós-correção (apenas no full) ──
    if mode == "full":
        task_quality_gate = Task(
            description=f"""\
DESCRIÇÃO DO SISTEMA:
{descricao}

SEU TRABALHO — QUALITY GATE: RE-ANÁLISE PÓS-CORREÇÃO:

Revise as correções propostas pelo Engenheiro de Correção e verifique:

1. **Eficácia**: As correções realmente eliminam as vulnerabilidades?
2. **Completude**: Todas as vulnerabilidades identificadas foram tratadas?
3. **Segurança**: As correções introduzem novas vulnerabilidades?
4. **Impacto**: As correções quebram funcionalidades existentes?
5. **Melhores Práticas**: As correções seguem as melhores práticas de segurança?

Emita um veredito:

## QUALITY GATE — VEREDITO

### Vulnerabilidades Remanescentes
- Críticas: [N] — [PASS/FAIL — deve ser 0]
- Altas: [N] — [PASS/FAIL — deve ser 0]
- Médias: [N] — [PASS/FAIL — aceitável se justificado]
- Baixas: [N] — [PASS/FAIL — aceitável se justificado]

### Resultado Final
**VEREDITO: [PASS/FAIL]**

Se PASS: O sistema atingiu o nível aceitável de segurança.
Se FAIL: Liste especificamente o que precisa ser corrigido antes da aprovação.
""",
            expected_output="Quality gate verdict: PASS/FAIL com análise de vulnerabilidades remanescentes e justificativas",
            agent=analista,
        )
        tasks.append(task_quality_gate)

    # --- Crew ---
    agents = [analista]
    if mode in ("pentest", "full"):
        agents.append(pentester)
    if mode in ("compliance", "full"):
        agents.append(compliance)
    if mode == "full":
        agents.append(engenheiro)

    crew = Crew(
        agents=agents,
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
        description="cp-seguranca: Segurança de Software Crew (self-contained)",
    )
    parser.add_argument(
        "descricao",
        nargs="?",
        help="Descrição do sistema/código a ser auditado",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="Arquivo com a descrição do sistema (alternativa ao argumento posicional)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Arquivo de saída para salvar o relatório de segurança",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["code-review", "pentest", "compliance", "full"],
        default="full",
        help="Modo de operação (default: full — ciclo completo)",
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

    output_path = args.output
    mode = args.mode

    print(f"\n🔒 Descrição: {descricao[:120]}...")
    print(f"📂 Agentes: embutidos (self-contained)")
    print(f"🎯 Modo: {mode}")
    print()

    crew = build_crew(descricao, mode, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew montada, agentes:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks):
            desc_short = task.description[:80].replace("\n", " ").strip()
            print(f"  {i+1}. {desc_short}...")
        print(f"\n✅ Crew pronta. Remova --dry-run para executar.")
        return

    print("🚀 Executando crew de segurança...\n")
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Relatório de Segurança gerado!\n")
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
        out_file = output_dir / f"seguranca_{mode}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Salvo em: {out_file.resolve()}")


if __name__ == "__main__":
    main()