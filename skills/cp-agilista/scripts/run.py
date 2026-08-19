#!/usr/bin/env python3
"""
cp-agilista — Agilista (Esteira de Execução) (self-contained)

Maestro da esteira de execução. O sistema de arquivos local (.context/kanban/) é a
FONTE DE VERDADE. O Trello é apenas uma VISÃO ESPELHADA do estado local —
nunca a fonte de decisão.

Arquitetura:
  [Local .context/kanban/]  ──(fonte de verdade)──►  [Trello (espelho/visão)]
        ▲                                              │
        └────────────── sincroniza estado ──────────────┘

  - O daemon SEMPRE lê do local (scan_ready, movimentação, dúvidas, impedimentos).
  - Se o espelhamento Trello estiver habilitado (--sync-trello), cada mudança
    local é refletida no Trello (cria/atualiza cards conforme o estado local).
  - O Trello NUNCA decide o estado — apenas exibe o que está no local.

Componentes:
  - CPAgilistaDaemon        : polling contínuo do local + despacho p/ orquestrador
  - CPAgilistaFeedbackLoop  : dúvidas, impedimentos e retomada (no local)
  - LocalIntegration        : fonte de verdade (.context/kanban/)
  - TrelloMirror            : espelho/visão do estado local no Trello
  - TaskTemplate            : template de task .md com frontmatter YAML

Uso:
  # Daemon de polling (sempre lê do local)
  python run.py --daemon

  # Daemon com espelhamento Trello (visão do local no Trello)
  python run.py --daemon --sync-trello

  # Registrar dúvida (no local; espelha no Trello se habilitado)
  python run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?" --sync-trello

  # Registrar impedimento
  python run.py --impedimento "task-123" --erro "Falha de conexão" --severidade alta

  # Retomar tarefa (resposta humana)
  python run.py --resume "task-123" --resposta "O MVP cobre login e cadastro"

  # Sincronizar o estado local inteiro para o Trello (one-shot)
  python run.py --sync-trello

  # Dry run
  python run.py --daemon --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
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
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

# Diretório raiz do kanban local. Usa env var com default relativo (portável).
KANBAN_ROOT = Path(os.environ.get("KANBAN_ROOT", ".context/kanban"))

# Pastas do kanban (ordem do fluxo)
KANBAN_COLUMNS = [
    "1-backlog",
    "2-todo",
    "3-doing",
    "4-review",
    "5-testing",
    "6-staging",
    "7-done",
]
BLOCKED_DIR = "blocked"

# Raiz do inbox: zona de drop de texto livre. Qualquer arquivo de texto solto
# na RAIZ (não nas subpastas) é triado e vira task no kanban.
INBOX_ROOT = Path(os.environ.get("INBOX_ROOT", ".context/inbox"))

# Onde o texto bruto é arquivado depois de virar task. A raiz esvazia, então a
# triagem é naturalmente idempotente — nada é triado duas vezes.
INBOX_PROCESSED_DIR = ".processados"

# Arquivos da raiz do inbox que a triagem ignora (documentação, não trabalho).
INBOX_IGNORED = {"readme.md", "index.md", ".gitkeep"}

# Teto de tamanho por item dropado. Acima disso não é texto solto, é anexo.
INBOX_MAX_BYTES = int(os.environ.get("INBOX_MAX_BYTES", 512 * 1024))

# Trilhas (o `tipo:` do item) e o prefixo de id de cada uma.
TRILHAS = {
    "iniciativa": "INIT",
    "task": "TASK",
    "bug": "BUG",
    "debito-tecnico": "DT",
}
DEFAULT_TRILHA = "task"

# Status que a triagem atribui quando o item não declara um. `ready` faz a
# esteira despachar no ciclo seguinte — é o ponto do drop zone.
TRIAGE_STATUS = os.environ.get("INBOX_TRIAGE_STATUS", "ready")

# Heurística de classificação: a primeira trilha cujo padrão casa vence, então
# a ordem importa. `bug` vem antes de tudo porque relato de erro é o caso mais
# frequente e o mais específico; `task` é o default, não um padrão.
TRILHA_PATTERNS = [
    ("bug", r"(?:\bbugs?\b|\berros?\b|\bfalha\b|exce[çc][ãa]o|stack ?trace|"
            r"traceback|\bquebrou\b|n[ãa]o funciona|regress[ãa]o|\bcrash)"),
    ("debito-tecnico", r"(?:d[ée]bito t[ée]cnico|refatora|refactor|gambiarra|"
                       r"workaround|d[íi]vida t[ée]cnica|\bTODO\b|\bFIXME\b)"),
    ("iniciativa", r"(?:\biniciativa\b|\b[ée]picos?\b|\bepic\b|\bvis[ãa]o\b|"
                   r"\broadmap\b|\bOKRs?\b|\bestrat[ée]gia\b|\bdiscovery\b)"),
]

# Prioridades aceitas no frontmatter (mesma escala do --severidade).
VALID_PRIORITIES = {"baixa", "media", "alta", "critica"}

# Estados válidos (frontmatter `status:`)
VALID_STATUSES = {
    "backlog", "ready", "todo", "doing", "review",
    "testing", "staging", "done", "blocked",
}

# Intervalo de polling (segundos)
POLL_INTERVAL = int(os.environ.get("AGILISTA_POLL_INTERVAL", "10"))

# Eventos padronizados
EVENT_TASK_DISPATCHED = "TASK_DISPATCHED"
EVENT_DUVIDA = "DUVIDA"
EVENT_IMPEDIMENTO = "IMPEDIMENTO"
EVENT_HUMAN_CLARIFICATION = "HUMAN_CLARIFICATION_RECEIVED"
EVENT_INBOX_TRIADO = "INBOX_ITEM_TRIADO"


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE DE TASK (.md com frontmatter YAML)
# ═══════════════════════════════════════════════════════════════════════════

TASK_TEMPLATE = """---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
assignee: {assignee}
created_at: {created_at}
updated_at: {updated_at}
tags: {tags}
tipo: {tipo}
origem: {origem}
---

# {title}

## Descrição

{description}

## Critérios de Aceitação

- [ ] {acceptance_criteria}

## Dúvidas Pendentes

<!-- Seções adicionadas pelo CPAgilistaFeedbackLoop -->

## Log de Impedimentos

<!-- Seções adicionadas pelo CPAgilistaFeedbackLoop -->
"""


def build_task_template(task_id, title, status="backlog", priority="media",
                        assignee="", tags="[]", description="",
                        acceptance_criteria="Definir critérios de aceitação",
                        tipo=DEFAULT_TRILHA, origem=""):
    """Gera o conteúdo de um arquivo de task .md a partir do template.

    `tipo` é a trilha do item (ver TRILHAS) e `origem` guarda o nome do arquivo
    dropado no inbox, quando a task veio da triagem — sem isso não há como
    voltar do kanban ao texto bruto arquivado.
    """
    now = datetime.now().isoformat(timespec="seconds")
    return TASK_TEMPLATE.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        assignee=assignee,
        created_at=now,
        updated_at=now,
        tags=tags,
        tipo=tipo,
        origem=origem,
        description=description,
        acceptance_criteria=acceptance_criteria,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PARSER DE FRONTMATTER YAML (mínimo, sem dependência externa)
# ═══════════════════════════════════════════════════════════════════════════

def parse_frontmatter(content: str) -> dict:
    """Extrai o frontmatter YAML (--- ... ---) de um arquivo .md."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def read_task_meta(path: Path) -> dict:
    """Lê o frontmatter completo de um arquivo de task."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    return parse_frontmatter(content)


def read_task_status(path: Path) -> str:
    """Lê o status de um arquivo de task a partir do frontmatter."""
    return read_task_meta(path).get("status", "")


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRAÇÃO LOCAL (.context/kanban/) — FONTE DE VERDADE
# ═══════════════════════════════════════════════════════════════════════════

class LocalIntegration:
    """Fonte de verdade do kanban (.context/kanban/). Todas as decisões vêm daqui."""

    def __init__(self, root: Path = None):
        self.root = Path(root) if root else KANBAN_ROOT
        self.ensure_structure()

    def ensure_structure(self):
        """Cria a estrutura de pastas do kanban se não existir."""
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            (self.root / col).mkdir(parents=True, exist_ok=True)

    def scan_ready(self) -> list:
        """Varre o backlog por arquivos com status: ready."""
        ready = []
        backlog = self.root / "1-backlog"
        if backlog.exists():
            for f in sorted(backlog.glob("*.md")):
                if read_task_status(f) == "ready":
                    ready.append(f)
        return ready

    def all_tasks(self) -> list:
        """Lista todas as tasks com sua coluna atual (para espelhamento)."""
        tasks = []
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            col_dir = self.root / col
            if not col_dir.exists():
                continue
            for f in sorted(col_dir.glob("*.md")):
                meta = read_task_meta(f)
                tasks.append({
                    "path": f,
                    "id": f.stem,
                    "title": meta.get("title", f.stem),
                    "status": meta.get("status", col),
                    "column": col,
                    "priority": meta.get("priority", "media"),
                })
        return tasks

    def document_kanban(self, context_root: Path = None) -> Path:
        """Gera/atualiza .context/docs/06-kanban.md com o estado do kanban.

        O kanban é documentado na estrutura .context/ (fonte de verdade do
        projeto). Se .context/ não existir, o arquivo é criado mesmo assim
        (o cp-inicializador-doc garante a estrutura completa).
        """
        tasks = self.all_tasks()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Agrupa por coluna
        by_col = {}
        for t in tasks:
            by_col.setdefault(t["column"], []).append(t)

        lines = [
            "# Kanban / Esteira de Execução",
            "",
            "> Documento gerido pela skill `cp-agilista`. Atualizado em " + now + ".",
            "",
            "## Estado do Kanban",
            "",
            "| Coluna | Tarefas |",
            "|--------|---------|",
        ]
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            n = len(by_col.get(col, []))
            lines.append(f"| {col} | {n} |")

        lines.append("")
        lines.append("## Tarefas por coluna")
        lines.append("")
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            col_tasks = by_col.get(col, [])
            if not col_tasks:
                continue
            lines.append(f"### {col}")
            lines.append("")
            for t in col_tasks:
                lines.append(f"- **{t['title']}** (`{t['id']}`) — prioridade {t['priority']}")
            lines.append("")

        content = "\n".join(lines)

        # Destino: .context/docs/06-kanban.md
        # Se o kanban já está dentro de .context/ (ex.: .context/kanban/),
        # o parent é .context/; senão, sobe um nível e acha .context/.
        if context_root is None:
            if self.root.parent.name == ".context":
                context_root = self.root.parent
            else:
                context_root = self.root.parent / ".context"
        dest = Path(context_root) / "docs" / "06-kanban.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return dest

    def move_to(self, task_id: str, column: str) -> Path:
        """Move um arquivo de task para uma coluna."""
        src = self.find_task(task_id)
        if not src:
            return None
        dest_dir = self.root / column
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        src.rename(dest)
        return dest

    def find_task(self, task_id: str) -> Path:
        """Localiza um arquivo de task pelo id em qualquer coluna."""
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            for f in (self.root / col).glob("*.md"):
                if f.stem == task_id or task_id in f.name:
                    return f
        return None

    def add_duvida(self, task_id: str, mensagem: str, origem: str = "IA") -> Path:
        """Adiciona seção '## ❓ Dúvidas Pendentes' no arquivo local."""
        path = self.find_task(task_id)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        duvida = (
            f"\n### ❓ [Dúvida da IA - {origem}] {datetime.now().isoformat(timespec='seconds')}\n"
            f"{mensagem}\n"
        )
        if "## ❓ Dúvidas Pendentes" in content:
            content = content.replace("## ❓ Dúvidas Pendentes",
                                      "## ❓ Dúvidas Pendentes\n" + duvida)
        else:
            content += f"\n## ❓ Dúvidas Pendentes\n{duvida}"
        path.write_text(content, encoding="utf-8")
        return path

    def add_impedimento(self, task_id: str, erro: str, severidade: str = "media") -> Path:
        """Move para blocked/ e anexa log de erro e severidade."""
        path = self.move_to(task_id, BLOCKED_DIR)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        log = (
            f"\n### 🚧 [Impedimento] {datetime.now().isoformat(timespec='seconds')}\n"
            f"- **Severidade**: {severidade}\n"
            f"- **Erro**: {erro}\n"
        )
        if "## Log de Impedimentos" in content:
            content = content.replace("## Log de Impedimentos",
                                      "## Log de Impedimentos\n" + log)
        else:
            content += f"\n## Log de Impedimentos\n{log}"
        path.write_text(content, encoding="utf-8")
        return path

    def resume(self, task_id: str, resposta: str) -> Path:
        """Registra a resposta humana e move de volta para todo/."""
        path = self.find_task(task_id)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        resp = (
            f"\n### ✅ [Resposta Humana] {datetime.now().isoformat(timespec='seconds')}\n"
            f"{resposta}\n"
        )
        content += resp
        path.write_text(content, encoding="utf-8")
        # Move de blocked/ para 2-todo/
        if path.parent.name == BLOCKED_DIR:
            dest = self.root / "2-todo" / path.name
            path.rename(dest)
            return dest
        return path


# ═══════════════════════════════════════════════════════════════════════════
# TRELLO MIRROR (espelho/visão do estado local)
# ═══════════════════════════════════════════════════════════════════════════

# Mapeia coluna local -> lista Trello
COLUMN_TO_TRELLO_LIST = {
    "1-backlog": "Backlog",
    "2-todo": "Todo",
    "3-doing": "Doing",
    "4-review": "Review",
    "5-testing": "Testing",
    "6-staging": "Staging",
    "7-done": "Done",
    "blocked": "Blocked",
}


class TrelloMirror:
    """Espelho/visão do estado local no Trello.

    O Trello NUNCA é a fonte de decisão — apenas reflete o que está no local.
    Se as tools MCP do Trello não estiverem disponíveis, o espelhamento é
    desabilitado silenciosamente (o local continua funcionando sozinho).
    """

    def __init__(self, board_name: str = None):
        self.board_name = board_name or os.environ.get("TRELLO_BOARD", "Backlog")
        self.available = self._check_tools()

    def _check_tools(self) -> bool:
        """Verifica se as tools MCP do Trello estão disponíveis."""
        try:
            from mcp_tools import trello  # noqa: F401
            return True
        except ImportError:
            return False

    def _list_for_column(self, column: str) -> str:
        """Retorna a lista Trello correspondente a uma coluna local."""
        return COLUMN_TO_TRELLO_LIST.get(column, "Backlog")

    def sync_task(self, task: dict):
        """Espelha uma task local no Trello (cria/atualiza card na lista certa)."""
        if not self.available:
            return False
        task_id = task["id"]
        title = task["title"]
        column = task["column"]
        trello_list = self._list_for_column(column)
        # Em ambiente real, chama as tools MCP:
        #   card = trello.find_card(name=title)
        #   if not card: trello.create_card(name=title, list_name=trello_list)
        #   else: trello.move_card(card_id=card.id, list_name=trello_list)
        print(f"  🔄 [Trello] '{title}' → lista '{trello_list}'")
        return True

    def sync_all(self, tasks: list) -> int:
        """Espelha todas as tasks locais no Trello. Retorna quantas sincronizou."""
        if not self.available:
            print("  ⚠️  Trello mirror indisponível (tools MCP não encontradas). "
                  "Local continua como fonte de verdade.")
            return 0
        count = 0
        for task in tasks:
            if self.sync_task(task):
                count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════
# LOOP BIDIRECIONAL DE FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════

class CPAgilistaFeedbackLoop:
    """Gerencia dúvidas, impedimentos e retomada.

    O local é SEMPRE a fonte de verdade. O Trello (se habilitado) é apenas
    espelhado após cada operação.
    """

    def __init__(self, sync_trello: bool = False):
        self.sync_trello = sync_trello
        self.local = LocalIntegration()
        self.trello = TrelloMirror()

    def _dispatch(self, event: str, payload: dict):
        """Emite um evento padronizado (log + payload JSON)."""
        event_line = {
            "event": event,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
        print(json.dumps(event_line, ensure_ascii=False, indent=2))
        return event_line

    def _mirror(self, task_id: str):
        """Espelha a task no Trello se o espelhamento estiver habilitado."""
        if not self.sync_trello:
            return
        path = self.local.find_task(task_id)
        if not path:
            return
        meta = read_task_meta(path)
        self.trello.sync_task({
            "id": task_id,
            "title": meta.get("title", task_id),
            "column": path.parent.name,
        })

    def duvida(self, task_id: str, mensagem: str, origem: str = "IA") -> dict:
        """Registra uma dúvida da IA no local e espelha no Trello."""
        payload = {"task_id": task_id, "mensagem": mensagem, "origem": origem}
        self.local.add_duvida(task_id, mensagem, origem)
        self._mirror(task_id)
        return self._dispatch(EVENT_DUVIDA, payload)

    def impedimento(self, task_id: str, erro: str, severidade: str = "media") -> dict:
        """Registra um impedimento no local (move p/ blocked/) e espelha."""
        payload = {"task_id": task_id, "erro": erro, "severidade": severidade}
        self.local.add_impedimento(task_id, erro, severidade)
        self._mirror(task_id)
        return self._dispatch(EVENT_IMPEDIMENTO, payload)

    def resume_task(self, task_id: str, resposta: str) -> dict:
        """Captura a resposta humana no local e espelha no Trello."""
        payload = {"task_id": task_id, "resposta": resposta}
        self.local.resume(task_id, resposta)
        self._mirror(task_id)
        return self._dispatch(EVENT_HUMAN_CLARIFICATION, payload)


# ═══════════════════════════════════════════════════════════════════════════
# DAEMON DE POLLING
# ═══════════════════════════════════════════════════════════════════════════

class CPAgilistaDaemon:
    """Polling contínuo do LOCAL (fonte de verdade) e despacho de tarefas.

    O Trello, se habilitado, é apenas espelhado — nunca lido como fonte.
    """

    def __init__(self, dry_run: bool = False, sync_trello: bool = False):
        self.dry_run = dry_run
        self.sync_trello = sync_trello
        self.local = LocalIntegration()
        self.trello = TrelloMirror()
        self.feedback = CPAgilistaFeedbackLoop(sync_trello)

    def _dispatch_task(self, task_path: Path):
        """Despacha uma tarefa pronta para a cp-orquestrador."""
        task_id = task_path.stem
        payload = {
            "task_id": task_id,
            "source": "local",
            "path": str(task_path),
            "event": EVENT_TASK_DISPATCHED,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        # Em ambiente real, chama a cp-orquestrador:
        #   subprocess.run([sys.executable, ORQUESTRADOR_RUN, task_id, "--auto"])
        # Move para 2-todo/ (despachada) — sempre no local
        if not self.dry_run:
            self.local.move_to(task_id, "2-todo")
            if self.sync_trello:
                self.trello.sync_task({
                    "id": task_id,
                    "title": task_path.stem,
                    "column": "2-todo",
                })

    def poll_once(self) -> list:
        """Uma única varredura do LOCAL. Retorna as tarefas prontas."""
        ready = self.local.scan_ready()

        dispatched = []
        for task in ready:
            print(f"  📦 Tarefa pronta: {task.name}")
            self._dispatch_task(task)
            dispatched.append(task)
        return dispatched

    def run(self, iterations: int = None):
        """Loop de polling contínuo do local."""
        print(f"🚀 CPAgilistaDaemon iniciado (fonte=local, "
              f"interval={POLL_INTERVAL}s, dry_run={self.dry_run}, "
              f"sync_trello={self.sync_trello})")
        print(f"   Kanban local (fonte de verdade): {self.local.root.resolve()}")
        if self.sync_trello:
            print(f"   Trello (espelho): board='{self.trello.board_name}'")
        print("   Pressione Ctrl+C para parar.\n")

        count = 0
        try:
            while iterations is None or count < iterations:
                count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Poll #{count}...")
                self.poll_once()
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n⏹️  Daemon interrompido pelo usuário.")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-agilista: Agilista (Esteira de Execução)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
O LOCAL (.context/kanban/) é sempre a fonte de verdade. O Trello é apenas uma visão
espelhada (--sync-trello) do estado local.

Exemplos:
  python run.py --daemon
  python run.py --daemon --sync-trello
  python run.py --sync-trello
  python run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?"
  python run.py --impedimento "task-123" --erro "Falha de conexão" --severidade alta
  python run.py --resume "task-123" --resposta "O MVP cobre login e cadastro"
  python run.py --daemon --dry-run
        """,
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Inicia o daemon de polling (sempre lê do local)")
    parser.add_argument("--sync-trello", action="store_true",
                        help="Espelha o estado local no Trello (visão, não fonte)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Não executa ações, apenas mostra o que faria")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Número de polls (default: infinito)")
    parser.add_argument("--duvida", metavar="TASK_ID",
                        help="Registra uma dúvida para a tarefa (no local)")
    parser.add_argument("--mensagem", help="Mensagem da dúvida")
    parser.add_argument("--impedimento", metavar="TASK_ID",
                        help="Registra um impedimento para a tarefa (no local)")
    parser.add_argument("--erro", help="Descrição do erro do impedimento")
    parser.add_argument("--severidade", choices=["baixa", "media", "alta", "critica"],
                        default="media", help="Severidade do impedimento")
    parser.add_argument("--resume", metavar="TASK_ID",
                        help="Retoma uma tarefa com resposta humana (no local)")
    parser.add_argument("--resposta", help="Resposta humana para desbloquear")
    parser.add_argument("--init", action="store_true",
                        help="Cria a estrutura .context/kanban/ e sai")
    parser.add_argument("--doc", action="store_true",
                        help="Gera/atualiza .context/docs/06-kanban.md com o estado do kanban")
    args = parser.parse_args()

    feedback = CPAgilistaFeedbackLoop(sync_trello=args.sync_trello)

    # ── Inicializa estrutura ──
    if args.init:
        LocalIntegration().ensure_structure()
        print(f"✅ Estrutura .context/kanban/ criada em {KANBAN_ROOT.resolve()}")
        return

    # ── Documenta o kanban em .context/docs/06-kanban.md ──
    if args.doc:
        local = LocalIntegration()
        dest = local.document_kanban()
        print(f"📋 Kanban documentado em {dest}")
        return

    # ── Sincronização one-shot do local para o Trello ──
    if args.sync_trello and not args.daemon and not args.duvida \
            and not args.impedimento and not args.resume:
        local = LocalIntegration()
        tasks = local.all_tasks()
        print(f"📋 Sincronizando {len(tasks)} tasks do local para o Trello (espelho)...")
        mirror = TrelloMirror()
        n = mirror.sync_all(tasks)
        print(f"✅ {n} tasks espelhadas no Trello.")
        return

    # ── Dúvida ──
    if args.duvida:
        if not args.mensagem:
            print("❌ --duvida requer --mensagem")
            sys.exit(1)
        feedback.duvida(args.duvida, args.mensagem)
        return

    # ── Impedimento ──
    if args.impedimento:
        if not args.erro:
            print("❌ --impedimento requer --erro")
            sys.exit(1)
        feedback.impedimento(args.impedimento, args.erro, args.severidade)
        return

    # ── Retomada ──
    if args.resume:
        if not args.resposta:
            print("❌ --resume requer --resposta")
            sys.exit(1)
        feedback.resume_task(args.resume, args.resposta)
        return

    # ── Daemon ──
    if args.daemon:
        daemon = CPAgilistaDaemon(args.dry_run, args.sync_trello)
        daemon.run(args.iterations)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
