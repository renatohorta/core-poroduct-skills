#!/usr/bin/env python3
"""
cp-goal-loop — Autonomous Try-Fix-Retry Loop (self-contained)

Executa um processo ate alcancar a condicao de sucesso.
Quando encontra um bloqueio, PARA, diagnostica, implementa a correcao,
valida isoladamente, e RECOMECA o processo do inicio.

Uso:
  python run.py --goal "deploy em staging funcionando" --steps "migrate,test,deploy,health-check"
  python run.py --goal "onboarding completo" --steps-file steps.json
  python run.py --goal "sync de contatos" --max-attempts 3
"""

import argparse
import sys
import os
import json
import time
import traceback
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
    "engineering-backend-architect": {
        "role": "Backend Architect",
        "goal": "Execute the process to achieve the defined goal",
        "backstory": (
            "Senior backend architect specializing in scalable system design, "
            "database architecture, API development, and cloud infrastructure. "
            "You build robust, secure, performant server-side applications and microservices. "
            "You are strategic, security-focused, scalability-minded, and reliability-obsessed."
        ),
    },
    "engineering-senior-developer": {
        "role": "Senior Developer",
        "goal": "Diagnose root causes of failures and implement minimal fixes",
        "backstory": (
            "Senior full-stack developer who creates premium web experiences. "
            "You are creative, detail-oriented, performance-focused, and innovation-driven. "
            "You've built many systems and know the difference between a proper fix and a workaround. "
            "Expert debugger who finds root causes fast."
        ),
    },
    "testing-api-tester": {
        "role": "QA Validator",
        "goal": "Validate that fixes work and the process can continue",
        "backstory": (
            "Expert API testing specialist focused on comprehensive API validation, "
            "performance testing, and quality assurance. You ensure reliable, performant, "
            "and secure API integrations. Thorough, security-conscious, automation-driven, "
            "and quality-obsessed. You break APIs before users do."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    """Get a CrewAI Agent from the embedded definitions."""
    data = AGENTS.get(slug)
    if not data:
        print(f"  [!] Agent not found: {slug} — using defaults")
        return Agent(
            role=slug.replace("-", " ").title(),
            goal="Complete the assigned task with excellence",
            backstory="Specialized AI agent",
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

def build_loop_crew(goal: str, steps: list, attempt: int, previous_failures: list):
    """Build a CrewAI crew for one attempt of the goal loop."""

    runner = get_agent("engineering-backend-architect")
    debugger = get_agent("engineering-senior-developer")
    qa = get_agent("testing-api-tester")

    # --- Build failure context ---
    failure_context = ""
    if previous_failures:
        failure_context = "\n\nPREVIOUS FAILURES (learn from these):\n"
        for i, f in enumerate(previous_failures, 1):
            failure_context += f"\nFAILURE {i}:\n"
            failure_context += f"  Step: {f.get('step', 'unknown')}\n"
            failure_context += f"  Error: {f.get('error', 'unknown')}\n"
            failure_context += f"  Root cause: {f.get('root_cause', 'unknown')}\n"
            failure_context += f"  Fix applied: {f.get('fix', 'unknown')}\n"

    # --- Tasks ---
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))

    execute_process = Task(
        description=f"""
        GOAL: {goal}
        ATTEMPT: {attempt}

        PROCESS STEPS (execute in order):
        {steps_text}
        {failure_context}

        YOUR JOB:
        1. Execute each step in order
        2. For each step, report: SUCCESS or FAILURE
        3. If a step FAILS:
           - Stop immediately (do NOT continue to next steps)
           - Report exactly which step failed
           - Report the exact error message
           - Report what you think the root cause is
        4. If ALL steps SUCCEED:
           - Report GOAL ACHIEVED
           - Provide evidence for each step

        IMPORTANT: Stop at the FIRST failure. Do not skip steps.
        """,
        expected_output="Step-by-step execution report: SUCCESS on all steps, or FAILURE at a specific step with error details",
        agent=runner,
    )

    diagnose_and_fix = Task(
        description=f"""
        GOAL: {goal}
        ATTEMPT: {attempt}

        The Runner agent attempted the process and hit a failure.
        Your job is to diagnose and fix the root cause.

        STEPS:
        1. Read the Runner's failure report carefully
        2. Identify the ROOT CAUSE (not just the symptom)
        3. Implement the MINIMAL fix (do NOT refactor unrelated code)
        4. Validate the fix in isolation (run the failing step alone)
        5. Report: what was broken, what you changed, and proof the fix works

        RULES:
        - Only fix what's broken — no scope creep
        - If the fix requires a code change, make it and show the diff
        - If the fix requires a config change, make it and show before/after
        - If the fix requires data, create/update it
        - If you CANNOT fix it, say so clearly and explain why
        """,
        expected_output="Root cause analysis, fix description with file paths and diffs, and validation evidence",
        agent=debugger,
    )

    validate_fix = Task(
        description=f"""
        GOAL: {goal}
        ATTEMPT: {attempt}

        The Debugger claims to have fixed the blocker.
        Your job: validate the fix independently.

        1. Re-run the EXACT step that failed
        2. Verify it now passes
        3. Check that the fix didn't break anything else (quick regression)
        4. Report: FIX VALID or FIX INVALID

        If FIX VALID: the loop can restart from step 1
        If FIX INVALID: send back to Debugger with specific issues
        """,
        expected_output="Validation report: FIX VALID or FIX INVALID with evidence",
        agent=qa,
    )

    crew = Crew(
        agents=[runner, debugger, qa],
        tasks=[execute_process, diagnose_and_fix, validate_fix],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-goal-loop: Autonomous Try-Fix-Retry Loop (self-contained)",
    )
    parser.add_argument("--goal", "-g", required=True, help="Objetivo a ser alcancado")
    parser.add_argument(
        "--steps", "-s",
        help="Passos do processo, separados por virgula",
    )
    parser.add_argument(
        "--steps-file",
        help="Arquivo JSON com os passos (array de strings)",
    )
    parser.add_argument(
        "--max-attempts", "-n",
        type=int, default=5,
        help="Numero maximo de tentativas (default: 5)",
    )
    parser.add_argument(
        "--max-time",
        type=int, default=30,
        help="Tempo maximo em minutos (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o plano, sem executar",
    )
    args = parser.parse_args()

    # --- Parse steps ---
    if args.steps:
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    elif args.steps_file:
        steps = json.loads(Path(args.steps_file).read_text())
    else:
        print("[!] Forneca --steps ou --steps-file")
        sys.exit(1)

    if not steps:
        print("[!] Lista de passos vazia")
        sys.exit(1)

    # --- Show plan ---
    print(f"\n{'='*60}")
    print(f"  GOAL LOOP — Modo Autonomo (self-contained)")
    print(f"{'='*60}")
    print(f"  Objetivo: {args.goal}")
    print(f"  Max tentativas: {args.max_attempts}")
    print(f"  Max tempo: {args.max_time}min")
    print(f"  Passos ({len(steps)}):")
    for i, s in enumerate(steps, 1):
        print(f"    {i}. {s}")
    print()

    if args.dry_run:
        print("[i] DRY RUN — plano exibido. Remova --dry-run para executar.")
        return

    # --- Main loop ---
    start_time = time.time()
    max_seconds = args.max_time * 60
    previous_failures = []
    final_result = None

    for attempt in range(1, args.max_attempts + 1):
        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            print(f"\n[!] Tempo maximo ({args.max_time}min) excedido. Parando.")
            break

        print(f"\n{'='*60}")
        print(f"  TENTATIVA {attempt}/{args.max_attempts}")
        print(f"  Tempo decorrido: {elapsed/60:.1f}min")
        print(f"  Bloqueios anteriores: {len(previous_failures)}")
        print(f"{'='*60}\n")

        try:
            crew = build_loop_crew(args.goal, steps, attempt, previous_failures)
            result = crew.kickoff()
            result_str = str(result)

            # Check if goal was achieved
            success_markers = ["GOAL ACHIEVED", "ALL STEPS SUCCEED", "SUCCESS"]
            if any(m in result_str.upper() for m in success_markers):
                print(f"\n  [***] GOAL ALCANCADO na tentativa {attempt}!")
                final_result = {
                    "status": "success",
                    "attempts": attempt,
                    "total_time_min": (time.time() - start_time) / 60,
                    "previous_failures": len(previous_failures),
                    "result": result_str[:1000],
                }
                break
            else:
                print(f"\n  [!] Tentativa {attempt} nao alcancou o objetivo.")
                failure_info = {
                    "attempt": attempt,
                    "step": "unknown",
                    "error": result_str[:500],
                    "root_cause": "Could not extract from result",
                    "fix": "Could not extract from result",
                }
                previous_failures.append(failure_info)

        except Exception as e:
            print(f"\n  [!!] Tentativa {attempt} explodiu: {e}")
            traceback.print_exc()
            failure_info = {
                "attempt": attempt,
                "step": "unknown",
                "error": str(e),
                "root_cause": str(e),
                "fix": "Exception — could not apply fix",
            }
            previous_failures.append(failure_info)

    # --- Final report ---
    elapsed_total = (time.time() - start_time) / 60
    print(f"\n{'='*60}")
    print(f"  RELATORIO FINAL")
    print(f"{'='*60}")

    if final_result and final_result["status"] == "success":
        print(f"  [OK] GOAL ALCANCADO!")
        print(f"  Tentativas: {final_result['attempts']}")
        print(f"  Tempo total: {final_result['total_time_min']:.1f}min")
        print(f"  Bloqueios resolvidos: {final_result['previous_failures']}")
    else:
        print(f"  [!!] GOAL NAO ALCANCADO apos {attempt} tentativas")
        print(f"  Tempo total: {elapsed_total:.1f}min")
        print(f"  Bloqueios encontrados: {len(previous_failures)}")
        print(f"\n  Bloqueios residuais:")
        for i, f in enumerate(previous_failures, 1):
            print(f"    {i}. Step: {f.get('step', '?')}")
            print(f"       Erro: {f.get('error', '?')[:200]}")

    # Save report
    output_dir = Path(__file__).resolve().parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "goal": args.goal,
        "steps": steps,
        "max_attempts": args.max_attempts,
        "timestamp": timestamp,
        "status": final_result["status"] if final_result else "failed",
        "attempts_made": attempt,
        "total_time_min": elapsed_total,
        "previous_failures": previous_failures,
        "final_result": final_result,
    }
    report_file = output_dir / f"goal_loop_{timestamp}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Relatorio salvo em: {report_file}")


if __name__ == "__main__":
    main()