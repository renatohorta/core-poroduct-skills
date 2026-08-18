# ECS/ALB health check → DisallowedHost (target_type "ip")

## Sintoma
Log de produção (ECS Fargate + ALB com `target_type = "ip"`):
```
django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '10.0.10.81:8000'
```
O health check do ALB bate no container usando o **IP privado** como Host header
(`10.0.10.100:8000`, `10.0.1.223:8000`, `172.16.x.x`, `192.168.x.x`). Esse IP não
está em `DJANGO_ALLOWED_HOSTS` (que só tem o domínio público), então o Django
rejeita com 400 e o serviço cai.

## Causa raiz
O ALB com `target_type = "ip"` envia o IP privado do target como `Host` no health
check. O `CommonMiddleware` do Django valida o Host contra `ALLOWED_HOSTS` e rejeita
IPs privados que não estejam listados.

## Correção — AllowPrivateIpHostMiddleware
Middleware que adiciona IPs privados RFC 1918 ao `ALLOWED_HOSTS` em runtime,
registrado **ANTES** do `CommonMiddleware` (que valida o Host):

```python
# config/middleware.py
import ipaddress

class AllowPrivateIpHostMiddleware:
    """Permite health checks do ALB/ECS que enviam IP privado como Host."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if self._is_private_ip(host):
            request.META["HTTP_HOST"] = host  # já aceito; ALLOWED_HOSTS ampliado abaixo
        return self.get_response(request)

    @staticmethod
    def _is_private_ip(host):
        hostname = host.split(":")[0]
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            return False
        return ip.is_private
```

Registro em `settings.py` — o middleware DEVE vir antes do `CommonMiddleware`:
```python
MIDDLEWARE = [
    "config.middleware.AllowPrivateIpHostMiddleware",  # antes do CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    ...
]
```

`_is_private_ip` cobre 10/8, 172.16/12, 192.168/16 (RFC 1918) via `ip.is_private`.
`example.com` → False; `10.0.10.100:8000` → True.

## Pitfall de diagnóstico — o fix pode JÁ estar na main
Antes de escrever código, verifique se o middleware já existe na main e compare a
**data do log de produção** com a **data do commit do fix**. Neste caso o log era de
29/07 e o fix foi adicionado em 08/08 — o erro já estava corrigido no código; só
faltava o **deploy**. Não reescreva um fix que já existe.

## Verificação
- `_is_private_ip` com os IPs exatos do log → True.
- Health endpoint sem auth (liveness probe): `def health(_request)` em `api_urls.py`.
- `terraform/alb.tf`: `health_check.path = "/api/v1/health/"`, `target_type = "ip"`.
- O domínio público ainda precisa estar no secret `DJANGO_ALLOWED_HOSTS` (o middleware
  só cobre os IPs privados do health check, não o tráfego público).
