# Debugging: code on disk vs running process + DRF/serializer pitfalls

Pitfalls emergidas ao corrigir bug de export PNG do carrossel (Playwright→resvg-py)
e ao adicionar campo novo no serializer de mensagens (branch picker + parts).

## 1. Traceback de lib que o código NO DISCO já não usa = processo antigo em memória

Sintoma: o traceback aponta para uma biblioteca/módulo que o código atual não importa
(ex.: erro de Playwright em `playwright/_impl/_connection.py`, mas `png_export.py`
já usa `resvg-py` e não referencia Playwright). A causa é um **processo Daphne/servidor
rodando com módulos antigos carregados** — o fix foi mergeado mas o servidor NÃO foi
reiniciado.

NÃO refaça o fix no código (ele está correto). Diagnóstico em 3 passos:

1. **Varra imports reais** da lib no fluxo atual, ignorando comentários/docs:
   ```python
   real = [l for l in txt.splitlines() if re.search(r"from playwright|import playwright|sync_playwright|async with async_playwright", l)]
   ```
   Se só aparecer em comentários → código OK.
2. **Teste o artefato ponta a ponta via shell** com o state real do banco
   (ex.: `export_carousel_pngs(pres.state, outdir, len(slides))` gerou os 7 PNGs).
   Se funcionar → código correto.
3. **A causa é o processo desatualizado** → reiniciar o servidor (matar PID na porta
   e relançar Daphne). O bug se resolve reiniciando, não editando.

Registrar na inbox como `[Corrigido]` mas mover para `processed` — a "correção" é a
constatação de que o código já estava certo + a instrução de reiniciar.

## 2. DRF `@action` — `url_path` vs nome do método

O DRF deriva a URL do **nome do método** (preserva underscore). Método `branch_version`
gera `.../branch_version/` (underscore), mas o frontend/curl pode chamar
`.../branch-version/` (hífen) → **404**. Correção: forçar `url_path` no decorator:

```python
@action(detail=True, methods=["get"], url_path="branch-version")
def branch_version(self, request, uuid=None): ...
```

Ao criar um `@action`, SEMPRE confira qual URL o consumidor vai usar e force o
`url_path` para bater. Ver rotas com: `for url in router.urls: print(url.pattern)`.

## 3. Adicionar campo ao serializer quebra teste de contrato de key-set

Ao adicionar um campo (ex.: `parts`) a um `ModelSerializer`, testes que assertam o
conjunto exato de chaves quebram:

```python
assertEqual(set(body["messages"][0].keys()), {"id","uuid","role","content",...})
# → AssertionError: Items in the first set but not the second: 'parts'
```

Isso é esperado — atualize o set no teste de contrato para incluir o campo novo.

## 4. Campo novo (FK self / index) exige migration + --create-db

Ao modelar um campo novo (ex.: `parent` FK self + `branch_index` em `ChatMessage`):
- `makemigrations <app>` gera a migration; `migrate <app>` aplica no dev DB
  (o pytest cria schema do zero, mas o dev acumula colunas órfãs de outros branches →
  `DROP COLUMN IF EXISTS` antes se preciso).
- Nos testes usar `--create-db` (nunca `--reuse-db` com schema velho → IntegrityError
  ou campo inexistente).
