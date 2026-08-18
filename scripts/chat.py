#!/usr/bin/env python3
"""
chat.py — Conversa direta com as skills cp-* usando o LLM via .env.

Permite acionar qualquer skill cp-* de forma interativa, usando o LLM
configurado no .env (mesma convenção do crewbotics-back: LLM_MODEL,
GEMINI_API_KEY/OPENAI_API_KEY/etc.). Não depende do agente (Hermes/Claude).

Uso:
  python chat.py                          # lista as skills disponíveis
  python chat.py cp-requisitos            # conversa com a skill
  python chat.py cp-requisitos "briefing" # executa com briefing direto
  python chat.py --skill cp-requisitos --prompt "sistema de agendamento"
  python chat.py --list                   # lista skills
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# Skills que aceitam briefing posicional (conversa direta)
CHAT_SKILLS = {
    "cp-requisitos": "briefing",
    "cp-arquitetura": "briefing",
    "cp-implementacao": "briefing",
    "cp-testes": "briefing",
    "cp-seguranca": "briefing",
    "cp-devops": "briefing",
    "cp-documentacao": "briefing",
    "cp-qualidade": "briefing",
    "cp-bug-fix": "bug_description",
    "cp-competitive-analysis": "context",
    "cp-manutencao": "descricao",
    "cp-goal-loop": "goal",
    "cp-orquestrador": "briefing",
}


def _load_dotenv(root: Path = None) -> dict:
    """Carrega variáveis de um .env na raiz do projeto."""
    base = Path(root) if root else Path.cwd()
    env_file = base / ".env"
    if not env_file.exists():
        return {}
    env = {}
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def list_skills():
    """Lista as skills disponíveis para conversa."""
    print("=== Skills cp-* disponíveis para conversa ===")
    for name, arg in CHAT_SKILLS.items():
        run_py = SKILLS_DIR / name / "scripts" / "run.py"
        status = "✅" if run_py.exists() else "❌"
        print(f"  {status} {name} (arg: {arg})")
    print("\nUso: python chat.py <skill> \"<briefing>\"")
    print("     python chat.py cp-requisitos \"sistema de agendamento\"")


def _resolve_python():
    """Resolve o interpretador Python que tem crewai instalado.

    Prioridade:
      1. Env var CP_SKILLS_PYTHON (explicita)
      2. .venv/Scripts/python.exe no diretório atual ou pai
      3. sys.executable (fallback)
    """
    explicit = os.environ.get("CP_SKILLS_PYTHON")
    if explicit and Path(explicit).exists():
        return explicit

    # Procura .venv no cwd e em diretórios pai
    cwd = Path.cwd()
    for base in [cwd] + list(cwd.parents[:4]):
        for venv in [base / ".venv", base / "venv"]:
            py = venv / "Scripts" / "python.exe"
            if py.exists():
                # Confirma que tem crewai
                import subprocess
                r = subprocess.run([str(py), "-c", "import crewai"],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    return str(py)
    return sys.executable


def run_skill(skill: str, prompt: str, extra_args: list = None):
    """Executa uma skill cp-* com o briefing fornecido."""
    run_py = SKILLS_DIR / skill / "scripts" / "run.py"
    if not run_py.exists():
        print(f"❌ Skill '{skill}' não encontrada em {run_py}")
        return 1

    # Carrega o .env e injeta no ambiente
    dotenv = _load_dotenv()
    for k, v in dotenv.items():
        os.environ.setdefault(k, v)

    # Resolve o Python com crewai
    python = _resolve_python()

    # Monta o comando
    cmd = [python, str(run_py)]
    if prompt:
        cmd.append(prompt)
    if extra_args:
        cmd.extend(extra_args)

    print(f"🚀 Executando {skill} com o LLM do .env...")
    print(f"   Python: {python}")
    print(f"   Comando: {' '.join(cmd)}\n")

    import subprocess
    result = subprocess.run(cmd, cwd=str(SKILLS_DIR.parent))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="chat.py — Conversa direta com as skills cp-* via .env",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python chat.py --list
  python chat.py cp-requisitos "sistema de agendamento para clínicas"
  python chat.py --skill cp-requisitos --prompt "sistema de agendamento"
  python chat.py cp-bug-fix "o endpoint /login retorna 500"
        """,
    )
    parser.add_argument("skill", nargs="?", help="Nome da skill (ex: cp-requisitos)")
    parser.add_argument("prompt", nargs="?", help="Briefing/prompt para a skill")
    parser.add_argument("--skill", dest="skill_flag", help="Nome da skill (alternativa)")
    parser.add_argument("--prompt", dest="prompt_flag", help="Briefing (alternativa)")
    parser.add_argument("--list", "-l", action="store_true", help="Lista as skills")
    parser.add_argument("--extra", nargs="*", default=[], help="Args extras para a skill")
    # parse_known_args: flags desconhecidas (ex: --dry-run) são capturadas e
    # repassadas para a skill, em vez de o argparse rejeitar.
    args, unknown = parser.parse_known_args()

    if args.list:
        list_skills()
        return 0

    skill = args.skill or args.skill_flag
    prompt = args.prompt or args.prompt_flag

    if not skill:
        list_skills()
        return 0

    if skill not in CHAT_SKILLS:
        print(f"❌ Skill '{skill}' não suporta conversa direta.")
        print("   Disponíveis:", ", ".join(CHAT_SKILLS.keys()))
        return 1

    # Combina --extra com flags desconhecidas (ex: --dry-run)
    extra = list(args.extra) + list(unknown)
    return run_skill(skill, prompt, extra)


if __name__ == "__main__":
    sys.exit(main())
