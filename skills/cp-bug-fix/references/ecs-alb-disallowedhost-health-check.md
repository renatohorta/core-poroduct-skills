# ECS/ALB health check → DisallowedHost (target_type "ip")

## Symptom
Production log (ECS Fargate + ALB with `target_type = "ip"`):
```
django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '10.0.10.81:8000'
```
The ALB health check hits the container using the **private IP** as the Host header
(`10.0.10.100:8000`, `10.0.1.223:8000`, `172.16.x.x`, `192.168.x.x`). This IP is not
in `DJANGO_ALLOWED_HOSTS` (which only has the public domain), so Django
rejects it with 400 and the service goes down.

## Root cause
The ALB with `target_type = "ip"` sends the target's private IP as the `Host` in the health
check. Django's `CommonMiddleware` validates the Host against `ALLOWED_HOSTS` and rejects
private IPs that are not listed.

## Fix — AllowPrivateIpHostMiddleware
Middleware that adds RFC 1918 private IPs to `ALLOWED_HOSTS` at runtime,
registered **BEFORE** the `CommonMiddleware` (which validates the Host):

```python
# config/middleware.py
import ipaddress

class AllowPrivateIpHostMiddleware:
    """Allows ALB/ECS health checks that send a private IP as the Host."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if self._is_private_ip(host):
            request.META["HTTP_HOST"] = host  # already accepted; ALLOWED_HOSTS expanded below
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

Registration in `settings.py` — the middleware MUST come before the `CommonMiddleware`:
```python
MIDDLEWARE = [
    "config.middleware.AllowPrivateIpHostMiddleware",  # before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    ...
]
```

`_is_private_ip` covers 10/8, 172.16/12, 192.168/16 (RFC 1918) via `ip.is_private`.
`example.com` → False; `10.0.10.100:8000` → True.

## Diagnosis pitfall — the fix may ALREADY be on main
Before writing code, check whether the middleware already exists on main and compare the
**production log date** with the **fix commit date**. In this case the log was from
29/07 and the fix was added on 08/08 — the error was already fixed in the code; only the
**deploy** was missing. Do not rewrite a fix that already exists.

## Verification
- `_is_private_ip` with the exact IPs from the log → True.
- Health endpoint without auth (liveness probe): `def health(_request)` in `api_urls.py`.
- `terraform/alb.tf`: `health_check.path = "/api/v1/health/"`, `target_type = "ip"`.
- The public domain still needs to be in the `DJANGO_ALLOWED_HOSTS` secret (the middleware
  only covers the health check's private IPs, not the public traffic).
