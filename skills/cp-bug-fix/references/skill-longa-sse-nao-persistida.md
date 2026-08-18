# Skill longa síncrona que "some" do chat (tool_call sem tool_result)

Padrão de bug descoberto em 2026-08-08 (LOOP-20260808-carrossel-ia-instagram):
usuário pede um carrossel de imagens de IA no chat; o Copilot busca notícias e
gera o carrossel, mas a resposta do assistente com o card **nunca aparece** na
conversa — a história some.

## Sintoma no ExecutionLog

Um `tool_call` de `create_presentation` (ou outra skill longa) **sem** `tool_result`
correspondente. A `AgentTask` fica com status `running` para sempre
(`finished_at=None`). Os artefatos da skill (apresentação, SVGs, imagens) são
criados no backend, mas a `ChatMessage` do assistente com o card **nunca é
persistida**.

## Causa raiz

A skill roda **inline no request SSE** (`_execute_skill` →
`skill_map[tool_name].execute(**args)` em `chat/agui/engine_async.py`). Se ela
demora mais que o timeout do Daphne, o Daphne mata a conexão SSE ("took too long
to shut down and was killed") **antes** que o código pós-execução rode — o
`_log("tool_result", ...)` e o `_finish()` (que persiste a `ChatMessage` e marca
a task `completed`) nunca executam.

No caso do carrossel: `presentations/services/orchestrator.py` →
`execute_presentation_pipeline` gera **imagem para cada slide** via
`_generate_image_file` (chamada síncrona ao Gemini `gemini-2.5-flash-image`).
12 slides ≈ 13 minutos. O `_finish()` em `chat/engine.py:494` (que cria a
`ChatMessage` e seta `task.status="completed"`) nunca roda.

## Como confirmar

1. `ExecutionLog.objects.filter(task_id=<id>)` — ver `tool_call` de
   `create_presentation` sem `tool_result`.
2. `AgentTask.objects.filter(id=<id>)` — status `running`, `finished_at=None`.
3. Conferir que os artefatos existem (ex: `Presentation` criada, `ProductContext`
   SVGs arquivados) — prova que a skill rodou, só a persistência da resposta falhou.

## Correção (implementação que funciona)

Skills longas NÃO devem rodar inline no SSE. Devem ser despachadas em **daemon
thread** (mesmo padrão do `run_crew`), persistindo a resposta via `_finish`
quando terminarem — mesmo que o Daphne mate o SSE antes.

Em `chat/agui/engine_async.py`:

1. **Lista de skills longas** (constante de módulo):
```python
LONG_SKILLS = {"create_presentation", "canvas_design", "generate_image"}
```

2. **No `_run_loop`, antes de executar a skill inline**, intercepte as longas —
   emite um placeholder amigável ao usuário, despacha em background e encerra o
   turno (persistindo o placeholder via `_finish` para a task não ficar presa em
   `running`):
```python
if call.name in LONG_SKILLS:
    msg = (f"⏳ Estou gerando o conteúdo de **{call.name}**… "
           "isso pode levar alguns minutos. Assim que ficar pronto, "
           "o resultado aparece aqui na conversa (recarregue se necessário).")
    async for frame in self._emit_text(msg):
        yield frame
    self._dispatch_long_skill(skill_map, call.name, call.args)
    await sync_to_async(self._sync._finish)(msg)  # persiste o placeholder
    return  # encerra o turno; NÃO emite TOOL_CALL_RESULT com o resultado real
```

3. **`_dispatch_long_skill`** roda a skill em daemon thread e persiste o resultado
   quando termina — o `_finish` aqui roda FORA do event loop async (na thread), então
   o ORM síncrono é seguro:
```python
def _dispatch_long_skill(self, skill_map, tool_name, args):
    import threading
    def _run():
        try:
            result = skill_map[tool_name].execute(**args)
            if isinstance(result, dict) and "component" in result:
                summary = self._sync._summarize_ui_component(result)
                self._sync._log("response", payload={"ui_component": result})
                self._sync._finish(summary, ui_component=result)
            elif isinstance(result, dict) and result.get("error"):
                self._sync._finish(f"⚠️ Não consegui concluir: {result['error']}")
            else:
                self._sync._finish(str(result))
        except Exception as exc:
            logger.exception("Skill longa %s falhou: %s", tool_name, exc)
            self._sync._finish(f"⚠️ Ocorreu um erro ao gerar: {exc}")
    threading.Thread(target=_run, daemon=True).start()
```

### Por que o `_finish` inline no teste quebra

O `_finish()` usa `transaction.atomic()` (ORM síncrono). Chamá-lo DENTRO do event
loop async (ex: num mock de `_dispatch_long_skill` que chama `_finish` direto)
levanta `SynchronousOnlyOperation`. No fluxo real, `_dispatch_long_skill` roda em
**daemon thread** (fora do loop), então o ORM é seguro. Ao testar, mocke
`_dispatch_long_skill` para apenas registrar a chamada — NÃO tente rodar `_finish`
inline no teste.

Alternativa de mitigação (não substitui o dispatch): reduzir o trabalho síncrono
(ex: gerar imagens de forma não-bloqueante/paralela, ou não gerar imagem por slide
no request).

## Pitfall de teste

- Não confie só no `bun run build`/pytest — o bug só se manifesta no runtime real
  (Daphne matando SSE). Reproduzir via browser com o prompt real e verificar se a
  `ChatMessage` do assistente foi persistida após a geração.
- Ao escrever testes AG-UI para o dispatch: mocke `litellm.acompletion` com um turno
  de `_tool_call_chunks("c1", "create_presentation", '{"prompt": "..."}')` e mocke
  `_dispatch_long_skill` para registrar a chamada. Valide que o SSE NÃO emite
  `TOOL_CALL_RESULT` (skill foi para background), emite um texto placeholder e
  termina com `RUN_FINISHED`. Confirme que a `AgentTask` ficou `completed` (o
  placeholder foi persistido). Ex.: `tests/chat/test_agui_long_skill.py`.
- Para skills NÃO-longas (ex: web_search), valide que `_dispatch_long_skill` NÃO é
  chamada (continuam inline).
