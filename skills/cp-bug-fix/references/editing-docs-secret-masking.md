# Editar docs .md — valores com cara de segredo são mascarados para `***`

## Sintoma

Ao escrever em arquivos `.md` exemplos/JSON com strings que parecem segredo
(ex: `{ "token": "TOKEN", "password": "SENHA" }`, `Authorization: Bearer ...`), a
ferramenta de escrita/edição pode mascarar esses valores para `***` (content-safety
filter). O `git diff` e a leitura mostram `***` em vez do valor que você escreveu.

Isso acontece **na escrita** (grava `***` no arquivo) e **na exibição** (mostra `***`
mesmo quando o arquivo está correto). Essa dupla camada confunde o diagnóstico — você
"vê" `***` e assume que a escrita falhou, mas o arquivo pode estar certo.

## Diagnóstico — ler bytes crus

Use bytes, não texto, para distinguir masking de conteúdo real:

```python
raw = open(p, "rb").read()
print(b'NOVA_SENHA' in raw)   # True = conteúdo correto no arquivo
print(b'***' in raw)          # False = sem masking gravado
```

Se os **bytes** contêm o valor esperado, o `***` é só mascaramento de exibição —
NÃO reescreva o arquivo (gasta iterações à toa). Se os bytes têm `***`, a escrita
realmente mascarou e é preciso corrigir.

## Correção — usar placeholders que não pareçam segredo

Substitua por placeholders neutros que não disparem o filtro:

```python
# em vez de: { "token": "xxx", "password": "yyy" }
# usar:      { "token": "TOKEN_DO_EMAIL", "password": "NOVA_SENHA" }
```

Para substituir uma linha exata que já ficou mascarada, use regex em bytes:

```python
import re
pat = re.compile(rb'\*\*Corpo:\*\* `\{[^\r\n]*"password"[^\r\n]*`')
m = pat.search(raw)
if m:
    raw = raw[:m.start()] + b'**Corpo:** `{ "token": "TOKEN_DO_EMAIL", "password": "NOVA_SENHA" }`' + raw[m.end():]
    open(p, "wb").write(raw)
```

## Nota

O replace por substring simples (`raw.replace(old, new)`) pode "não encontrar" o old
se houver alguma diferença invisível de bytes (CRLF, espaços). Prefira regex em bytes
sobre a linha inteira quando o replace exato falhar.
