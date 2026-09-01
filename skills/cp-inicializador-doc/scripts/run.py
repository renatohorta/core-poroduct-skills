#!/usr/bin/env python3
"""
cp-inicializador-doc — Inicializador de Documentação (self-contained)

Centraliza o contexto do projeto em .context/ como fonte de verdade única,
eliminando a poluição de .hermes/ ou .claude/. Cria arquivos ponte na raiz
(CLAUDE.md e AGENT.md) que instruem qualquer agente a usar .context/.

Uso:
  python run.py                          # inicializa no diretório atual
  python run.py --dir /caminho/do/projeto
  python run.py --dry-run                # mostra o que faria, sem criar
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# DT-01: UTF-8 no stdout/stderr (o console do Windows usa cp1252 e derruba a
# skill com UnicodeEncodeError ao imprimir emoji/box-drawing).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# ESTRUTURA .context/
# ═══════════════════════════════════════════════════════════════════════════

CONTEXT_DIR = ".context"

# Arquivos de documentação por disciplina (docs/)
DOC_FILES = {
    "00-vision.md": "Visão do produto",
    "01-requisitos.md": "Requisitos (cp-requisitos)",
    "02-arquitetura.md": "Arquitetura (cp-arquitetura)",
    "03-seguranca-lgpd.md": "Segurança/LGPD (cp-seguranca)",
    "04-qualidade-qa.md": "Qualidade/QA (cp-qualidade, cp-testes)",
    "05-devops-operacoes.md": "DevOps/Operações (cp-devops)",
    "06-kanban.md": "Kanban/esteira (cp-agilista)",
}

# Pastas de inbox
INBOX_DIRS = ["iniciativas", "tasks", "bugs", "debitos-tecnicos"]

# Pastas de tracking
TRACKING_DIRS = ["progresso.md", "decisoes.md"]

# Colunas do kanban (kanban/) — espelham KANBAN_COLUMNS/BLOCKED_DIR de
# cp-agilista/scripts/run.py. A estrutura nasce aqui, na inicialização: o
# cp-agilista assume que ela existe e a esteira precisa de fila desde o dia 1.
KANBAN_COLUMNS = [
    "1-backlog",
    "2-todo",
    "3-doing",
    "4-review",
    "5-testing",
    "6-staging",
    "7-done",
]
KANBAN_BLOCKED_DIR = "blocked"

# Template do README do .context/
CONTEXT_README = """# .context/ — Fonte de Verdade do Projeto

Este diretório é a **fonte de verdade única** do contexto do projeto. Todos os
agentes (Claude Code, Hermes Agent, etc.) devem ler e escrever contexto aqui,
**nunca** em `.hermes/` ou `.claude/`.

## Estrutura

### docs/ — Disciplinas de engenharia
| Arquivo | Disciplina |
|---------|-----------|
| `00-vision.md` | Visão do produto + Iniciativas (épicos) |
| `01-requisitos.md` | Requisitos (cp-requisitos) |
| `02-arquitetura.md` | Arquitetura (cp-arquitetura) |
| `03-seguranca-lgpd.md` | Segurança/LGPD (cp-seguranca) |
| `04-qualidade-qa.md` | Qualidade/QA (cp-qualidade, cp-testes) |
| `05-devops-operacoes.md` | DevOps/Operações (cp-devops) |
| `06-kanban.md` | Kanban/esteira (cp-agilista) |

### inbox/ — Entrada de trabalho
- `iniciativas/` — Iniciativas de produto
- `tasks/` — Tarefas
- `bugs/` — Bugs
- `debitos-tecnicos/` — Débitos técnicos

### tracking/ — Rastreamento
- `progresso.md` — Progresso geral
- `decisoes.md` — Registro de decisões (ADRs)

### kanban/ — Esteira de execução (`cp-agilista`)
Fonte de verdade do fluxo de tarefas; o Trello, quando configurado, é só um
espelho. Uma task é um `.md` com frontmatter YAML, e a coluna é a pasta.
Item bruto fica em `inbox/`; depois de triado, vira task em `kanban/1-backlog/`.

`1-backlog/` → `2-todo/` → `3-doing/` → `4-review/` → `5-testing/` →
`6-staging/` → `7-done/`, mais `blocked/` para dúvidas e impedimentos.

## Regra

Toda skill `cp-*` documenta seus artefatos em `.context/docs/`. O
`cp-inicializador-doc` garante que a estrutura exista.
"""

# Template do README do kanban/
KANBAN_README = """# kanban/ — Esteira de Execução

Fonte de verdade do fluxo de tarefas, gerida pela skill `cp-agilista`. Quando o
Trello está configurado, ele é apenas uma **visão espelhada** — o que vale é o
que está aqui.

## Relação com `../inbox/`

`inbox/` é entrada bruta: rascunho de iniciativa, task, bug ou débito técnico.
Depois de triado, o item vira uma task aqui, em `1-backlog/`, com `status:`
preenchido — mova com `git mv` para preservar o histórico.

## Colunas

| Pasta | Significado |
|-------|-------------|
| `1-backlog/` | Entrada. O daemon varre aqui por tasks com `status: ready` |
| `2-todo/` | Priorizada, aguardando execução |
| `3-doing/` | Em execução (despachada para a `cp-orquestrador`) |
| `4-review/` | Aguardando revisão |
| `5-testing/` | Em teste |
| `6-staging/` | Homologação |
| `7-done/` | Concluída |
| `blocked/` | Dúvida ou impedimento aguardando resposta humana |

## Formato de uma task

Um arquivo `.md` por task, com frontmatter YAML. O campo `status:` deve
acompanhar a pasta em que o arquivo está.

```markdown
---
id: TASK-001
title: Título da task
status: ready
priority: media
assignee:
created_at: 2026-01-01T00:00:00
updated_at: 2026-01-01T00:00:00
tags: []
---

# Título da task

## Descrição

## Critérios de Aceitação

- [ ] ...
```

`status:` válidos: `backlog`, `ready`, `todo`, `doing`, `review`, `testing`,
`staging`, `done`, `blocked`. Só `ready` no `1-backlog/` é despachado.

## Comandos

```bash
# Monitorar o backlog e despachar tasks
python <skills>/cp-agilista/scripts/run.py --daemon

# Documentar o estado atual do kanban em ../docs/06-kanban.md
python <skills>/cp-agilista/scripts/run.py --doc
```
"""

# Template do CLAUDE.md (ponteiro na raiz)
CLAUDE_MD = """# CLAUDE.md — Contexto do Projeto

**Fonte de verdade: `.context/`**

Leia e escreva todo o contexto do projeto em `.context/`. **NÃO** crie nem use
`.hermes/` ou `.claude/` para contexto.

- Visão geral: `.context/README.md`
- Disciplinas de engenharia: `.context/docs/`
- Entrada de trabalho: `.context/inbox/`
- Rastreamento: `.context/tracking/`
- Esteira de tarefas: `.context/kanban/`
"""

# Template do AGENT.md (ponteiro na raiz)
AGENT_MD = """# AGENT.md — Contexto do Projeto

**Fonte de verdade: `.context/`**

Leia e escreva todo o contexto do projeto em `.context/`. **NÃO** crie nem use
`.hermes/` ou `.claude/` para contexto.

- Visão geral: `.context/README.md`
- Disciplinas de engenharia: `.context/docs/`
- Entrada de trabalho: `.context/inbox/`
- Rastreamento: `.context/tracking/`
- Esteira de tarefas: `.context/kanban/`
"""

# Template de um doc de disciplina
DISCIPLINA_TEMPLATE = """# {titulo}

> Documento gerido pela skill `{skill}`. Atualizado em {data}.

## Status

- [ ] Pendente
- [ ] Em andamento
- [ ] Concluído

## Conteúdo

<!-- Artefatos da skill {skill} são escritos aqui -->

## Decisões

<!-- Registro de decisões desta disciplina -->
"""

# Template especial para 00-vision.md — inclui seção de iniciativas
VISION_TEMPLATE = """# 00 — Visão do Produto

> Documento gerido pela skill `cp-inicializador-doc`. Atualizado em {data}.

## O que é

<!-- Descrição do produto/sistema -->

## Por que este repositório existe

<!-- Contexto, motivação, restrições -->

## Iniciativas (Épicos)

<!-- Lista de iniciativas/épicos do projeto. Cada iniciativa agrega múltiplos cards do kanban.
     Formato sugerido: tabela com ID, título, status e tasks vinculadas.
     Iniciativas concluídas e em aberto podem estar na mesma seção, separadas por subtítulo.

| ID | Iniciativa | Status | Progresso |
|----|-----------|--------|-----------|
| ... | ... | ... | ... |
-->
"""

# Template de um arquivo de inbox
INBOX_TEMPLATE = """# {nome}

<!-- Itens de {nome} são registrados aqui. Formato: um arquivo .md por item. -->
"""

# Template de tracking
TRACKING_PROGRESSO = """# Progresso do Projeto

<!-- Atualizado pelo orquestrador a cada fase concluída -->

| Fase | Status | Data |
|------|--------|------|
| Inicialização | {status} | {data} |
"""

TRACKING_DECISOES = """# Registro de Decisões (ADRs)

<!-- Cada decisão importante é registrada aqui com contexto e justificativa -->

## ADR-0001 — Fonte de verdade em .context/

**Data**: {data}
**Status**: Aceita
**Contexto**: O projeto centraliza o contexto em `.context/` para evitar
poluição de `.hermes/`/`.claude/` e garantir portabilidade entre agentes.
**Decisão**: Todo contexto é lido/escrito em `.context/`.
"""


# ═══════════════════════════════════════════════════════════════════════════
# INICIALIZADOR
# ═══════════════════════════════════════════════════════════════════════════

class InicializadorDoc:
    """Cria a estrutura .context/ e os ponteiros na raiz."""

    def __init__(self, project_dir: Path = None, dry_run: bool = False):
        self.root = Path(project_dir) if project_dir else Path.cwd()
        self.dry_run = dry_run
        self.context = self.root / CONTEXT_DIR
        self.created = []
        self.vision_ingested = False

    def _write(self, path: Path, content: str, overwrite: bool = False):
        """Escreve um arquivo (ou registra no dry-run).

        Por padrão (overwrite=False), não sobrescreve arquivos existentes —
        a inicialização é idempotente e preserva docs já populados.

        Com overwrite=True, sobrescreve (usado para READMEs e templates
        de infraestrutura que não têm conteúdo customizado).
        """
        if path.exists() and not overwrite:
            return
        if self.dry_run:
            self.created.append(f"[dry-run] {path.relative_to(self.root)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.created.append(str(path.relative_to(self.root)))

    def _mkdir(self, path: Path):
        """Cria um diretório (ou registra no dry-run)."""
        if self.dry_run:
            self.created.append(f"[dry-run] {path.relative_to(self.root)}/")
            return
        path.mkdir(parents=True, exist_ok=True)
        self.created.append(str(path.relative_to(self.root)) + "/")

    def ingest_vision(self):
        """Move vision.md (se existir na raiz) para .context/docs/00-vision.md."""
        vision_src = self.root / "vision.md"
        if not vision_src.exists():
            return False
        vision_dst = self.context / "docs" / "00-vision.md"
        if self.dry_run:
            self.created.append(f"[dry-run] mover vision.md → {vision_dst.relative_to(self.root)}")
            return True
        vision_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(vision_src), str(vision_dst))
        self.created.append(f"mover vision.md → {vision_dst.relative_to(self.root)}")
        return True

    def migrate_tracking_to_kanban(self):
        """Migra conteúdo de tracking/tasks.md, tracking/bugs.md e
        tracking/debitos-tecnicos.md para dentro dos respectivos cards no
        kanban/. Preserva backup em tracking/_backup_pre_migracao/. Após a
        migração, remove os 3 arquivos de tracking pois o conteúdo agora
        está nos cards.

        Idempotente: se o card já tem '## Conteúdo do tracking' ou o tracking
        file não existe, pula.
        """
        if self.dry_run:
            self.created.append("[dry-run] migrar tracking/ → kanban/ (pularia se tracking files existirem)")
            return

        tracking_files = {
            "tasks.md": self._parse_tasks,
            "bugs.md": self._parse_bugs,
            "debitos-tecnicos.md": self._parse_debt,
        }

        all_sections = {}

        for fname, parser in tracking_files.items():
            src = self.context / "tracking" / fname
            if not src.exists():
                continue
            text = src.read_text(encoding="utf-8")
            sections = parser(text)
            all_sections.update(sections)

        if not all_sections:
            return  # nada para migrar

        # Backup dos tracking files
        backup_dir = self.context / "tracking" / "_backup_pre_migracao"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for fname in tracking_files:
            src = self.context / "tracking" / fname
            if src.exists():
                dst = backup_dir / fname
                if not dst.exists():
                    os.rename(str(src), str(dst))

        # Percorre todos os cards kanban e injeta conteúdo
        kanban_dir = self.context / "kanban"
        updated = 0
        for root, dirs, files in os.walk(kanban_dir):
            for fname in files:
                if not fname.endswith(".md") or fname == "README.md":
                    continue
                card_id = Path(fname).stem  # BUG-018, TSK-001, TD-022
                card_path = Path(root) / fname

                # Busca seção correspondente
                section_content = None
                if card_id in all_sections:
                    section_content = all_sections[card_id]
                else:
                    continue  # card sem conteúdo no tracking

                # Lê card atual
                card_text = card_path.read_text(encoding="utf-8")

                # Idempotente: já migrado?
                if "## Conteúdo do tracking" in card_text:
                    continue

                # Separa frontmatter do body
                if card_text.startswith("---"):
                    parts = card_text.split("---", 2)
                    frontmatter = "---" + parts[1] + "---"
                    body = parts[2] if len(parts) >= 3 else ""
                else:
                    frontmatter = ""
                    body = card_text

                # Nova body
                title_line = ""
                for line in body.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("# ") and "mora no tracking" not in stripped:
                        title_line = stripped
                        break

                new_body = title_line or f"# {card_id}"
                new_body += "\n\n---\n\n"
                new_body += "## Conteúdo do tracking\n\n"
                new_body += section_content

                card_path.write_text(frontmatter + "\n" + new_body, encoding="utf-8")
                updated += 1

        self.created.append(f"migrar tracking/ → kanban/: {updated} cards atualizados, backup em tracking/_backup_pre_migracao/")

    # ── Parsers de tracking ──────────────────────────────────────────────

    @staticmethod
    def _parse_tasks(text):
        """Parse tasks.md: seções marcadas por '- [ ] **TSK-NNN: Title**'"""
        sections = {}
        pattern = re.compile(r'^- \[(.)\] \*\*(TSK-\d+):(.+?)\*\*')
        lines = text.split("\n")
        current_id = None
        current_lines = []

        for line in lines:
            m = pattern.match(line)
            if m:
                if current_id:
                    sections[current_id] = "\n".join(current_lines)
                current_id = m.group(2)
                status = m.group(1)
                title = m.group(3).strip()
                current_lines = [
                    f"## {current_id}: {title}",
                    f'**Status no tracking:** {"✅ Concluído" if status == "x" else "⬜ Pendente"}',
                ]
            elif current_id:
                current_lines.append(line)

        if current_id:
            sections[current_id] = "\n".join(current_lines)
        return sections

    @staticmethod
    def _parse_bugs(text):
        """Parse bugs.md: seções detalhadas '## BUG-NNN — Title' + tabela"""
        sections = {}
        # Seções detalhadas
        section_pattern = re.compile(r"^## (BUG-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
        section_starts = {}
        for m in section_pattern.finditer(text):
            section_starts[m.group(1)] = (m.start(), m.group(2).strip())

        sorted_ids = sorted(section_starts.keys())
        for i, bug_id in enumerate(sorted_ids):
            start, title = section_starts[bug_id]
            end = section_starts[sorted_ids[i + 1]][0] if i + 1 < len(sorted_ids) else len(text)

            # Tabela
            table_row = ""
            for line in text.split("\n"):
                if f"| {bug_id} " in line or f"|~~{bug_id}~~" in line:
                    table_row = line.strip()
                    break

            content_lines = [f"## {bug_id}: {title}"]
            if table_row:
                content_lines.append(f"**Entrada na tabela:** {table_row}")
            content_lines.append("")
            content_lines.append(text[start:end].strip())
            sections[bug_id] = "\n".join(content_lines)

        return sections

    @staticmethod
    def _parse_debt(text):
        """Parse debitos-tecnicos.md: seções detalhadas '## TD-NNN — Title' + tabela"""
        sections = {}
        section_pattern = re.compile(r"^## (TD-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
        section_starts = {}
        for m in section_pattern.finditer(text):
            section_starts[m.group(1)] = (m.start(), m.group(2).strip())

        sorted_ids = sorted(section_starts.keys())
        for i, td_id in enumerate(sorted_ids):
            start, title = section_starts[td_id]
            end = section_starts[sorted_ids[i + 1]][0] if i + 1 < len(sorted_ids) else len(text)

            table_row = ""
            for line in text.split("\n"):
                if f"| {td_id} " in line or f"|~~{td_id}~~" in line:
                    table_row = line.strip()
                    break

            content_lines = [f"## {td_id}: {title}"]
            if table_row:
                content_lines.append(f"**Entrada na tabela:** {table_row}")
            content_lines.append("")
            content_lines.append(text[start:end].strip())
            sections[td_id] = "\n".join(content_lines)

        return sections

    def build(self) -> dict:
        """Executa a inicialização completa. Retorna resumo."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # README do .context/ — infraestrutura, pode sobrescrever
        self._write(self.context / "README.md", CONTEXT_README, overwrite=True)

        # docs/ — disciplinas: NUNCA sobrescreve docs existentes para
        # preservar conteúdo já populado por skills ou manualmente
        for fname, titulo in DOC_FILES.items():
            doc_path = self.context / "docs" / fname
            if doc_path.exists():
                continue  # preserva conteúdo existente
            if fname == "00-vision.md":
                # 00-vision.md tem template especial com seção de iniciativas
                content = VISION_TEMPLATE.format(data=now)
            else:
                skill = {
                    "01-requisitos.md": "cp-requisitos",
                    "02-arquitetura.md": "cp-arquitetura",
                    "03-seguranca-lgpd.md": "cp-seguranca",
                    "04-qualidade-qa.md": "cp-qualidade",
                    "05-devops-operacoes.md": "cp-devops",
                    "06-kanban.md": "cp-agilista",
                }[fname]
                content = DISCIPLINA_TEMPLATE.format(
                    titulo=titulo, skill=skill, data=now
                )
            self._write(doc_path, content)

        # inbox/
        for nome in INBOX_DIRS:
            self._mkdir(self.context / "inbox" / nome)
            self._write(self.context / "inbox" / nome / "README.md",
                        INBOX_TEMPLATE.format(nome=nome),
                        overwrite=True)

        # tracking/ — templates de infraestrutura, sobrescreve
        self._write(self.context / "tracking" / "progresso.md",
                    TRACKING_PROGRESSO.format(status="Pendente", data=now),
                    overwrite=True)
        self._write(self.context / "tracking" / "decisoes.md",
                    TRACKING_DECISOES.format(data=now),
                    overwrite=True)

        # kanban/ — a esteira existe desde a inicialização, não a partir do
        # primeiro run do cp-agilista. Cada coluna leva um .gitkeep porque o
        # git não versiona diretório vazio.
        self._write(self.context / "kanban" / "README.md", KANBAN_README,
                    overwrite=True)
        for col in KANBAN_COLUMNS + [KANBAN_BLOCKED_DIR]:
            self._mkdir(self.context / "kanban" / col)
            self._write(self.context / "kanban" / col / ".gitkeep", "",
                        overwrite=True)

        # Migração tracking → kanban: se existirem tracking/tasks.md,
        # tracking/bugs.md ou tracking/debitos-tecnicos.md, extrai o conteúdo
        # de cada seção e injeta nos respectivos cards do kanban. Os tracking
        # files são movidos para _backup_pre_migracao/.
        self.migrate_tracking_to_kanban()

        # Ingestão do vision.md
        vision_ingested = self.ingest_vision()
        self.vision_ingested = vision_ingested

        # Ponteiros na raiz — infraestrutura, sobrescreve
        self._write(self.root / "CLAUDE.md", CLAUDE_MD, overwrite=True)
        self._write(self.root / "AGENT.md", AGENT_MD, overwrite=True)

        return {
            "root": str(self.root),
            "context": str(self.context),
            "files_created": len(self.created),
            "vision_ingested": vision_ingested,
            "dry_run": self.dry_run,
        }

    def report_gaps(self):
        """Apresenta resumo executivo e perguntas clarificatórias por disciplina."""
        print("\n" + "=" * 60)
        print("  📋 RESUMO EXECUTIVO — Inicialização de Documentação")
        print("=" * 60)
        print(f"  Raiz: {self.root}")
        print(f"  Fonte de verdade: {self.context}")
        print(f"  Arquivos criados: {len(self.created)}")
        print(f"  Kanban: {len(KANBAN_COLUMNS)} colunas + blocked/ em "
              f"{CONTEXT_DIR}/kanban/")
        print(f"  vision.md ingerido: {'sim' if self.vision_ingested else 'não encontrado'}")
        print()

        print("  ❓ Perguntas clarificatórias por disciplina:")
        perguntas = {
            "Requisitos (01)": "Qual o escopo do MVP? Quais os stakeholders?",
            "Arquitetura (02)": "Quais as tecnologias? Há restrições de infraestrutura?",
            "Segurança/LGPD (03)": "Quais dados pessoais são tratados? Há DPO?",
            "Qualidade/QA (04)": "Qual a cobertura de testes desejada? Há CI?",
            "DevOps/Operações (05)": "Onde será o deploy? Há monitoramento?",
            "Kanban/esteira (06)": "O kanban já existe em .context/kanban/ — há integração Trello? Quais as primeiras tasks?",
        }
        for disc, pergunta in perguntas.items():
            print(f"    • {disc}: {pergunta}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-inicializador-doc: Inicializador de Documentação",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python run.py
  python run.py --dir /caminho/do/projeto
  python run.py --dry-run
        """,
    )
    parser.add_argument("--dir", "-d", default=None,
                        help="Diretório do projeto (default: diretório atual)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra o que faria, sem criar arquivos")
    args = parser.parse_args()

    init = InicializadorDoc(Path(args.dir) if args.dir else None, args.dry_run)
    resumo = init.build()

    print(f"🚀 Inicializando documentação em {resumo['root']}...")
    if resumo["dry_run"]:
        print("🧪 DRY RUN — nada foi criado. Remova --dry-run para executar.\n")
    else:
        print(f"✅ Estrutura .context/ criada em {resumo['context']}\n")

    for item in init.created:
        print(f"  {item}")

    init.report_gaps()


if __name__ == "__main__":
    main()
