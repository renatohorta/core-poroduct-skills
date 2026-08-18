# Crew roda em STUB mesmo com Gemini configurado — causa: restart do backend via subprocess sem env do Windows

## Sintoma
- A crew é acionada, o card mostra "Erro na execução" ou o run completa DONE mas todos os outputs são `[STUB — crewai ausente] Task 'X' por ...`.
- O log do Daphne mostra `crew.kickoff stub (crewai ausente) crew=<nome>`.
- **Contradição:** o Gemini ESTÁ configurado (`is_configured()` retorna `True`, `GEMINI_API_KEY` presente no `.env`, e o log mostra `LiteLLM completion() model= gemini-2.5-flash; provider = gemini`). As chamadas LiteLLM que aparecem são de OUTRAS partes (Copilot/chat), não da crew.

## Causa raiz
O `run_pipeline_async` decide o stub por:
```python
if not _crewai_available() or not llm_configured:
    reason = "crewai ausente" if not _crewai_available() else "LLM não configurado"
```
`_crewai_available()` faz `import crewai` num try/except. Quando o backend é reiniciado via **subprocess** (ex.: `subprocess.Popen([py, "-m", "daphne", ...])`) com um `env` construído à mão, o `import crewai` (1.15.5) quebra silenciosamente porque o `chromadb` chama `Path.home()` e o `crewai_core` (telemetria) chama `Path(LOCALAPPDATA)`.

Erros reais do import (sem as env vars do Windows):
```
RuntimeError: Could not determine home directory.   # chromadb → Path.home()
TypeError: argument should be a str or an os.PathLike object ... not 'NoneType'  # crewai_core → Path(LOCALAPPDATA)
```

## Correção
Ao relançar o Daphne/ASGI via subprocess no Windows, o `env` DEVE incluir as variáveis de ambiente do Windows que o crewai/chromadb exigem:
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
Verificação rápida antes de subir:
```bash
python -c "import crewai; print(crewai.__version__)"   # com o MESMO env do Popen
```
Se imprimir a versão, o import funciona e a crew vai rodar de verdade.

## Nota importante
Isso NÃO é um bug do código do projeto. Quando o backend é iniciado pelo fluxo normal (terminal do Windows), essas variáveis existem e o crewai importa sem erro. O problema só aparece quando o agente reinicia o backend via subprocess com um `env` incompleto. Sempre herde o `os.environ` do processo e só sobrescreva o que for necessário (PYTHONPATH, DJANGO_SETTINGS_MODULE), em vez de construir um env mínimo do zero.

## Confirmação do fix
Após relançar com o env completo, acionar a crew numa conversa NOVA e checar:
- Run fica `RUNNING` (não stub, não ERROR) e completa `DONE` em ~1-2 min.
- Outputs têm conteúdo real (len > 5KB) e o quality gate retorna `PASS` — não `[STUB — crewai ausente]`.
