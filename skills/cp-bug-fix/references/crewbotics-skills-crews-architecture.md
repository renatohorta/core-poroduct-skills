# Crewbotics — Skills x Crews: Arquitetura Real (2026-08-08)

Visão de arquitetura descoberta ao investigar "posso apagar os templates de crew
do marketplace se as skills fazem a mesma coisa?". Resposta: **não são a mesma
coisa, e apagar quebra o Copilot**. Guarde isto antes de qualquer refactor de
skills/crews no projeto.

## Dois mecanismos distintos

1. **Skills** — capacidades de conversa que o LLM chama via function calling.
   - Registradas 100% em CÓDIGO via `@register_skill` (decorator). **Não há modelo
     no banco para skill** — não é editável via admin (por design).
   - Atômicas (executam direto): `web_search`, `analyze_image`, `create_presentation`,
     `canvas_design`, `generate_image`, `execute_crew`, `list_crews`, etc.
   - Compostas (`CpCrewSkill`): acionam uma crew. Buscam `CrewTemplate` por
     `template_slug`, criam `CrewInstance` (copia members/tasks) e chamam
     `dispatch_run`.

2. **Crews / CrewTemplate** — o motor multi-agente.
   - `CrewTemplate` é o catálogo (marketplace), com `CrewTemplateMember` (agentes,
     tools por agente) + `CrewTemplateTask` (tasks, quality_gate, handoff,
     is_output, tools por task). Tem admin (`crews/admin.py`) com inlines.
   - `CrewInstance` = crew contratada/customizada pelo usuário, copia members/tasks
     do template. Acionável via `dispatch_run` e via skill `execute_crew`.

## Ponto crítico: skill composta DEPENDE do CrewTemplate

`CpCrewSkill.execute()` faz:
```python
template = CrewTemplate.objects.filter(
    metadata__crew_slug=self.template_slug, is_public=True).first()
if not template:
    return {"error": f"Template '{self.template_slug}' não encontrado no marketplace."}
```
Cada uma das 46 skills `cp_*` (Fábrica de Software) tem `template_slug = "cp_*"`.
**Em 2026-08-08 havia 0 templates `cp_*` no banco** (só os 6 `agency-*`) → todas as
46 skills `cp_*` retornavam "Template não encontrado" (quebradas).

Implicação: **esconder/apagar o marketplace NÃO faz as skills "assumirem"** — as
skills `cp_*` procuram slugs `cp_*`, não `agency-*`. Para as skills do Copilot
funcionarem é preciso POPULAR os templates `cp_*` (internos, `is_public=False`).

## Estado dos dados (08/08)

- Templates agency no banco (6, todos is_public=True): agency-campanha-marketing-
  multicanal, agency-carousel-creator-instagram (criado na sessão), agency-feature-
  enterprise, agency-lancamento-produto-digital, agency-presenca-digital-profissional,
  agency-resposta-crise.
- `crews/seed_data/crew_templates.json` está VAZIO (`{"crews": []}`). Os `cp_*` NUNCA
  foram seedados.
- `crews/seed_data/agency_crew_templates.json` tem os 6 agency.

## Seed atual é DESTRUTIVO

`upsert_agency_crews` e `upsert_crews` fazem `obj.members.all().delete()` +
`obj.tasks.all().delete()` e recriam. **Qualquer edição no admin é perdida no próximo
seed.** Se o usuário pedir "editar template via admin", é preciso tornar o seed
não-destrutivo (só popular 1ª vez ou por flag) — ainda não feito (a sessão terminou
antes disso).

## Componentização alvo (direção do usuário)

Usuário quer "componentização ao máximo, mantendo em código, sem editar tudo por
banco". Visão de camadas:
- SKILL (processo auto-contido) → Skill atômica | Skill composta (→ crew)
- CREW (motor) → agentes reutilizáveis (Python, não JSON) + tasks reutilizáveis
- Substituir o `agency_crew_templates.json` por definições Python de agentes/tasks/
  crews compostos (cada agente definido 1x e referenciado por N crews).
- Já há reuso parcial: `agency-reality-checker` aparece em 5 crews, `agency-content-
  creator` em 4, etc. (20 agentes distintos usados em 35 instâncias).

## Ferramentas/execução úteis nesta área

- Rodar queries Django com o venv do projeto e **PYTHONPATH limpo** (só
  `.venv\Lib\site-packages`), senão o sandbox Hermes injeta o PIL/venv dele e dá
  `ImportError: cannot import name '_imaging'`. Usar:
  `env = dict(os.environ); env["PYTHONPATH"] = <site-packages do projeto>`
- Inspetar o catálogo de skills sem instanciar com usuário: `from chat.skills.registry import _registry` e iterar `sorted(_registry.keys())`.
