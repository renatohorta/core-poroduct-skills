# CrewAI LLM injection + Daphne env pitfalls (Crewbotics)

Pitfalls descobertos ao implementar skills CrewAI e reiniciar o backend no
Crewbotics. Todos validados em sessão real.

## 1. `Agent()` do CrewAI sem `llm=` cai no OpenAI default

Criar `Agent(...)` sem `llm=` faz o CrewAI usar o default OpenAI e tentar
`OPENAI_API_KEY` — mesmo com o projeto configurado em Gemini. Sintoma no log:
`OPENAI_API_KEY is required` / `OpenAI API call failed`.

**Correção:** construir o LLM da config global (provider-agnostic) e injetar em
TODOS os agents:

```python
from crewai import LLM
from crews.crew_runner_async import build_llm_kwargs
from django.conf import settings

llm_kwargs = build_llm_kwargs(
    getattr(settings, "LLM_MODEL", "gemini/gemini-2.5-flash") or "gemini/gemini-2.5-flash",
    float(getattr(settings, "LLM_TEMPERATURE", 0.7)),
)
crew_llm = LLM(**llm_kwargs)
agent = Agent(..., llm=crew_llm)
```

`build_llm_kwargs` já monta `model/temperature/timeout/api_key/provider/is_litellm`
corretamente para o provider ativo. NUNCA deixe `Agent()` sem `llm=`.

## 2. Daphne relançado via subprocess precisa do env Windows completo

Quando o backend é reiniciado via `subprocess.Popen` (não pelo terminal do
usuário), um env mínimo pode faltar variáveis do Windows que o `import crewai`
exige. O crewai 1.15.5 puxa `chromadb` (chama `Path.home()`) e `crewai_core`
(chama `Path(LOCALAPPDATA)`). Sem `USERPROFILE`/`HOME`/`LOCALAPPDATA`, o import
quebra e `_crewai_available()` retorna `False` → a crew cai em modo **stub**
(`[STUB — crewai ausente]`) MESMO com o Gemini configurado e acessível.

**Sintoma confuso:** o log mostra `LiteLLM completion() model= gemini-2.5-flash`
(do Copilot/chat) mas a crew roda em stub. O Gemini está OK; o problema é o import.

**Correção:** ao relançar o Daphne via subprocess, inclua o env completo:
```python
env = {
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "PYTHONPATH": os.path.join(back, ".venv", "Lib", "site-packages"),
    "PATH": os.path.join(back, ".venv", "Scripts") + os.pathsep + os.environ.get("PATH", ""),
    "VIRTUAL_ENV": os.path.join(back, ".venv"),
    "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
    "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    "USERPROFILE": os.environ.get("USERPROFILE", r"C:\Users\renat"),
    "HOMEDRIVE": os.environ.get("HOMEDRIVE", "C:"),
    "HOMEPATH": os.environ.get("HOMEPATH", r"\Users\renat"),
    "HOME": os.environ.get("HOME", r"C:\Users\renat"),
    "TEMP": os.environ.get("TEMP", r"C:\Users\renat\AppData\Local\Temp"),
    "TMP": os.environ.get("TMP", r"C:\Users\renat\AppData\Local\Temp"),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", r"C:\Users\renat\AppData\Local"),
    "APPDATA": os.environ.get("APPDATA", r"C:\Users\renat\AppData\Roaming"),
}
```
**Verificar antes de subir:** `python -c "import crewai; print(crewai.__version__)"`
com esse env — se importar, o Daphne vai rodar a crew de verdade.

## 3. `from django.conf import settings` dentro de função → UnboundLocalError

Se o módulo tem `from django.conf import settings` no topo E também um
`from django.conf import settings` DENTRO de uma função (ex.: num bloco `if`),
o Python trata `settings` como variável LOCAL na função inteira — qualquer uso
de `settings` antes desse import local lança `UnboundLocalError: cannot access
local variable 'settings'`. Correção: renomear o import local
(`from django.conf import settings as dj_settings`) ou usar só o do topo.

## 4. `title__in`/`name__in` do Postgres é case-sensitive

Ao filtrar por `exclude`/`targets` com `__in`, NÃO lowercase os valores antes da
query — o Postgres compara exatamente. Se você fizer `str(x).strip().lower()`
para normalizar e depois usar `title__in=[...]`, o match falha silenciosamente e
o item "mantido" acaba sendo excluído. Mantenha os valores originais para a query
(use lowercase só para comparação manual, não para o filtro do ORM).

## 5. Modelo Gemini SEM o prefixo `gemini/` é roteado para `vertex_ai` (ADC) em produção

**Sintoma no log de produção (ECS):** chamadas ao LLM com `gemini-2.5-flash` (sem
o prefixo `gemini/`) produzem:
```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FALHA
google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found
...
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← FUNCIONA
```
O chat ainda responde (o fallback `gemini/gemini-2.5-flash` funciona), mas com
~15s de atraso por chamada — o LiteLLM tenta `vertex_ai` primeiro, falha por falta
de ADC, e só então cai no fallback. No ECS não há Application Default Credentials
(service account), então `vertex_ai` nunca funciona.

**Causa raiz:** um modelo **sem barra** (`gemini-2.5-flash`) é roteado pelo LiteLLM
para o provider `vertex_ai` (que exige ADC), em vez de `gemini` (que usa API key via
`GEMINI_API_KEY`). O default do código é `gemini/gemini-2.5-flash` (com prefixo) —
correto; o bug é o **secret `LLM_MODEL`** que veio sem prefixo.

**Correção em 2 camadas:**
1. **Secret em produção (AWS):** corrigir `LLM_MODEL` para `gemini/gemini-2.5-flash`
   (mesmo padrão do bug anterior `gemini-3-flash` inexistente).
2. **Hardening no código** (`chat/llm_client.py`) para que um secret sem prefixo
   não quebre em nenhum ambiente:
```python
def _normalize_model(model: str) -> str:
    """Garante o formato LiteLLM `provider/model`. Modelo sem barra (ex.:
    gemini-2.5-flash) é roteado pelo LiteLLM para vertex_ai (exige ADC) em vez
    de gemini (API key). Prepend gemini/ a modelos sem prefixo."""
    if "/" in model:
        return model
    return f"gemini/{model}"

def get_model() -> str:
    raw = getattr(settings, "LLM_MODEL", "") or "gemini/gemini-2.5-flash"
    return _normalize_model(raw)
```
   Aplicar `_normalize_model()` em `get_model()`, `_base_kwargs()` (ponto central
   onde o modelo chega ao LiteLLM) e no modelo de embedding (`embed()`) também. O
   caminho das crews já é seguro (`_resolve_litellm_model` usa `get_model()`).

**Como diagnosticar rapidamente:** no log, comparar as linhas `LiteLLM completion()
model= ...; provider = ...`. Se `provider = vertex_ai` aparece antes do fallback
`provider = gemini`, é este o bug — não é problema de chave, é de prefixo/provider.
