"""DT-02 — Smoke tests das skills cp-*.

Verifica o mínimo que toda skill deve garantir, sem chamar LLM:
  - `--help` funciona sempre (mesmo sem crewai instalado)
  - `--dry-run` monta a crew sem exigir credencial
  - a ausência de credencial falha com código 2 e mensagem acionável
  - a ausência de crewai falha com código 3 e mensagem acionável
"""
import subprocess
import sys
import tempfile

import pytest

from conftest import (EXIT_NO_CREWAI, EXIT_NO_LLM, EXIT_OK, REPO_ROOT,
                      skill_names, skill_script)

SKILLS = skill_names()

# Briefing mínimo aceito por cada skill, conforme seu contrato CLI próprio.
# Ver .context/docs/02-arquitetura.md (metadado `invoke`).
BRIEFING_ARGS = {
    "cp-goal-loop": ["--goal", "objetivo de teste"],
    "cp-agilista": [],
    "cp-inicializador-doc": [],
}
DEFAULT_BRIEFING = ["briefing de teste"]

# Skills que não usam LLM: são Python puro e rodam integralmente sem credencial.
NO_LLM_SKILLS = {"cp-agilista", "cp-inicializador-doc"}


def briefing_for(skill: str, tmp_path=None):
    if skill == "cp-inicializador-doc":
        return ["--dir", str(tmp_path or tempfile.mkdtemp())]
    return BRIEFING_ARGS.get(skill, DEFAULT_BRIEFING)


def run_skill(skill, args, env, python_cmd, timeout=120):
    return subprocess.run(
        [python_cmd, str(skill_script(skill))] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )


@pytest.mark.parametrize("skill", SKILLS)
def test_help_sempre_funciona(skill, clean_env, python_cmd):
    """`--help` deve funcionar em toda skill, inclusive sem crewai (DT-07).

    Regressão: antes do DT-07, 12 das 15 skills importavam crewai no topo do
    módulo e morriam com ModuleNotFoundError antes do argparse.
    """
    r = run_skill(skill, ["--help"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--help falhou:\n{r.stdout}\n{r.stderr}"
    assert "usage:" in r.stdout.lower()


@pytest.mark.parametrize("skill", SKILLS)
def test_help_funciona_sem_crewai(skill, clean_env, python_cmd, tmp_path):
    """`--help` não pode depender de crewai — simulado bloqueando o import."""
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai bloqueado pelo teste')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)

    r = run_skill(skill, ["--help"], env, python_cmd)
    assert r.returncode == EXIT_OK, (
        f"--help quebrou sem crewai (DT-07):\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS))
def test_dry_run_nao_exige_credencial(skill, clean_env, python_cmd):
    """`--dry-run` monta a crew e lista os agentes sem nenhuma chave de LLM."""
    r = run_skill(skill, briefing_for(skill) + ["--dry-run"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, (
        f"--dry-run exigiu credencial:\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS - {"cp-orquestrador"}))
def test_sem_llm_falha_com_mensagem_acionavel(skill, clean_env, python_cmd):
    """Sem credencial, a execução real sai com 2 e diz o que configurar (DT-08).

    Regressão: antes, `build_crew_llm()` devolvia None, o None chegava ao
    Agent() e o CrewAI caía no default OpenAI, falhando lá na frente com
    `OPENAI_API_KEY is required`.
    """
    r = run_skill(skill, briefing_for(skill), clean_env, python_cmd)
    saida = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_LLM, (
        f"esperava exit {EXIT_NO_LLM}, veio {r.returncode}:\n{saida}")
    assert "LLM_API_KEY" in saida, "a mensagem precisa dizer o que configurar"
    assert "--dry-run" in saida, "a mensagem precisa apontar a alternativa sem LLM"


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS))
def test_sem_crewai_falha_com_mensagem_acionavel(skill, clean_env, python_cmd, tmp_path):
    """Sem a lib, a execução sai com 3 e instrui a instalar (DT-07)."""
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai bloqueado pelo teste')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)

    r = run_skill(skill, briefing_for(skill), env, python_cmd)
    saida = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_CREWAI, (
        f"esperava exit {EXIT_NO_CREWAI}, veio {r.returncode}:\n{saida}")
    assert "pip install crewai" in saida
    assert "Traceback" not in saida, "deve ser mensagem acionável, não traceback"


@pytest.mark.parametrize("skill", sorted(NO_LLM_SKILLS))
def test_skills_sem_llm_rodam_integralmente(skill, clean_env, python_cmd, tmp_path):
    """cp-agilista e cp-inicializador-doc são Python puro: rodam sem credencial."""
    args = briefing_for(skill, tmp_path) + ["--dry-run"]
    r = run_skill(skill, args, clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"{skill} falhou sem LLM:\n{r.stdout}\n{r.stderr}"


def test_inicializador_cria_kanban_desde_o_inicio(clean_env, python_cmd, tmp_path):
    """O kanban nasce na inicializacao, nao no primeiro run do cp-agilista.

    Regressao: `.context/docs/06-kanban.md` e o `cp-agilista` referenciam
    `.context/kanban/`, mas so o `--init` do agilista criava as colunas — em
    projeto novo o ponteiro ficava orfao.
    """
    r = run_skill("cp-inicializador-doc", ["--dir", str(tmp_path)],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"inicializador falhou: {r.stdout} {r.stderr}"

    kanban = tmp_path / ".context" / "kanban"
    assert (kanban / "README.md").is_file(), "kanban/README.md nao foi criado"

    # As colunas espelham KANBAN_COLUMNS + BLOCKED_DIR de cp-agilista.
    colunas = ["1-backlog", "2-todo", "3-doing", "4-review",
               "5-testing", "6-staging", "7-done", "blocked"]
    for col in colunas:
        assert (kanban / col).is_dir(), f"coluna {col} nao foi criada"
        # git nao versiona diretorio vazio: sem .gitkeep a estrutura nao viaja.
        assert (kanban / col / ".gitkeep").is_file(), f"{col}/.gitkeep faltando"


def test_colunas_do_kanban_batem_entre_agilista_e_inicializador():
    """As duas skills declaram as colunas separadamente — nao podem divergir."""
    import re

    def colunas(skill, const):
        src = skill_script(skill).read_text(encoding="utf-8")
        bloco = re.search(rf"^{const} = \[(.*?)\]", src, re.S | re.M)
        assert bloco, f"{const} nao encontrado em {skill}"
        return re.findall(r'"([^"]+)"', bloco.group(1))

    assert colunas("cp-agilista", "KANBAN_COLUMNS") ==         colunas("cp-inicializador-doc", "KANBAN_COLUMNS")


def test_install_sh_dry_run_lista_todas_as_skills(clean_env, tmp_path, bash_cmd):
    """`install.sh --dry-run` deve listar as 15 skills e o helper _shared."""
    env = dict(clean_env)
    env["HERMES_SKILLS_DIR"] = str(tmp_path / "hermes")
    env["CLAUDE_SKILLS_DIR"] = str(tmp_path / "claude")

    r = subprocess.run(
        [bash_cmd, "scripts/install.sh", "--dry-run"],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )
    assert r.returncode == EXIT_OK, f"install.sh falhou:\n{r.stdout}\n{r.stderr}"
    for skill in SKILLS:
        assert skill in r.stdout, f"{skill} não apareceu no plano de instalação"
    assert "_shared" in r.stdout, "_shared precisa ser propagado (não é skill)"
