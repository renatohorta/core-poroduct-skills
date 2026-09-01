"""Regressão do quality gate do orquestrador (BUG-03 e BUG-04).

O quality gate é a principal garantia do orquestrador: se ele aprova uma fase
que falhou, todas as fases seguintes rodam sobre um artefato vazio e o relatório
final mente. Estes testes fixam os dois modos de falha já observados.
"""
import importlib.util

import pytest

from conftest import SKILLS_DIR

ORQ_RUN = SKILLS_DIR / "cp-orchestrator" / "scripts" / "run.py"


def _carrega_orquestrador():
    spec = importlib.util.spec_from_file_location("orq_run_gate", ORQ_RUN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ORQ = _carrega_orquestrador()


@pytest.fixture
def gate():
    """Só o método de gate — sem tocar no resto do executor."""
    executor = ORQ.PipelineExecutor.__new__(ORQ.PipelineExecutor)
    return lambda texto, rc=0: executor._check_quality_gate("fase-x", texto, rc)


# ─────────────────────────── BUG-03 ───────────────────────────

@pytest.mark.parametrize("returncode", [1, 2, 3, 127])
def test_exit_code_diferente_de_zero_reprova(gate, returncode):
    """Exit code != 0 é FAIL, mesmo com saída de aparência positiva.

    Regressão do BUG-03: a skill morria com traceback, o texto não continha
    nenhuma fail-keyword, o gate devolvia WARN e o pipeline reportava
    "Pipeline concluído com sucesso".
    """
    resultado = gate("Everything APPROVED with SUCCESS", returncode)
    assert resultado["status"] == "FAIL"
    assert str(returncode) in resultado["detail"]


def test_traceback_puro_reprova(gate):
    """O caso real: ModuleNotFoundError com exit 1."""
    saida = ("Traceback (most recent call last):\n"
             "  File \"run.py\", line 17, in <module>\n"
             "ModuleNotFoundError: No module named 'crewai'")
    assert gate(saida, 1)["status"] == "FAIL"


def test_traceback_reprova_mesmo_com_exit_zero(gate):
    """Defesa em profundidade: TRACEBACK é fail-keyword, não só o exit code."""
    assert gate("Traceback (most recent call last): erro", 0)["status"] == "FAIL"


# ─────────────────────────── BUG-04 ───────────────────────────

@pytest.mark.parametrize("saida", [
    "Error: invalid API token",       # "OK" inside "token"
    "Broken pipeline detected",      # "OK" inside "Broken"
    "Cookbook unavailable",           # "OK" inside "Cookbook"
])
def test_ok_como_substring_nao_aprova(gate, saida):
    """Regressão do BUG-04: keywords casavam como substring.

    "invalid API token" — o erro mais comum quando falta credencial — era
    classificado como PASS porque "OK" cabe dentro de "token".
    """
    assert gate(saida, 0)["status"] != "PASS", (
        f"{saida!r} nao pode ser PASS: 'OK' aparece so como substring")


def test_ok_como_palavra_continua_aprovando(gate):
    """A correção não pode custar o caso legítimo."""
    assert gate("Testes OK", 0)["status"] == "PASS"


@pytest.mark.parametrize("saida,esperado", [
    ("All tests PASS, coverage 92%", "PASS"),
    ("Build APPROVED", "PASS"),
    ("Pipeline with PENDING caveat", "WARN"),
    ("Quality gate FAIL: incomplete requirements", "FAIL"),
    ("output with no recognizable indicator", "WARN"),
])
def test_classificacao_por_palavra_inteira(gate, saida, esperado):
    assert gate(saida, 0)["status"] == esperado
