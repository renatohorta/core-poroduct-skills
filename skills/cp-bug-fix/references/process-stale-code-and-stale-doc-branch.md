# Diagnóstico: traceback de lib que o código no disco não usa mais (processo com código antigo)

## Padrão
O usuário cola um traceback apontando para uma biblioteca (ex.: Playwright `_connection.py` /
`_make_subprocess_transport`), mas o código no disco **já foi migrado** para outra
(ex.: `resvg-py`). A causa NÃO é código errado — é o servidor (Daphne/runserver) rodando
com um módulo antigo carregado em memória desde antes do merge do fix.

**NÃO re-aplique um fix que já está na main.** Diagnostique a divergência disco↔processo
antes de editar qualquer coisa.

## Como confirmar (antes de tocar no código)
1. **Varra o fluxo por uso REAL da lib antiga** — não só comentários/docs:
   ```python
   import re
   for rel in [arquivos do caminho]:
       t = open(rel, encoding="utf-8").read()
       real = [l for l in t.splitlines()
               if re.search(r"from playwright|sync_playwright|async_playwright|\.chromium", l)]
       # se só aparece em docstring/comentário → código ok
   ```
2. **Rode a função de produção DIRETO** num shell com o state real do usuário
   (`manage.py shell -c "..."` ou script): se funcionar, o código está correto e só
   o processo precisa reiniciar. Ex.: `export_carousel_pngs(pres.state, outdir, len(slides))`
   gerou os 7 PNGs do state real — código confirmado bom.
3. **Verifique o processo**: `netstat -ano | findstr :8000`; distinga WSGI vs ASGI pelo
   header `Server:` da resposta. Reinicie o Daphne com o env Windows completo
   (USERPROFILE/HOME/LOCALAPPDATA/APPDATA/TEMP) para carregar o código novo.

## Sintoma-clássico
Usuário reporta bug num fluxo que VOCÊ já corrigiu e mergeou; o traceback aponta para
o código antigo. Diagnostique a divergência disco↔processo ANTES de re-fixar.

---

# Resolver branches de docs desatualizadas — extrair valor, NÃO mergear direto

## Padrão
Uma branch de docs (ex.: `docs/consolidar-documentacao`) foi criada há dias e a main
evoluiu. O merge direto pode **REMOVER conteúdo que a main ganhou depois** (ex.: a branch
deleta `knowledge_folder`, seções de ActivityLog/password-reset adicionadas depois).

## Verificações antes de mergear
- `git diff main <branch> -- <arquivo>` e conte adições vs remoções — remoção muito maior
  que adição em doc de referência = perda provável.
- Verifique se o arquivo que a branch deleta (ex.: `00-vision.md` 35KB com checklist/contrato)
  tem o conteúdo em OUTRO doc. Se não, NÃO deixe a branch apagá-lo.
- `git merge-base main <branch>` e compare a idade — merge-base antigo + muitos commits
  novos na main = alto risco de conflito/perda.

## Ação preferida
1. Extrair só o valor (ex.: fundir `01-visao-geral.md` + `01-visao-negocio.md` num
   `01-visao.md` manualmente, preservando `00-vision.md` completo).
2. Commitar na main.
3. `git branch -D` as branches (antes, `git ls-remote --heads origin` para confirmar se
   existem no remote — se não, só deleta local).
