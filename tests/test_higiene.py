"""Higiene do repositório — portabilidade e segredos.

Dois invariantes que o README promete e que só um teste mantém honesto:
  - **Portabilidade**: zero paths de SO/máquina e zero valores pessoais fixos.
  - **Segredos fora do repositório**: nenhuma chave versionada.
"""
import re
import subprocess

import pytest

from conftest import REPO_ROOT

# Extensões versionadas que valem inspeção.
EXTENSOES = ("*.py", "*.sh", "*.md", "*.txt", "*.yml", "*.yaml", "*.example")

# Diretórios ignorados (não versionados ou irrelevantes).
IGNORAR = {".git", ".venv", "venv", "__pycache__", "outputs", ".pytest_cache", "node_modules"}

# Paths de máquina/usuário que não podem estar hardcoded.
# Case-SENSITIVE de propósito: as references enumeram env vars como
# "USERPROFILE/HOME/LOCALAPPDATA", que casaria com /home/ sem distinção de caixa.
PADROES_PATH = [
    re.compile(r"[Cc]:[\\/]+Users[\\/]+[A-Za-z]"),   # home Windows
    re.compile(r"/c/Users/[A-Za-z]"),                # home Windows via git-bash
    re.compile(r"/home/[a-z][a-z0-9_-]*/"),          # home Linux
    re.compile(r"/Users/[a-z][a-z0-9_-]*/"),         # home macOS
]

# Formatos de chave de API de provedores reais.
PADROES_SEGREDO = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "chave OpenAI"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "chave Anthropic"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"), "chave Google/Gemini"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "token GitHub"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "token Slack"),
]


def arquivos_versionados():
    """Arquivos rastreados pelo git, filtrados por extensão."""
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                       cwd=str(REPO_ROOT), encoding="utf-8", errors="replace")
    if r.returncode != 0:
        pytest.skip("git indisponivel")
    for linha in r.stdout.splitlines():
        caminho = REPO_ROOT / linha.strip()
        if not caminho.is_file():
            continue
        if any(parte in IGNORAR for parte in caminho.parts):
            continue
        if caminho.suffix in {".py", ".sh", ".md", ".txt", ".yml", ".yaml", ".example"}:
            yield caminho


def test_sem_segredo_versionado():
    """Nenhuma chave de API pode estar em arquivo rastreado pelo git."""
    achados = []
    for caminho in arquivos_versionados():
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        for padrao, rotulo in PADROES_SEGREDO:
            if padrao.search(texto):
                achados.append(f"{caminho.relative_to(REPO_ROOT)}: {rotulo}")
    assert not achados, "segredo versionado:\n  " + "\n  ".join(achados)


# Só arquivos EXECUTÁVEIS entram na checagem de portabilidade.
#
# Markdown fica de fora de propósito. As `references/` são relatos de incidentes
# reais — "o backend subia de C:\\Users\\...\\PycharmProjects\\crewbotics-back, um
# clone antigo" — em que o path concreto É a informação; generalizar destruiria o
# valor diagnóstico. A promessa do README ("as skills são portáveis, paths usam
# env var + default relativo") é sobre o código, e é isso que este teste sustenta.
EXT_EXECUTAVEIS = {".py", ".sh"}


def test_sem_path_de_maquina_hardcoded():
    """Portabilidade: no código, paths vêm de env var + default relativo.

    Os testes são a exceção deliberada — precisam localizar o Git Bash do host.
    """
    achados = []
    for caminho in arquivos_versionados():
        rel = caminho.relative_to(REPO_ROOT)
        if rel.parts[0] == "tests" or caminho.suffix not in EXT_EXECUTAVEIS:
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        for padrao in PADROES_PATH:
            for m in padrao.finditer(texto):
                achados.append(f"{rel}: {m.group(0)!r}")
    assert not achados, "path de maquina hardcoded:\n  " + "\n  ".join(achados)


def test_env_nao_versionado():
    """`.env` guarda credencial e nunca pode ser rastreado — só `.env.example`."""
    r = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True,
                       cwd=str(REPO_ROOT), encoding="utf-8", errors="replace")
    assert not r.stdout.strip(), ".env esta versionado — remova com `git rm --cached .env`"
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


def test_env_example_nao_tem_valor_real():
    """`.env.example` é template: as variáveis de chave ficam vazias ou comentadas."""
    exemplo = REPO_ROOT / ".env.example"
    if not exemplo.exists():
        pytest.skip(".env.example ausente")
    suspeitas = []
    for n, linha in enumerate(exemplo.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        if "KEY" not in chave.upper() and "TOKEN" not in chave.upper():
            continue
        valor = valor.strip().strip('"').strip("'")
        # Placeholders óbvios são aceitáveis.
        if valor and not re.fullmatch(r"[<{].*[>}]|sua[-_].*|your[-_].*|xxx+|\.\.\.|change[-_]?me",
                                      valor, re.I):
            suspeitas.append(f"linha {n}: {chave.strip()}={valor[:12]}...")
    assert not suspeitas, ".env.example com valor real:\n  " + "\n  ".join(suspeitas)
