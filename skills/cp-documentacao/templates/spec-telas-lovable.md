# Modelo de spec de telas para gerador de UI (Lovable etc.)

Estrutura comprovada num projeto React (TanStack Router + shadcn). Use como esqueleto
para a saída de "documentar todas as telas para gerar variações de layout".

## Contrato de saída
- Idioma: português do Brasil (labels/CTAs/títulos).
- Preservar o shell (AppShell) em todas as telas internas; só auth é fullscreen.
- Exigir estados por tela: loading, erro (com retry), vazio, populated.
- Variação = layout, NUNCA funcionalidade/escopo.

## Esqueleto do documento

```
# <Produto> — Especificação Técnica de Todas as Telas

> Documento de entrada para o <Lovable>: gere variações de layout fiel ao produto real.
> Leia a seção "Design System" primeiro — define os tokens que TODAS as telas usam.
> Regra de ouro: <frontend é só visualização> (repetir a regra do projeto).

## 1. Design System (obrigatório para todas as telas)
- Tema (cores: fundo, superfície, borda, primary, acento).
- Fontes (headings / corpo / mono).
- Componentes recorrentes (botões, chips/pills, tags de status, cards, tabelas,
  KPIs/métricas, inputs, avatar, toast) — nomear as classes/variantes reais.

## 2. Layout global — AppShell
- Sidebar rail (colapsável) + itens de nav (com rotas).
- Statusbar (metadados globais: online, contagens, selo de plano).
- Nota de preservação obrigatória.

## 3..N Telas
Para cada tela:
- Título + rota (`/path`).
- Objetivo (1 linha).
- Estrutura ordenada (dentro do shell, se interno).
- Estados (loading/erro/vazio/populated) e modais/CTAs.
- ⚠️ Marcar telas fullscreen (auth) separadamente.

## Tela de chat / conversacional — se existir:
- Lista lateral de threads + bubbles + composer.
- ⚠️ Subseção OBRIGATÓRIA: "Generative UI — Cards ricos devolvidos no chat".
  Para CADA card do registry (não são rotas, são telas): header, corpo, estados,
  ações, e a REGRA DE CONTRATO (ex.: card de aprovação encaminha decisão ao backend;
  front não decide nada).

## Resumo de rotas (mapa)
Tabela: Rota | Tela | Dentro do AppShell? (Sim/Não-fullscreen auth)

## Diretrizes para variações de layout
1. Shell consistente em todas as telas internas.
2. Tema escuro fixo (se o produto for escuro) — não inventar claro.
3. Idioma PT-BR.
4. Estados obrigatórios por tela.
5. Um CTA primário por tela; ações secundárias como chips; destrutivas em vermelho + confirmação.
6. Densidade profissional (spaçamento generoso, raio ~12px, sombras suaves, micro-animações).
7. Fontes por função (mono p/ ids/timestamps/tokens).
8. Não criar novas funcionalidades.
```

## Checklist de inventário (para não repetir o erro de pular cards dinâmicos)
- [ ] Rotas file-based inventariadas (routes/**).
- [ ] Shell/layout compartilhado documentado uma vez.
- [ ] Registry de Generative UI / cards dinâmicos inventariados (chat/conversacional).
- [ ] Telas de auth marcadas como fullscreen (sem shell).
- [ ] Design system definido antes das telas.
- [ ] Estados por tela (loading/erro/vazio/populated) presentes.
- [ ] Regra "front = visualização pura / sem regra de negócio" preservada nas descrições.
