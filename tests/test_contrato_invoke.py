"""DT-03 — Valida o contrato `invoke` do orquestrador contra o argparse real.

O orquestrador declara, no dict `CREWS`, como cada skill é acionada
(`invoke.briefing_arg` e `invoke.output`). Esse metadado é mantido à mão: se uma
skill mudar seu argparse e o metadado não acompanhar, a fase quebra só em
execução — e, por causa do quality gate, podia até passar despercebida.

A verificação não faz regex sobre o código-fonte: usa o `--help` real de cada
skill (que o DT-07 garantiu funcionar sempre) e, no teste mais forte, executa a
linha de comando que o próprio orquestrador montaria.

Este arquivo teria pego o BUG-05 (modo goal-loop enviava só `--goal`, mas a
skill exigia `--steps`).
"""
import importlib.util
import subprocess

import pytest

from conftest import EXIT_OK, REPO_ROOT, SKILLS_DIR

ORQ_RUN = SKILLS_DIR / "cp-orquestrador" / "scripts" / "run.py"


def _carrega_orquestrador():
    """Importa o run.py do orquestrador como módulo, para ler CREWS/MODOS."""
    spec = importlib.util.spec_from_file_location("orq_run", ORQ_RUN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ORQ = _carrega_orquestrador()

# Crews que apontam para uma skill externa (o NEXUS roda nativo, sem subprocess).
CREWS_COM_SKILL = sorted(
    k for k, v in ORQ.CREWS.items()
    if k in ORQ.SKILL_PATHS and ORQ.SKILL_PATHS[k].exists()
)

# Crews executadas nativamente pelo orquestrador (NexusExecutor), sem subprocess.
CREWS_NATIVAS = {"full-dev"}

# Default aplicado por `_build_cli_args` quando a crew nao declara `invoke`.
# As 8 crews do pipeline dependem dele — e isso e intencional, nao um esquecimento.
INVOKE_DEFAULT = {"briefing_arg": "input", "output": True}


def invoke_efetivo(crew_key: str) -> dict:
    """Metadado `invoke` como o codigo de producao o enxerga."""
    return ORQ.CREWS[crew_key].get("invoke", INVOKE_DEFAULT)


# Qual flag cada briefing_arg exige que exista no argparse da skill.
FLAG_POR_BRIEFING_ARG = {
    "goal": "--goal",
    "daemon": "--daemon",
    "dir": "--dir",
    "input": "--input",
    "positional": None,  # posicional não aparece como flag
}


@pytest.fixture(scope="module")
def help_por_crew(clean_env, python_cmd):
    """Saída de `--help` de cada skill referenciada pelo orquestrador."""
    saidas = {}
    for ck in CREWS_COM_SKILL:
        path = ORQ.SKILL_PATHS[ck]
        r = subprocess.run(
            [python_cmd, str(path), "--help"],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT), env=clean_env, encoding="utf-8", errors="replace",
        )
        assert r.returncode == EXIT_OK, f"{ck}: --help falhou\n{r.stdout}{r.stderr}"
        saidas[ck] = r.stdout
    return saidas


@pytest.mark.parametrize("crew_key", CREWS_COM_SKILL)
def test_briefing_arg_e_valor_conhecido(crew_key):
    """O `briefing_arg` efetivo precisa ser um dos modos que `_build_cli_args` trata.

    Um valor novo (ex.: "daemon" quando foi introduzido) sem o branch
    correspondente cai silenciosamente no ramo `else`, que passa o briefing como
    posicional — e a skill rejeita.
    """
    briefing_arg = invoke_efetivo(crew_key).get("briefing_arg")
    assert briefing_arg in FLAG_POR_BRIEFING_ARG, (
        f"{crew_key}: briefing_arg desconhecido: {briefing_arg!r}. "
        f"Adicione o branch em _build_cli_args antes de usar.")


@pytest.mark.parametrize("crew_key", CREWS_COM_SKILL)
def test_output_declarado_bate_com_argparse(crew_key, help_por_crew):
    """`invoke.output` precisa refletir se a skill aceita mesmo `--output`.

    Declarar `output=True` numa skill que não aceita faz o argparse dela
    rejeitar o flag e a fase morrer.
    """
    declarado = invoke_efetivo(crew_key).get("output", True)
    aceita = "--output" in help_por_crew[crew_key]
    assert declarado == aceita, (
        f"{crew_key}: invoke.output={declarado} mas a skill "
        f"{'aceita' if aceita else 'NAO aceita'} --output")


@pytest.mark.parametrize("crew_key", CREWS_COM_SKILL)
def test_briefing_arg_existe_na_skill(crew_key, help_por_crew):
    """A flag exigida pelo `briefing_arg` precisa existir no argparse da skill."""
    briefing_arg = invoke_efetivo(crew_key)["briefing_arg"]
    flag = FLAG_POR_BRIEFING_ARG[briefing_arg]
    if flag is None:
        return
    assert flag in help_por_crew[crew_key], (
        f"{crew_key}: invoke.briefing_arg={briefing_arg!r} exige {flag}, "
        f"ausente no --help da skill")


@pytest.mark.parametrize("crew_key", CREWS_COM_SKILL)
def test_comando_montado_pelo_orquestrador_e_aceito(crew_key, clean_env, python_cmd,
                                                    tmp_path):
    """O teste forte: roda a linha que o orquestrador montaria, com --dry-run.

    Constrói os argumentos pelo mesmo `_build_cli_args` usado em produção e
    verifica que a skill os aceita. Um erro de argparse (exit 2 do argparse,
    "unrecognized arguments", "required") reprova.

    Este é o teste que teria pego o BUG-05.
    """
    # Construtor real: montar o executor a mao esconde atributos novos.
    executor = ORQ.PipelineExecutor(
        briefing="briefing de teste", mode="full",
        output_dir=str(tmp_path), python_cmd=python_cmd,
    )

    args = executor._build_cli_args(crew_key)
    assert args is not None, f"{crew_key}: _build_cli_args devolveu None"

    # cp-agilista sem --dry-run sobe um daemon de polling: não roda aqui.
    if "--daemon" in args:
        pytest.skip("cp-agilista em modo daemon nao termina sozinho")

    r = subprocess.run(
        args + ["--dry-run"], capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=clean_env, encoding="utf-8", errors="replace",
    )
    saida = r.stdout + r.stderr

    assert "unrecognized arguments" not in saida, (
        f"{crew_key}: o orquestrador passa flag que a skill rejeita.\n"
        f"  comando: {' '.join(str(a) for a in args)}\n{saida}")
    assert "the following arguments are required" not in saida, (
        f"{crew_key}: a skill exige argumento que o orquestrador nao envia "
        f"(caso do BUG-05).\n  comando: {' '.join(str(a) for a in args)}\n{saida}")
    assert r.returncode == EXIT_OK, (
        f"{crew_key}: comando montado pelo orquestrador falhou (exit "
        f"{r.returncode}).\n  comando: {' '.join(str(a) for a in args)}\n{saida}")


def test_todo_modo_referencia_crew_existente():
    """Nenhum modo pode apontar para crew inexistente.

    `full-dev` e a excecao legitima: roda nativamente pelo NexusExecutor, sem
    entrada em CREWS.
    """
    for modo, info in ORQ.MODOS.items():
        for ck in info["crews"]:
            assert ck in ORQ.CREWS or ck in CREWS_NATIVAS, (
                f"modo {modo!r} referencia crew inexistente: {ck!r}")


def test_toda_crew_com_skill_tem_caminho_valido():
    """Toda crew que aponta para skill externa precisa que o run.py exista."""
    faltando = [
        ck for ck, path in ORQ.SKILL_PATHS.items()
        if ck in ORQ.CREWS and not path.exists()
    ]
    assert not faltando, f"skills declaradas mas ausentes no disco: {faltando}"
