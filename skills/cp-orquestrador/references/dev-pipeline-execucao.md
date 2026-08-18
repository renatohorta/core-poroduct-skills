# Execução do pipeline de desenvolvimento (crewbotics-back) — pitfalls reais

Lições duráveis de execuções reais do pipeline (INI-80, 11/08/2026). Complementa
`roadmap-inbox-manutencao.md` (estado real vs roadmap) e
`windows-wsl-bash-relay-workaround.md` (relay bash).

## Rodar testes: use `uv run pytest`, NÃO `.venv`

O projeto usa `uv` e **NÃO tem `.venv` próprio** no repo. `uv run` cria o venv sob
demanda (e sincroniza deps, atualizando `uv.lock`). Não procure `python.exe` em
`.venv/` — não existe. Padrão:

```python
import os, subprocess
base = r"C:\Users\renat\Documents\Professional\Crewbotics\crewbotics-back"
env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
r = subprocess.run(["uv", "run", "pytest", "tests/chat/test_x.py", "-q", "-p", "no:cacheprovider"],
                   capture_output=True, text=True, env=env, cwd=base, timeout=600)
print(r.returncode, r.stdout[-3000:], r.stderr[-2000:])
```

- `uv run` pode demorar na 1ª vez (instala deps) — use timeout generoso (600s).
- `uv run` atualiza `uv.lock` se deps estavam desatualizadas. Isso é legítimo de
  commitar (ex.: `resvg-py` já era importado mas faltava no lock). Verifique o diff
  antes de incluir.

## Testes que tocam banco falham sem `.env`/Postgres

Testes que importam models Django (ex.: `test_instagram_carousel_skill.py`) falham
com `OperationalError: password authentication failed for user "postgres"` quando
não há `.env`/banco acessível. Isso é **pré-existente e não relacionado à sua
mudança** — não tente "corrigir" o código. Testes que NÃO tocam banco (ex.: um
executor PIL puro) passam. Ao reportar, distinga claramente: "meus testes passam;
os de X falham por conexão com Postgres (pré-existente)".

## Commit: SEMPRE verificar `git status --short` antes de commitar

Pitfall real: stagei só alguns arquivos, commitei, e 3 arquivos modificados
(`canvas_design_crew.py`, `presentation_skill.py`, `tasks.md`) ficaram de fora do
commit — o `git commit` só pega o que está staged. O commit "passou" mas o trabalho
ficou órfão.

Padrão seguro:
1. `git add <arquivos>` (liste TODOS os arquivos da mudança explicitamente).
2. `git status --short` → confirme que TODOS os arquivos pretendidos estão staged
   (coluna `A`/`M` na 1ª posição).
3. Só então `git commit`.
4. Após o commit, `git status --short` de novo → deve estar limpo (ou só o que
   ficou de fora de propósito).

Se um commit saiu incompleto, faça um commit de follow-up com os arquivos restantes
— não reescreva o histórico.

## PIL + `tempfile.TemporaryDirectory` no Windows: feche a imagem

Teste que abre PNG com `Image.open(p)` e depois usa `TemporaryDirectory` falha no
Windows com `PermissionError: [WinError 32] ... being used by another process` —
o `Image.open` segura o file handle e impede o `rmtree` do tempdir.

Correção: usar context manager `with Image.open(p) as im:` (fecha o handle ao sair
do bloco). Sempre feche imagens PIL antes de deletar o diretório que as contém.

## `false` vs `False` em dict de parameters (Python)

Ao escrever um dict de JSON Schema em Python (ex.: `parameters` de uma skill), use
`True`/`False` (Python), NÃO `true`/`false` (JSON/JS). `"default": false` levanta
`NameError: name 'false' is not defined` no import do módulo. O `ast.parse` pega a
sintaxe mas NÃO pega esse erro de runtime — rode o teste/import para confirmar.
