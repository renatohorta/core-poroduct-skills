# Crew roda em STUB ("crewai ausente") mesmo com Gemini configurado — Windows

## Sintoma
- O card de execução da crew mostra `[STUB — crewai ausente]` como output de cada task.
- O log do Daphne mostra `crew.kickoff stub (crewai ausente) crew=<nome>`.
- MAS o Gemini ESTÁ configurado: `is_configured()` retorna `True`, `GEMINI_API_KEY` presente no `.env`, e o log mostra chamadas `LiteLLM completion() model= gemini-2.5-flash; provider = gemini` (essas são de OUTRAS partes — Copilot/chat — não da crew).

## Causa raiz
O `run_pipeline_async` decide o stub por:
```python
if not _crewai_available() or not llm_configured:
    reason = "crewai ausente" if not _crewai_available() else "LLM não configurado"
```
`_crewai_available()` faz `import crewai` num try/except. Se o import falhar, retorna `False` → stub. **A chave do Gemini é irrelevante aqui** — o problema é o import do crewai.

O `import crewai` (1.15.5) puxa `chromadb` (que chama `Path.home()`) e `crewai_core` (telemetria, que chama `Path(LOCALAPPDATA)`). No Windows, se o processo não tiver as variáveis de home no ambiente, o import quebra:

```
RuntimeError: Could not determine home directory.   # chromadb → Path.home()
TypeError: argument should be a str or an os.PathLike object ... not 'NoneType'  # crewai_core → Path(LOCALAPPDATA)
```

## Quando acontece
Quando o Daphne é relançado via `subprocess.Popen` com um `env` construído à mão (ex.: só `DJANGO_SETTINGS_MODULE`, `PYTHONPATH`, `SystemRoot`, `WINDIR`) — sem `USERPROFILE`/`HOME`/`LOCALAPPDATA`/`APPDATA`/`TEMP`. O sandbox do Hermes não injeta essas vars no subprocesso.

## Correção
Relançar o Daphne com o ambiente Windows completo:
```python
env = {
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "PYTHONPATH": os.path.join(back, ".venv", "Lib", "site-packages"),
    "PATH": os.path.join(back, ".venv", "Scripts") + os.pathsep + os.environ.get("PATH", ""),
    "VIRTUAL_ENV": os.path.join(back, ".venv"),
    "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
    "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    "USERPROFILE": os.environ.get("USERPROFILE", r"C:\Users\<user>"),
    "HOMEDRIVE": os.environ.get("HOMEDRIVE", "C:"),
    "HOMEPATH": os.environ.get("HOMEPATH", r"\Users\<user>"),
    "HOME": os.environ.get("HOME", r"C:\Users\<user>"),
    "TEMP": os.environ.get("TEMP", r"C:\Users\<user>\AppData\Local\Temp"),
    "TMP": os.environ.get("TMP", r"C:\Users\<user>\AppData\Local\Temp"),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", r"C:\Users\<user>\AppData\Local"),
    "APPDATA": os.environ.get("APPDATA", r"C:\Users\<user>\AppData\Roaming"),
}
```

## Verificação
Antes de relançar, testar o import com o MESMO env que será usado:
```bash
python -c "import crewai; print('crewai OK', crewai.__version__)"
```
Se imprimir `crewai OK 1.15.5`, o env está correto. Se der `RuntimeError: Could not determine home directory` ou `TypeError ... not 'NoneType'`, falta `USERPROFILE`/`LOCALAPPDATA`.

## Nota
Isso é um problema do processo de reinício via subprocess com env incompleto — NÃO do código do projeto. Quando o backend é iniciado pelo shell normal do usuário, essas vars existem e o crewai importa sem erro. Não é um bug de produção.
