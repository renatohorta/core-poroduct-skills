# Windows: WSL bash relay falha intermitentemente — use execute_code

## Sintoma
Neste host Windows, as ferramentas `terminal` e `write_file`/`patch` às vezes
falham com:
```
<3>WSL (NN - Relay) ERROR: CreateProcessCommon:735: execvpe(/bin/bash) failed: No such file or directory
```
Isso é o relay do Hermes tentando subir `/bin/bash` via WSL e não achando o
binário — NÃO é um erro do seu comando nem do projeto. É intermitente: o mesmo
comando pode funcionar numa chamada e falhar na seguinte.

## Workaround confiável
Use `execute_code` com Python puro (subprocess / open) — não passa pelo relay bash:

- **Rodar git / pytest / comandos:**
  ```python
  import os, subprocess
  env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
  back = r"C:\Users\renat\PycharmProjects\crewbotics-back"
  py = os.path.join(back, ".venv", "Scripts", "python.exe")
  r = subprocess.run([py, "-m", "pytest", "tests/chat/test_agui.py", "-q"],
                     capture_output=True, text=True, env=env, cwd=back, timeout=600)
  print(r.returncode, r.stdout[-3000:], r.stderr[-3000:])
  ```
  Para git, defina um helper `def git(*args): subprocess.run(["git"]+list(args), ...)`.

- **Escrever/ler arquivo:** use `open(p, "w", encoding="utf-8")` / `open(p, encoding="utf-8").read()`
  em vez de `write_file`/`read_file` quando o relay estiver falhando.

## Pitfall de leitura
`read_file` pode retornar "File unchanged since last read" (dedup) mesmo quando
você nunca leu o arquivo nesta sessão — se precisar do conteúdo real, leia via
`open(p, encoding="utf-8").read()` no `execute_code`.

## Nota
Não trate isso como "terminal não funciona" permanente — é um relay intermitente.
Tente `terminal` primeiro; se falhar com o erro WSL, caia no `execute_code`.

## Pitfall: `git push` pendura no Git Credential Manager (headless)

Neste host Windows, `git push` pode **pendurar indefinidamente** (timeout de 300s no
`execute_code`) porque o credential helper é `manager` (Git Credential Manager), que
tenta abrir um diálogo de autenticação que não completa em ambiente headless. Sintomas:
- `git push` nunca retorna; o `execute_code` estoura o timeout de 300s mesmo com
  `subprocess.run(..., timeout=45)` — o wrapper fica preso.
- Vários processos `git.exe` / `git-credential-manager.exe` acumulam no `tasklist`.

Diagnóstico e workaround:

1. **Confirmar que é o GCM:** rodar com o helper desativado para ver o erro real rápido:
   ```python
   env["GIT_TERMINAL_PROMPT"] = "0"
   subprocess.run(["git", "-c", "credential.helper=", "push", "origin", "main"], ...)
   ```
   Se falhar imediatamente com `Authentication failed` / `Repository not found`, é o GCM
   que não está fornecendo credencial — não é problema de rede nem de branch.
2. **Rodar o push com kill forçado** (não deixa o wrapper travar):
   ```python
   p = subprocess.Popen(["git", "push", "origin", "main"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=env, cwd=back, start_new_session=True, text=True)
   try:
       out, err = p.communicate(timeout=45)
   except subprocess.TimeoutExpired:
       os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # mata o grupo inteiro
       out, err = p.communicate()
   ```
   `start_new_session=True` + `os.killpg` é o que destrava — sem isso o `communicate`
   fica preso e o `execute_code` estoura o timeout de 300s.
3. **Limpar processos acumulados:** `taskkill /F /IM git.exe`, `git-remote-https.exe`,
   `git-credential-manager.exe` (via `subprocess.run(["taskkill","/F","/IM",img])`).
4. **O travamento é transitório:** o mesmo push pode funcionar numa tentativa seguinte
   (o GCM às vezes completa). Se persistir, o caminho confiável é o usuário rodar
   `git push origin main` no terminal dele, onde o GCM abre o diálogo normalmente.

Não trate como "push não funciona" permanente — é o GCM headless. O padrão de retry com
kill forçado + `-c credential.helper=` para diagnóstico é a lição durável.
