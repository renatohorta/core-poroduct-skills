# Diagnóstico: código certo localmente mas não funciona no app

Pitfall real (11/08/2026, carrossel de cards no crewbotics). Implementei a detecção
automática de cards (`parse_card_list`) na skill `instagram_carousel`, validei com
testes passando e o prompt real — mas o app na porta 8080 continuou gerando o
carrossel ANTIGO (sem detecção). Debugar a skill foi inútil: o problema nunca foi
o código.

## Causa raiz: o backend roda de OUTRO clone do repo

O servidor na porta 8000 não estava rodando do diretório onde eu trabalhava. Havia
DOIS clones do `crewbotics-back`:
- `C:\Users\renat\Documents\Professional\Crewbotics\crewbotics-back` — onde o
  trabalho de dev (branchs, features) realmente acontece.
- `C:\Users\renat\PycharmProjects\crewbotics-back` — clone antigo, que o
  `scripts/all_dev.ps1` usava como `$backDir`.

O backend na :8000 subia do PycharmProjects (código sem a feature), por isso o
comportamento antigo persistia mesmo com o código novo pronto no outro clone.

## Regra

**Antes de debugar uma skill que "não pega" no app, confirme de QUAL diretório o
processo na porta está rodando.** Verificar o PID + CommandLine do listener, não
assumir que é o repo atual de trabalho.

## Como verificar (Windows, via execute_code)

O `netstat` via git-bash/MSYS às vezes retorna vazio (instável); use PowerShell.

```python
import subprocess, os
PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
ps = '''
$ErrorActionPreference='SilentlyContinue'
foreach ($port in 8000,8080) {
  $c = Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -First 1
  if ($c) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"
    $pp = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
    Write-Output ("PORT {0} PID={1} START={2}" -f $port, $c.OwningProcess, $proc.CreationDate)
    Write-Output ("  CMD=" + $proc.CommandLine)
    Write-Output ("  PARENT=" + $pp.CommandLine)
  } else { Write-Output "no listener on $port" }
}
'''
r = subprocess.run([PS,"-NoProfile","-Command",ps], capture_output=True, text=True, timeout=60)
print(r.stdout)
```

O `CommandLine` do python revela o diretório (ex.: `...\PycharmProjects\crewbotics-back\.venv\Scripts\python.exe -m daphne ...`). Compare com o repo onde o código certo está.

Confirme também se o arquivo da skill no diretório do processo tem o código novo:
```python
import os
for p in [r"...\cloneA\chat\skills\instagram_carousel_skill.py",
          r"...\cloneB\chat\skills\instagram_carousel_skill.py"]:
    src = open(p, encoding="utf-8", errors="replace").read()
    print(os.path.basename(os.path.dirname(os.path.dirname(p))), "parse_card_list" in src)
```

## Correção

1. Ajuste o `all_dev.ps1` para `$backDir` apontar para o clone de trabalho correto
   (mantendo `$frontDir` no clone canônico do front — pode ser outro diretório).
2. O script já mata processos nas portas 8000/8080 no início — rodar de novo derruba
   o processo antigo automaticamente.

## Nota: feature em branch não-mergeada não existe na main

Se a mudança está numa branch `feature/...` que ainda não foi mergeada na main, um
backend rodando da main não a terá. Verifique `git branch --contains <commit>` para
confirmar onde o commit existe antes de assumir que o código deveria estar ativo.
`main local` vs `origin/main` podem divergir — `git rev-parse main origin/main`.
