# ddgs (DuckDuckGo Search) — API Quirks & Pitfalls

## Version

`ddgs==9.14.4` (installed via pip in project venv).

## Import: avoid the lazy proxy

```python
# BROKEN — triggers lxml.etree import from the WRONG venv:
from ddgs import DDGS

# WORKS — bypasses the lazy proxy metaclass:
from ddgs.ddgs import DDGS
```

The `ddgs` package uses a `_ProxyMeta` metaclass that lazy-loads the real `DDGS` class
from `ddgs.ddgs` on first access. This proxy triggers `from lxml import html` inside
`ddgs/base.py`, which in turn does `from .. import etree`. If the Hermes venv's `lxml`
(which lacks `etree`) is on `sys.path` before the project venv's `lxml`, the import
fails with `ImportError: cannot import name 'etree'`.

**Fix:** import directly from `ddgs.ddgs` to bypass the proxy entirely.

## `images()` method signature

```python
# BROKEN — ddgs 9.x ignores `keywords=` keyword:
ddgs.images(keywords=query, max_results=5)

# WORKS — query is the FIRST positional argument:
ddgs.images(query, max_results=5)
```

The `_search_sync` method accepts `query` as the second positional parameter and
`keywords` as an optional deprecated alias. However, when called via the proxy
metaclass, the `keywords=` keyword is silently ignored, resulting in:
`DDGS.images() missing 1 required positional argument: 'query'`

**Fix:** pass `query` as the first positional argument.

## Other methods (same pattern)

```python
ddgs.text(query, max_results=10)
ddgs.news(query, max_results=5)
ddgs.videos(query, max_results=3)
```

All search methods follow the same positional-query pattern.

## DNS failure: `record type OPT only allowed in additional section`

**Sintoma:** todos os engines do ddgs falham intermitentemente com:

```
Error in engine google: DDGSException("ConnectError: ... dns error > protocol error: decoding error: record type OPT only allowed in additional section")
```

**Causa raiz:** o ddgs usa o `primp` (HTTP client Rust) que por padrão usa o resolver
DNS **hickory** embutido. Esse resolver falha intermitentemente decodificando respostas
EDNS0 (OPT). Como TODOS os engines usam o mesmo client primp, uma única falha de DNS
derruba a busca inteira. É intermitente (~50% de falha no Windows).

**Diagnóstico:** rodar `ddgs.text()` várias vezes — às vezes OK, às vezes `record type OPT`.

**Correção:** forçar `dns_resolver="system"` no client primp. Como `primp.Client` é uma
extensão Rust (não sub-classable e `__init__` não substituível), patchear o
`BaseSearchEngine.__init__` do ddgs para construir o client com `dns_resolver="system"`:

```python
import primp
import ddgs.http_client as _hc
from ddgs.base import BaseSearchEngine
from ddgs.exceptions import DDGSException, TimeoutException

class _SystemDNSHttpClient:
    def __init__(self, proxy=None, timeout=10, *, verify=True):
        self.client = primp.Client(
            dns_resolver="system", proxy=proxy, timeout=timeout,
            impersonate="random", impersonate_os="random",
            verify=verify if isinstance(verify, bool) else True,
            ca_cert_file=verify if isinstance(verify, str) else None,
        )
    def headers_update(self, *a, **k):
        return self.client.headers_update(*a, **k)
    def request(self, *args, **kwargs):
        try:
            return _hc.Response(self.client.request(*args, **kwargs))
        except primp.TimeoutError as ex:
            raise TimeoutException(ex) from ex
        except Exception as ex:
            raise DDGSException(f"{type(ex).__name__}: {ex!r}") from ex
    def get(self, url, *a, **k): return self.request("GET", url, *a, **k)
    def post(self, url, *a, **k): return self.request("POST", url, *a, **k)

_orig_init = BaseSearchEngine.__init__
def _patched_init(self, proxy=None, timeout=None, *, verify=True):
    self.http_client = _SystemDNSHttpClient(proxy=proxy, timeout=timeout, verify=verify)
    try:
        self.http_client.headers_update(self.headers_update)
    except Exception:
        pass
    self.results = []
BaseSearchEngine.__init__ = _patched_init
```

Validado: 6/6 OK estável (antes ~50% falha). Referência da correção no projeto:
`chat/web_search.py` → `_patch_ddgs_system_dns()`.
