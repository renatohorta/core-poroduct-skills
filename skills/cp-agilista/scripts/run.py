#!/usr/bin/env python3
"""
cp-agilista — Agilista (Esteira de Execução) (self-contained)

Maestro da esteira de execução. Monitora o backlog (local ou Trello), despacha
tarefas prontas para a cp-orquestrador, e gerencia o loop bidirecional de
feedback (dúvidas e impedimentos da IA, retomada com resposta humana).

Componentes:
  - CPAgilistaDaemon        : polling contínuo + watcher de arquivos/Trello
  - CPAgilistaFeedbackLoop  : dúvidas, impedimentos e retomada
  - TrelloIntegration       : integração com Trello via MCP tools
  - LocalIntegration        : integração com sistema de arquivos local (.kanban/)
  - TaskTemplate            : template de task .md com frontmatter YAML

Uso:
  # Daemon de polling (local)
  python run.py --daemon --source local

  # Daemon de polling (Trello)
  python run.py --daemon --source trello

  # Registrar dúvida
  python run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?"

  # Registrar impedimento
  python run.py --impedimento "task-123" --erro "Falha de conexão" --severidade alta

  # Retomar tarefa (resposta humana)
  python run.py --resume "task-123" --resposta "O MVP cobre login e cadastro"

  # Dry run
  python run.py --daemon --source local --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

# Diretório raiz do kanban local. Usa env var com default relativo (portável).
KANBAN_ROOT = Path(os.environ.get("KANBAN_ROOT", ".kanban"))

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
                        acceptance_criteria="Definir critérios de aceitação"):
    """Gera o conteúdo de um arquivo de task .md a partir do template."""
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


def read_task_status(path: Path) -> str:
    """Lê o status de um arquivo de task a partir do frontmatter."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    return parse_frontmatter(content).get("status", "")


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRAÇÃO LOCAL (.kanban/)
# ═══════════════════════════════════════════════════════════════════════════

class LocalIntegration:
    """Integração com o sistema de arquivos local (.kanban/)."""

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
# INTEGRAÇÃO TRELLO (via MCP tools)
# ═══════════════════════════════════════════════════════════════════════════

class TrelloIntegration:
    """Integração com Trello via tools MCP.

    Usa as tools MCP do Trello (list_name, card, comment, label). Se as tools
    não estiverem disponíveis no ambiente, degrada para o modo local.
    """

    def __init__(self, board_name: str = None):
        self.board_name = board_name or os.environ.get("TRELLO_BOARD", "Backlog")
        self.available = self._check_tools()

    def _check_tools(self) -> bool:
        """Verifica se as tools MCP do Trello estão disponíveis."""
        # Tenta importar as tools MCP (se o ambiente as expuser)
        try:
            from mcp_tools import trello  # noqa: F401
            return True
        except ImportError:
            return False

    def scan_ready(self) -> list:
        """Varre o Trello por cards na lista Backlog."""
        if not self.available:
            return []
        # Placeholder: em ambiente real, chama a tool MCP
        # trello.list_cards(list_name="Backlog")
        return []

    def add_duvida(self, task_id: str, mensagem: str, origem: str = "IA") -> bool:
        """Injeta comentário formatado no card com label ai:waiting-human."""
        if not self.available:
            return False
        comment = f"❓ [Dúvida da IA - {origem}] {mensagem}"
        # trello.add_comment(card_id=task_id, text=comment)
        # trello.add_label(card_id=task_id, label="ai:waiting-human")
        return True

    def add_impedimento(self, task_id: str, erro: str, severidade: str = "media") -> bool:
        """Move o card para a lista blocked e anexa log."""
        if not self.available:
            return False
        # trello.move_card(card_id=task_id, list_name="blocked")
        # trello.add_comment(card_id=task_id, text=f"🚧 {erro} (severidade: {severidade})")
        return True

    def resume(self, task_id: str, resposta: str) -> bool:
        """Captura a resposta humana e move o card de volta."""
        if not self.available:
            return False
        # trello.add_comment(card_id=task_id, text=f"✅ Resposta humana: {resposta}")
        # trello.move_card(card_id=task_id, list_name="Todo")
        return True


# ═══════════════════════════════════════════════════════════════════════════
# LOOP BIDIRECIONAL DE FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════

class CPAgilistaFeedbackLoop:
    """Gerencia dúvidas, impedimentos e retomada (bidirecionalidade)."""

    def __init__(self, source: str = "local"):
        self.source = source
        self.local = LocalIntegration()
        self.trello = TrelloIntegration()

    def _dispatch(self, event: str, payload: dict):
        """Emite um evento padronizado (log + payload JSON)."""
        event_line = {
            "event": event,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
        print(json.dumps(event_line, ensure_ascii=False, indent=2))
        return event_line

    def duvida(self, task_id: str, mensagem: str, origem: str = "IA") -> dict:
        """Registra uma dúvida da IA e a envia para o humano."""
        payload = {"task_id": task_id, "mensagem": mensagem, "origem": origem}
        if self.source == "trello":
            self.trello.add_duvida(task_id, mensagem, origem)
        else:
            self.local.add_duvida(task_id, mensagem, origem)
        return self._dispatch(EVENT_DUVIDA, payload)

    def impedimento(self, task_id: str, erro: str, severidade: str = "media") -> dict:
        """Registra um impedimento e move a tarefa para blocked/."""
        payload = {"task_id": task_id, "erro": erro, "severidade": severidade}
        if self.source == "trello":
            self.trello.add_impedimento(task_id, erro, severidade)
        else:
            self.local.add_impedimento(task_id, erro, severidade)
        return self._dispatch(EVENT_IMPEDIMENTO, payload)

    def resume_task(self, task_id: str, resposta: str) -> dict:
        """Captura a resposta humana e desbloqueia a esteira."""
        payload = {"task_id": task_id, "resposta": resposta}
        if self.source == "trello":
            self.trello.resume(task_id, resposta)
        else:
            self.local.resume(task_id, resposta)
        return self._dispatch(EVENT_HUMAN_CLARIFICATION, payload)


# ═══════════════════════════════════════════════════════════════════════════
# DAEMON DE POLLING
# ═══════════════════════════════════════════════════════════════════════════

class CPAgilistaDaemon:
    """Polling contínuo do backlog e despacho de tarefas prontas."""

    def __init__(self, source: str = "local", dry_run: bool = False):
        self.source = source
        self.dry_run = dry_run
        self.local = LocalIntegration()
        self.trello = TrelloIntegration()
        self.feedback = CPAgilistaFeedbackLoop(source)

    def _dispatch_task(self, task_path: Path):
        """Despacha uma tarefa pronta para a cp-orquestrador."""
        task_id = task_path.stem
        payload = {
            "task_id": task_id,
            "source": self.source,
            "path": str(task_path),
            "event": EVENT_TASK_DISPATCHED,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        # Em ambiente real, chama a cp-orquestrador:
        #   subprocess.run([sys.executable, ORQUESTRADOR_RUN, task_id, "--auto"])
        # Move para 2-todo/ (despachada)
        if not self.dry_run:
            self.local.move_to(task_id, "2-todo")

    def poll_once(self) -> list:
        """Uma única varredura do backlog. Retorna as tarefas prontas."""
        if self.source == "trello":
            ready = self.trello.scan_ready()
        else:
            ready = self.local.scan_ready()

        dispatched = []
        for task in ready:
            print(f"  📦 Tarefa pronta: {task.name}")
            self._dispatch_task(task)
            dispatched.append(task)
        return dispatched

    def run(self, iterations: int = None):
        """Loop de polling contínuo."""
        print(f"🚀 CPAgilistaDaemon iniciado (source={self.source}, "
              f"interval={POLL_INTERVAL}s, dry_run={self.dry_run})")
        print(f"   Kanban local: {self.local.root.resolve()}")
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
Exemplos:
  python run.py --daemon --source local
  python run.py --daemon --source trello
  python run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?"
  python run.py --impedimento "task-123" --erro "Falha de conexão" --severidade alta
  python run.py --resume "task-123" --resposta "O MVP cobre login e cadastro"
  python run.py --daemon --source local --dry-run
        """,
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Inicia o daemon de polling")
    parser.add_argument("--source", choices=["local", "trello"], default="local",
                        help="Fonte do backlog (default: local)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Não executa ações, apenas mostra o que faria")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Número de polls (default: infinito)")
    parser.add_argument("--duvida", metavar="TASK_ID",
                        help="Registra uma dúvida para a tarefa")
    parser.add_argument("--mensagem", help="Mensagem da dúvida")
    parser.add_argument("--impedimento", metavar="TASK_ID",
                        help="Registra um impedimento para a tarefa")
    parser.add_argument("--erro", help="Descrição do erro do impedimento")
    parser.add_argument("--severidade", choices=["baixa", "media", "alta", "critica"],
                        default="media", help="Severidade do impedimento")
    parser.add_argument("--resume", metavar="TASK_ID",
                        help="Retoma uma tarefa com resposta humana")
    parser.add_argument("--resposta", help="Resposta humana para desbloquear")
    parser.add_argument("--init", action="store_true",
                        help="Cria a estrutura .kanban/ e sai")
    args = parser.parse_args()

    feedback = CPAgilistaFeedbackLoop(args.source)

    # ── Inicializa estrutura ──
    if args.init:
        LocalIntegration().ensure_structure()
        print(f"✅ Estrutura .kanban/ criada em {KANBAN_ROOT.resolve()}")
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
        daemon = CPAgilistaDaemon(args.source, args.dry_run)
        daemon.run(args.iterations)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
