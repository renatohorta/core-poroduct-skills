---
name: cp-testes
description: "Testes de Software — cria uma crew CrewAI com Engenheiros de Teste Unitário, Integração, E2E, Performance e Analista de Resultados para validar qualidade do software. Use quando o usuário disser 'testar', 'criar testes', 'validar qualidade', 'fazer testes de performance', 'aumentar cobertura'."
---

# cp-testes — Testes de Software

Cria uma crew CrewAI com agentes especializados para executar o ciclo completo de testes de software:

1. **Engenheiro de Testes Unitários** — Cria testes unitários (pytest, Jest). Obcecado por cobertura e testes isolados.
2. **Engenheiro de Testes de Integração** — Testa integração entre componentes/APIs. Especialista em encontrar bugs que só aparecem quando componentes conversam.
3. **Engenheiro de Testes E2E** — Testa fluxos completos (Playwright, Cypress). Odeia sleeps, usa role-based selectors, testes determinísticos.
4. **Engenheiro de Testes de Performance** — Load testing, stress testing (k6, Locust). Encontra bottlenecks antes do usuário.
5. **Analista de Resultados** — Compila resultados, calcula cobertura, identifica regressões. Transforma dados de teste em decisões.

## Agentes

| Agente | Função |
|--------|--------|
| Engenheiro de Testes Unitários | Cria testes unitários isolados com alta cobertura |
| Engenheiro de Testes de Integração | Testa integração entre componentes/APIs |
| Engenheiro de Testes E2E | Testa fluxos completos de ponta a ponta |
| Engenheiro de Testes de Performance | Load testing, stress testing, benchmarks |
| Analista de Resultados | Compila resultados, calcula cobertura, emite veredito |

## Pipeline

```
1. Análise de código e planejamento de testes (Analista)
2. Criação de testes unitários (Eng. Unitários)
3. Criação de testes de integração (Eng. Integração)
4. Criação de testes E2E (Eng. E2E)
5. Testes de performance (Eng. Performance)
6. Compilação e relatório final (Analista) — emite PASS/FAIL
```

## Quality Gate

- **Cobertura mínima:** 80%
- **Falhas críticas:** 0
- **Performance:** p95 < 500ms para APIs, < 3s para páginas
- **Veredito:** PASS (tudo ok) ou FAIL (algo abaixo do mínimo)

## Entrada

- Código fonte (caminho do diretório ou arquivo)
- Critérios de aceitação (opcional)
- Modo de teste: unit, integration, e2e, performance, ou full

## Saída

Relatório de testes completo contendo:
- Resultados de cada categoria de teste
- Cobertura de código por módulo
- Métricas de performance (p50, p95, p99)
- Regressões identificadas
- Veredito final PASS/FAIL com justificativa

## Uso

```bash
# Modo completo (todos os tipos de teste)
python .hermes/skills/cp-testes/scripts/run.py "sistema de agendamento de consultas" --source ./src

# Modo específico
python .hermes/skills/cp-testes/scripts/run.py "API de agendamento" --source ./src --mode unit

# Com critérios de aceitação
python .hermes/skills/cp-testes/scripts/run.py "módulo de pagamentos" --source ./src --acceptance criterios.md

# Salvar relatório em arquivo
python .hermes/skills/cp-testes/scripts/run.py "app mobile" --source ./src --output relatorio.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-testes/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-testes/scripts/run.py \
  "sistema de agendamento de consultas médicas com autenticação, \
   CRUD de pacientes, agendamento com slots de horário, \
   e notificações por email" \
  --source ./src \
  --mode full \
  --output relatorio-testes.md
```

## Modos de Operação

### 🧪 Simulação (CrewAI — default)

Usa a crew CrewAI com 5 agentes para planejar, simular e documentar a suíte de testes. Ideal para:
- Planejamento antes de escrever testes
- Estimar cobertura e esforço
- Gerar relatório de qualidade

### ⚡ Direto (criação direta de testes — preferido do usuário)

Usado quando o usuário pede "gere testes" sem passar por CrewAI. Fluxo:

1. **Auditar cobertura existente** — comparar endpoints registrados nos `urls.py` contra URLs testadas nos arquivos de teste existentes
2. **Identificar gaps** — endpoints sem cobertura de teste
3. **Ler views e serializers** — entender contrato de cada endpoint (métodos HTTP, payload, resposta)
4. **Criar arquivo de teste** — seguir o padrão do projeto:
   - `APITestCase` do DRF
   - `_Base` class com `setUp` criando org + user + auth
   - Testes para: sucesso, auth (401), validação (400), escopo por org, casos de borda
5. **Verificar sintaxe** — `compile(content, path, 'exec')`
6. **Commit + push**

**Padrão de arquivo de teste:**
```python
class _Base(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Alpha")
        self.user = User.objects.create_user(
            email="p@a.com", password="x", name="Prod", organization=self.org
        )
        self.client.credentials(HTTP_AUTHORIZATION=*** {issue_tokens(self.user)['access']}")

class NomeTests(_Base):
    def test_success_case(self):
        resp = self.client.post(self.url, {...}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_requires_auth(self):
        self.client.credentials()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_validation_error(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_scoped_by_org(self):
        # Cria dados em outra org e verifica que não vazam
        ...
```

**Pitfalls pós-migração asyncio (consultar `references/testes-async-pos-migracao.md`):**
- `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` não existe mais — remover o decorator
- Funções `async def` chamadas em testes síncronos precisam de `asyncio.run()`
- Embeddings de 3 dimensões em testes de DocumentChunk precisam ser `[0.1] * 768`
- `sync_to_async` não vê dados não-comitados de `APITestCase` — usar `TransactionTestCase`
- `doc.id` vs `doc.pk` em chamadas de `index_document(str(doc.pk))`

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
