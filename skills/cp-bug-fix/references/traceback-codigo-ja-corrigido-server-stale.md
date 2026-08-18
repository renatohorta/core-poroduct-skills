# Traceback de código já corrigido — processo servidor stale

## Quando aplicar
O usuário cola um traceback que referencia uma lib/abordagem que **você acha que já foi substituída**
(ex.: traceback de Playwright `NotImplementedError` em `_make_subprocess_transport` quando o código
já foi migrado para `resvg-py`). Antes de diagnosticar/corrigir qualquer coisa, confirme se o
traceback casa com o código ATUAL no disco.

## Fluxo de verificação (3 passos) — NUNCA pular
1. **Grep o disco** — confirme que o arquivo no working tree NÃO importa mais a lib antiga.
   Use regex que pega import real, não comentário/docstring:
   ```python
   real = [l for l in t.splitlines()
           if re.search(r"from playwright|import playwright|async_playwright|sync_playwright|p\.chromium", l)]
   ```
   Só comentários/docs = código já migrado.

2. **Teste o caminho real ponta a ponta** — rode a função no `manage.py shell` (ou subprocess
   com `.venv/Scripts/python.exe`) usando o state real persistido no banco:
   ```python
   from presentations.services.png_export import export_carousel_pngs
   pres = Presentation.objects.filter(uuid="...").first()
   pngs = export_carousel_pngs(pres.state, tempdir, len(slides))
   ```
   Se os artefatos (PNGs) são gerados sem a lib antiga, o código está correto.

3. **Se código OK + teste passa → processo servidor stale.** O Daphne/runserver que estava no ar
   foi iniciado ANTES do merge do fix e mantém o módulo antigo carregado em memória. O `netstat`
   pode nem mostrar a porta (já caiu). A correção é **reiniciar o servidor**, não editar código.
   Registrar o bug como `[Corrigido]` (o fix já está na main) e documentar que precisa de restart.

## Por que isso acontece
`git merge` atualiza o disco, mas NÃO recarrega módulos Python já importados num processo vivo.
O usuário testa contra o processo antigo → vê o erro pré-fix. O traceback do log é evidência do
código antigo, não do código atual.

## Regra de ouro
Não "corrija" um código que já está certo. Traceback + código no disco já migrado = servidor stale,
não bug novo. Verificar primeiro evita edições desnecessárias e commits de "fix" vazios.
