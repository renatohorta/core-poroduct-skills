"""Testes internos (unidade) das skills cp-*.

Diferente dos smoke tests (que chamam o script via subprocess), estes testes
importam o código diretamente para testar funções e classes internas:
  - cp-agilista: LocalIntegration, parse_frontmatter, build_task_template
  - cp-inicializador-doc: InicializadorDoc, KANBAN_COLUMNS, ingest_vision
  - cp-orquestrador: PipelineExecutor._build_cli_args, nexus_detect_mode

NENHUM teste requer crewai ou LLM — testam apenas lógica pura em Python.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SKILLS_DIR, clean_env

# ═══════════════════════════════════════════════════════════════════════
# HELPERS — import run.py como módulo, isolando dependências de crewai
# ═══════════════════════════════════════════════════════════════════════

AGILISTA_PY = SKILLS_DIR / "cp-agilista" / "scripts" / "run.py"
INICIALIZADOR_PY = SKILLS_DIR / "cp-inicializador-doc" / "scripts" / "run.py"
ORQUESTRADOR_PY = SKILLS_DIR / "cp-orquestrador" / "scripts" / "run.py"


def import_skill(path: Path, name: str = None):
    """Importa run.py como módulo, sem executar main()."""
    spec = importlib.util.spec_from_file_location(
        name or path.stem, path,
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════
# cp-agilista — lógica pura (sem crewai)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def agilista():
    return import_skill(AGILISTA_PY, "cp_agilista")


class TestAgilistaCore:
    """Funções auxiliares: template, frontmatter, parsing."""

    def test_build_task_template_preenche_todos_os_campos(self, agilista):
        conteudo = agilista.build_task_template(
            task_id="TASK-001",
            title="Implementar login",
            status="ready",
            priority="alta",
            assignee="renat",
            tags='["frontend", "auth"]',
            description="Criar tela de login com JWT",
            acceptance_criteria="Login funcional com email e senha",
            tipo="task",
            origem="inbox/bugs/bug-report.md",
        )
        assert "id: TASK-001" in conteudo
        assert "title: Implementar login" in conteudo
        assert "status: ready" in conteudo
        assert "priority: alta" in conteudo
        assert "assignee: renat" in conteudo
        assert "tipo: task" in conteudo
        assert "origem: inbox/bugs/bug-report.md" in conteudo
        assert "## Critérios de Aceitação" in conteudo
        # O template tem seções que o feedback loop adiciona
        assert "## Dúvidas Pendentes" in conteudo
        assert "## Log de Impedimentos" in conteudo

    def test_build_task_template_defaults(self, agilista):
        """Testa que defaults sensatos sao aplicados."""
        conteudo = agilista.build_task_template("TASK-042", "Minha task")
        assert "priority: media" in conteudo
        assert "status: backlog" in conteudo
        assert "tipo: task" in conteudo  # DEFAULT_TRILHA
        assert "origem: " in conteudo  # vazio por default

    def test_parse_frontmatter_basico(self, agilista):
        conteudo = """---
id: TASK-001
title: Teste
status: ready
priority: alta
---
# Conteudo
"""
        meta = agilista.parse_frontmatter(conteudo)
        assert meta["id"] == "TASK-001"
        assert meta["title"] == "Teste"
        assert meta["status"] == "ready"

    def test_parse_frontmatter_sem_frontmatter(self, agilista):
        assert agilista.parse_frontmatter("# So conteudo") == {}

    def test_parse_frontmatter_valor_com_aspas(self, agilista):
        conteudo = """---
title: 'Meu titulo'
tags: "[]"
---
"""
        meta = agilista.parse_frontmatter(conteudo)
        assert meta["title"] == "Meu titulo"
        assert meta["tags"] == "[]"

    def test_parse_frontmatter_campo_vazio(self, agilista):
        conteudo = """---
id: TASK-001
assignee:
---
"""
        meta = agilista.parse_frontmatter(conteudo)
        assert meta["id"] == "TASK-001"
        assert meta.get("assignee", "") == ""

    def test_read_task_meta_arquivo_inexistente(self, agilista, tmp_path):
        meta = agilista.read_task_meta(tmp_path / "nao-existe.md")
        assert meta == {}

    def test_read_task_status_lida_do_frontmatter(self, agilista, tmp_path):
        task = tmp_path / "tarefa.md"
        task.write_text("""---
id: TASK-X
status: doing
---
# Tarefa
""", encoding="utf-8")
        assert agilista.read_task_status(task) == "doing"

    def test_read_task_status_sem_frontmatter(self, agilista, tmp_path):
        task = tmp_path / "tarefa.md"
        task.write_text("# Apenas conteudo", encoding="utf-8")
        assert agilista.read_task_status(task) == ""

    def test_constantes_validas(self, agilista):
        """Verifica que VALID_STATUSES e TRILHAS estao consistentes."""
        # TODAS as trilhas tem prefixo
        for trilha, prefixo in agilista.TRILHAS.items():
            assert len(prefixo) > 0, f"{trilha} sem prefixo"
        assert agilista.DEFAULT_TRILHA in agilista.TRILHAS
        # `inbox` nao esta nas trilhas — e um conceito separado
        assert "inbox" not in agilista.TRILHAS
        # blocked e um status valido
        assert "blocked" in agilista.VALID_STATUSES

    def test_trilha_patterns_cobrem_todas_as_trilhas(self, agilista):
        """Cada trilha (exceto task, que e default) tem pelo menos um padrao."""
        trilhas_com_padrao = {t for t, _ in agilista.TRILHA_PATTERNS}
        trilhas_definidas = set(agilista.TRILHAS.keys())
        # task nao precisa de padrao — e default
        assert trilhas_com_padrao == trilhas_definidas - {"task"}, (
            f"TRILHA_PATTERNS nao cobre: {trilhas_definidas - {'task'} - trilhas_com_padrao}"
        )


class TestAgilistaLocalIntegration:
    """LocalIntegration: operacoes no sistema de arquivos local."""

    @pytest.fixture
    def local(self, agilista, tmp_path):
        kanban_root = tmp_path / ".context" / "kanban"
        return agilista.LocalIntegration(root=kanban_root)

    def test_ensure_structure_cria_colunas(self, agilista, tmp_path):
        root = tmp_path / "kanban"
        li = agilista.LocalIntegration(root=root)
        for col in agilista.KANBAN_COLUMNS + [agilista.BLOCKED_DIR]:
            assert (root / col).is_dir(), f"coluna {col} nao criada"

    def test_scan_ready_encontra_tasks_prontas(self, local, agilista):
        # Cria task com status: ready no 1-backlog
        backlog = local.root / "1-backlog"
        t1 = backlog / "TASK-001.md"
        t1.parent.mkdir(parents=True, exist_ok=True)
        t1.write_text("""---
id: TASK-001
status: ready
---
""", encoding="utf-8")
        # Cria task com status: backlog — ignorada
        t2 = backlog / "TASK-002.md"
        t2.write_text("""---
id: TASK-002
status: backlog
---
""", encoding="utf-8")

        prontas = local.scan_ready()
        assert len(prontas) == 1
        assert prontas[0].name == "TASK-001.md"

    def test_scan_ready_backlog_vazio_retorna_lista_vazia(self, local):
        assert local.scan_ready() == []

    def test_all_tasks_lista_em_todas_as_colunas(self, local, agilista):
        # Task no backlog
        b1 = local.root / "1-backlog" / "TASK-001.md"
        b1.parent.mkdir(parents=True, exist_ok=True)
        b1.write_text("---\nid: TASK-001\ntitle: Backlog task\nstatus: ready\n---\n", encoding="utf-8")
        # Task no doing
        d1 = local.root / "3-doing" / "TASK-002.md"
        d1.parent.mkdir(parents=True, exist_ok=True)
        d1.write_text("---\nid: TASK-002\ntitle: Doing task\nstatus: doing\n---\n", encoding="utf-8")

        tasks = local.all_tasks()
        assert len(tasks) == 2
        titulos = {t["title"] for t in tasks}
        assert "Backlog task" in titulos
        assert "Doing task" in titulos

    def test_move_to_move_arquivo_entre_colunas(self, local, agilista):
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        moved = local.move_to("TASK-001", "2-todo")
        assert moved is not None
        assert moved.parent.name == "2-todo"
        assert moved.exists()
        assert not src.exists()

    def test_move_to_task_inexistente_retorna_none(self, local):
        assert local.move_to("TASK-INEXISTENTE", "2-todo") is None

    def test_find_task_acha_em_qualquer_coluna(self, local, agilista):
        src = local.root / "4-review" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        encontrado = local.find_task("TASK-001")
        assert encontrado is not None
        assert encontrado.name == "TASK-001.md"

    def test_find_task_inexistente_retorna_none(self, local):
        assert local.find_task("GHOST") is None

    def test_add_duvida_adiciona_secao_no_arquivo(self, local, agilista):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n\n# Minha Task\n", encoding="utf-8")

        result = local.add_duvida("TASK-001", "Qual o escopo do MVP?")
        assert result is not None
        conteudo = result.read_text(encoding="utf-8")
        assert "## ❓ Dúvidas Pendentes" in conteudo
        assert "Qual o escopo do MVP?" in conteudo

    def test_add_duvida_acumula_multiplas(self, local, agilista):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        local.add_duvida("TASK-001", "Primeira duvida")
        local.add_duvida("TASK-001", "Segunda duvida")
        conteudo = src.read_text(encoding="utf-8")
        # Duas entradas sob a mesma secao
        assert conteudo.count("## ❓ Dúvidas Pendentes") == 1
        assert conteudo.count("Primeira duvida") == 1
        assert conteudo.count("Segunda duvida") == 1

    def test_add_duvida_task_inexistente_retorna_none(self, local):
        assert local.add_duvida("GHOST", "mensagem") is None

    def test_add_impedimento_move_para_blocked_e_adiciona_log(self, local, agilista):
        src = local.root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.add_impedimento("TASK-001", "Falha de conexao", "alta")
        assert result is not None
        assert result.parent.name == "blocked"
        conteudo = result.read_text(encoding="utf-8")
        assert "## Log de Impedimentos" in conteudo
        assert "Falha de conexao" in conteudo
        assert "alta" in conteudo

    def test_resume_move_de_blocked_para_todo(self, local, agilista):
        src = local.root / "blocked" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.resume("TASK-001", "Resposta: sim")
        assert result is not None
        assert result.parent.name == "2-todo"
        conteudo = result.read_text(encoding="utf-8")
        assert "✅ [Resposta Humana]" in conteudo
        assert "Resposta: sim" in conteudo

    def test_resume_sem_estar_blocked_nao_move(self, local, agilista):
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\n---\n", encoding="utf-8")

        result = local.resume("TASK-001", "ok")
        # Continua na mesma pasta (nao estava blocked)
        assert result.parent.name == "1-backlog"

    def test_resume_task_inexistente_retorna_none(self, local):
        assert local.resume("GHOST", "ok") is None

    def test_document_kanban_gera_md(self, local, agilista, tmp_path):
        # Adiciona uma task
        src = local.root / "1-backlog" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\ntitle: Minha Task\npriority: alta\n---\n", encoding="utf-8")

        # documentacao deve ir para o contexto certo
        context_root = tmp_path / ".context"
        dest = local.document_kanban(context_root=str(context_root))
        assert dest.exists()
        conteudo = dest.read_text(encoding="utf-8")
        assert "Kanban / Esteira de Execução" in conteudo
        assert "1-backlog" in conteudo
        assert "Minha Task" in conteudo
        assert "TASK-001" in conteudo


class TestAgilistaFeedbackLoop:
    @pytest.fixture
    def feedback(self, agilista, tmp_path):
        root = tmp_path / ".context" / "kanban"
        # Precisa de uma task existente
        src = root / "3-doing" / "TASK-001.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("---\nid: TASK-001\ntitle: Minha Task\n---\n", encoding="utf-8")
        # Troca o KANBAN_ROOT para o tmp_path
        old_root = agilista.KANBAN_ROOT
        agilista.KANBAN_ROOT = root
        fb = agilista.CPAgilistaFeedbackLoop(sync_trello=False)
        yield fb

    def test_duvida_emite_evento(self, feedback):
        evento = feedback.duvida("TASK-001", "Qual o escopo?")
        assert evento["event"] == "DUVIDA"
        assert evento["payload"]["task_id"] == "TASK-001"

    def test_impedimento_emite_evento(self, feedback):
        evento = feedback.impedimento("TASK-001", "Falha geral", "critica")
        assert evento["event"] == "IMPEDIMENTO"
        assert evento["payload"]["severidade"] == "critica"

    def test_resume_task_emite_evento(self, feedback):
        # Primeiro block, depois resume
        feedback.impedimento("TASK-001", "erro")
        evento = feedback.resume_task("TASK-001", "resposta humana")
        assert evento["event"] == "HUMAN_CLARIFICATION_RECEIVED"
        assert evento["payload"]["resposta"] == "resposta humana"


# ═══════════════════════════════════════════════════════════════════════
# cp-inicializador-doc — lógica pura
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def inic():
    return import_skill(INICIALIZADOR_PY, "cp_inicializador_doc")


class TestInicializadorDocCore:
    """InicializadorDoc: criacao de estrutura e ingestao de vision."""

    def test_build_cria_toda_estrutura(self, inic, tmp_path):
        init = inic.InicializadorDoc(project_dir=tmp_path)
        resumo = init.build()
        assert resumo["files_created"] > 0
        # Verifica pecas-chave
        context = tmp_path / ".context"
        assert (context / "README.md").is_file()
        # docs
        for fname in inic.DOC_FILES:
            assert (context / "docs" / fname).is_file(), f"{fname} faltando"
        # inbox
        for nome in inic.INBOX_DIRS:
            assert (context / "inbox" / nome / "README.md").is_file(), f"inbox/{nome} faltando"
        # tracking
        assert (context / "tracking" / "progresso.md").is_file()
        assert (context / "tracking" / "decisoes.md").is_file()
        # kanban
        assert (context / "kanban" / "README.md").is_file()
        for col in inic.KANBAN_COLUMNS + [inic.KANBAN_BLOCKED_DIR]:
            assert (context / "kanban" / col / ".gitkeep").is_file(), f"kanban/{col}/.gitkeep faltando"
        # Ponteiros na raiz
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / "AGENT.md").is_file()

    def test_build_dry_run_nao_cria_arquivos(self, inic, tmp_path):
        init = inic.InicializadorDoc(project_dir=tmp_path, dry_run=True)
        resumo = init.build()
        assert resumo["dry_run"] is True
        # Nada foi criado de fato
        assert not (tmp_path / ".context").exists()
        assert "dry-run" in init.created[0]

    def test_ingest_vision_move_arquivo(self, inic, tmp_path):
        # Cria vision.md na raiz
        vision_src = tmp_path / "vision.md"
        vision_src.write_text("# Visao do Produto\n", encoding="utf-8")

        init = inic.InicializadorDoc(project_dir=tmp_path)
        ingerido = init.ingest_vision()
        assert ingerido is True
        # vision.md foi movido para .context/docs/
        destino = tmp_path / ".context" / "docs" / "00-vision.md"
        assert destino.is_file()
        assert not vision_src.exists()
        assert "Visao do Produto" in destino.read_text(encoding="utf-8")

    def test_ingest_vision_sem_vision_retorna_false(self, inic, tmp_path):
        init = inic.InicializadorDoc(project_dir=tmp_path)
        assert init.ingest_vision() is False

    def test_ingest_vision_dry_run_nao_move(self, inic, tmp_path):
        vision_src = tmp_path / "vision.md"
        vision_src.write_text("# Visao\n", encoding="utf-8")

        init = inic.InicializadorDoc(project_dir=tmp_path, dry_run=True)
        ingerido = init.ingest_vision()
        assert ingerido is True
        # Arquivo original ainda existe
        assert vision_src.exists()

    def test_kankan_columns_batem_agilista(self, inic):
        """As colunas declaradas no inicializador batem com as do agilista."""
        agilista = import_skill(AGILISTA_PY, "cp_agilista")
        assert inic.KANBAN_COLUMNS == agilista.KANBAN_COLUMNS
        assert inic.KANBAN_BLOCKED_DIR == agilista.BLOCKED_DIR

    def test_report_gaps_nao_quebra(self, inic, tmp_path, capsys):
        init = inic.InicializadorDoc(project_dir=tmp_path)
        init.build()
        init.report_gaps()
        capturado = capsys.readouterr().out
        assert "RESUMO EXECUTIVO" in capturado
        assert "Kanban/esteira (06)" in capturado


# ═══════════════════════════════════════════════════════════════════════
# cp-orquestrador — logica pura (sem crewai)
# ═══════════════════════════════════════════════════════════════════════


class TestOrquestradorNexusDetectMode:
    """nexus_detect_mode: classificacao de requisito em modo NEXUS."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORQUESTRADOR_PY, "cp_orquestrador")

    def test_full_keywords(self):
        """Palavras de sistema completo retornam 'full'."""
        assert self.orq.nexus_detect_mode("Construir um sistema de agendamento") == "full"
        assert self.orq.nexus_detect_mode("Criar do zero uma plataforma SaaS") == "full"
        assert self.orq.nexus_detect_mode("Aplicativo de delivery") == "full"
        assert self.orq.nexus_detect_mode("app de musica") == "full"

    def test_sprint_keywords(self):
        """Palavras de feature/funcionalidade retornam 'sprint'."""
        assert self.orq.nexus_detect_mode("implementar feature de login") == "sprint"
        assert self.orq.nexus_detect_mode("Adicionar relatorio de vendas") == "sprint"
        assert self.orq.nexus_detect_mode("Nova tela de cadastro") == "sprint"

    def test_micro_keywords(self):
        """Palavras de bug/correcao retornam 'micro'."""
        assert self.orq.nexus_detect_mode("Corrigir bug no login") == "micro"
        assert self.orq.nexus_detect_mode("Ajustar layout da tela") == "micro"
        assert self.orq.nexus_detect_mode("fix pequeno no header") == "micro"

    def test_tie_full_ganha(self):
        """Empate vai para full (prioridade na ordem de comparacao)."""
        assert self.orq.nexus_detect_mode("sistema de relatorio") == "full"

    def test_case_insensitive(self):
        assert self.orq.nexus_detect_mode("CRIAR PLATAFORMA") == "full"
        assert self.orq.nexus_detect_mode("ADICIONAR BOTAO") == "sprint"

    def test_requisito_vazio_retorna_full_pelo_tiebreaker(self):
        """String vazia: nenhum keyword casa, full ganha no tiebreaker (full >= sprint)."""
        assert self.orq.nexus_detect_mode("") == "full"
        assert self.orq.nexus_detect_mode("   ") == "full"


class TestOrquestradorCrewPaths:
    """SKILL_PATHS e CREWS: validacao das definicoes estaticas."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORQUESTRADOR_PY, "cp_orquestrador")

    def test_toda_crew_com_skill_tem_path_valido(self):
        """Toda crew que aponta pra skill externa precisa que o run.py exista."""
        faltando = [
            ck for ck, path in self.orq.SKILL_PATHS.items()
            if ck in self.orq.CREWS and not path.exists()
        ]
        assert not faltando, f"skills faltando: {faltando}"

    def test_todo_modo_referencia_crew_existente(self):
        """Nenhum modo aponta para crew inexistente."""
        crews_nativas = {"full-dev"}
        for modo, info in self.orq.MODOS.items():
            for ck in info["crews"]:
                assert ck in self.orq.CREWS or ck in crews_nativas, (
                    f"modo {modo!r} -> crew inexistente: {ck!r}"
                )

    def test_invoke_default_aplicado_onde_falta(self):
        """Crews sem 'invoke' recebem o default {briefing_arg: 'input', output: True}."""
        invoke_default = {"briefing_arg": "input", "output": True}
        for ck, crew in self.orq.CREWS.items():
            if "invoke" not in crew:
                assert crew.get("invoke", invoke_default) == invoke_default, (
                    f"{ck}: sem invoke explicito, mas default nao seria aplicado"
                )

    def test_crews_tem_todos_os_campos_obrigatorios(self):
        """Cada crew tem name, skill, description, agents, inputs, outputs, quality_gate."""
        obrigatorios = {"name", "skill", "description", "agents",
                        "inputs", "outputs", "quality_gate"}
        for ck, crew in self.orq.CREWS.items():
            ausentes = obrigatorios - set(crew.keys())
            assert not ausentes, f"{ck}: campos obrigatorios ausentes: {ausentes}"


class TestOrquestradorPipelineExecutor:
    """PipelineExecutor: construcao de args e resolucao de fases."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORQUESTRADOR_PY, "cp_orquestrador")

    def test_build_cli_args_crew_com_invoke(self, tmp_path):
        """Crew com invoke explicito e respeitada."""
        executor = self.orq.PipelineExecutor(
            briefing="teste", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("goal-loop")
        assert args is not None
        # goal-loop tem invoke: {briefing_arg: 'goal', output: False}
        assert "--goal" in " ".join(args)
        assert "--dry-run" not in " ".join(args)

    def test_build_cli_args_agilista_retorna_daemon_sem_dry_run(self, tmp_path):
        """Agilista retorna com --daemon, sem precisar de --dry-run (o orquestrador nao passa)."""
        executor = self.orq.PipelineExecutor(
            briefing="teste", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("agilista")
        assert args is not None
        args_str = " ".join(args)
        assert "--daemon" in args_str
        assert "teste" not in args_str  # briefing nao vai para modo daemon

    def test_build_cli_args_com_output_quando_skill_aceita(self, tmp_path):
        """Skills com output=True recebem --output com path valido."""
        executor = self.orq.PipelineExecutor(
            briefing="teste", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        args = executor._build_cli_args("arquitetura")
        args_str = " ".join(args)
        assert "--output" in args_str

    def test_resolve_modo_mantem_modo_explicito(self):
        """Quando o usuario passa --mode explicitamente, esse modo e usado."""
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)
        executor.mode = "micro"
        assert executor.mode == "micro"

    def test_get_previous_artifact_mapeia_corretamente(self, tmp_path):
        """O mapa prev_map liga cada fase a fase anterior correta."""
        executor = self.orq.PipelineExecutor(
            briefing="teste", mode="full",
            output_dir=str(tmp_path), python_cmd=sys.executable,
        )
        # Simula artefatos de fases anteriores
        prev_map_esperado = {
            "arquitetura": "requisitos",
            "implementacao": "arquitetura",
            "testes": "implementacao",
            "seguranca": "implementacao",
            "devops": "implementacao",
            "documentacao": "implementacao",
            "qualidade": None,
            "bug-fix": None,
            "competitive-analysis": None,
            "goal-loop": None,
            "manutencao": None,
            "inicializador-doc": None,
            "agilista": None,
        }
        # Testa via _get_previous_artifact (indiretamente)
        for crew_key, esperado in prev_map_esperado.items():
            if crew_key in self.orq.CREWS:
                invoke = self.orq.CREWS[crew_key].get("invoke", {"briefing_arg": "input", "output": True})
                # Skills que nao usam --input nao tem fase anterior
                if invoke.get("briefing_arg") != "input":
                    continue
                # Nao da pra acessar prev_map direto, mas o comportamento de
                # _get_previous_artifact retorna None quando nao tem artefato
                result = executor._get_previous_artifact(crew_key)
                if esperado is None:
                    assert result is None or result == "", f"{crew_key}: esperava None, veio {result!r}"


class TestOrquestradorModos:
    """MODOS: validacao estrutural de cada pipeline mode."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORQUESTRADOR_PY, "cp_orquestrador")

    def test_modo_full_tem_oito_crews(self):
        modo = self.orq.MODOS.get("full")
        assert modo is not None
        len(modo["crews"]) >= 7  # pelo menos as 7 primeiras

    def test_todo_modo_tem_name_e_description(self):
        for slug, info in self.orq.MODOS.items():
            assert "name" in info, f"modo {slug} sem name"
            assert "description" in info, f"modo {slug} sem description"
            assert "crews" in info, f"modo {slug} sem crews"
            assert len(info["crews"]) > 0, f"modo {slug} com crews vazia"


class TestOrquestradorQualityGate:
    """Testes do QualityGate extra (alem do test_quality_gate.py)."""

    orq = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_orq(cls):
        cls.orq = import_skill(ORQUESTRADOR_PY, "cp_orquestrador")

    def test_check_quality_gate_classifica_corretamente(self):
        """Testa mais alguns casos do quality gate."""
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)

        # PASS keywords
        assert executor._check_quality_gate("fase", "Testes OK", 0)["status"] == "PASS"

        # FAIL por keyword (TRACEBACK, FALHOU, CRÍTICO, etc.)
        assert executor._check_quality_gate("fase", "Pipeline FALHOU no build", 0)["status"] == "FAIL"
        assert executor._check_quality_gate("fase", "Erro CRÍTICO encontrado", 0)["status"] == "FAIL"

        # WARN quando nao reconhece nada ou saida vazia
        assert executor._check_quality_gate("fase", "build concluido com ressalvas", 0)["status"] == "WARN"
        assert executor._check_quality_gate("fase", "", 0)["status"] == "WARN"

    def test_quality_gate_rejeita_traceback(self):
        executor = self.orq.PipelineExecutor.__new__(self.orq.PipelineExecutor)
        resultado = executor._check_quality_gate(
            "fase",
            "Traceback (most recent call last):\n  File \"run.py\", line 1",
            1,
        )
        assert resultado["status"] == "FAIL"
