# Manutenção do roadmap e da inbox (crewbotics-back)

## Regra de ouro: SEMPRE verificar o estado real contra o código antes de reportar "o que falta"

O `.hermes/roadmap/tasks.md` e os arquivos da `.hermes/inbox/` **costumam ficar
desatualizados em relação ao código**. Antes de responder "o que falta fazer?" ou
"atualize o roadmap", cruze os checkboxes/status com a realidade:

1. **Modelo existe?** `django.apps.apps.get_model("<app>", "<Model>")`.
2. **Endpoint existe?** `grep` por `PasswordResetRequestView`, `dashboard/kpis`, etc.
3. **Teste existe?** `os.path.exists("tests/<app>/test_x.py")`.
4. **Onde vive?** O roadmap pode prever um app/location errado. Ex: ActivityLog estava
   previsto em `utils/models.py`, mas foi implementado em `activity/models.py` (app
   dedicado). Marque a task como feita com uma nota "implementado em <local real>".
5. **Frontend mora em OUTRO repo** (`C:\Users\renat\WebstormProjects\crewbotics-front`).
   Tasks de frontend (páginas /auth/forgot-password, reset-password, link no login)
   NÃO são implementáveis neste repo backend — mantenha-as pendentes e sinalize o repo.

## Convenção inbox → processed

- Features em `.hermes/inbox/features/` e bugs em `.hermes/inbox/bugs/`.
- Quando um item tem status `[Concluído]` (feature) ou `[Corrigido]` (bug), ele deve ser
  MOVIDO para `.hermes/inbox/processed/` (mesmo nome de arquivo, pasta plana).
- Usar **`git mv`** (preserva histórico de rename) para o movimento.
- Itens SEM status explícito (ou status Aberto/Reclassificado) permanecem na pasta ativa.
- Ao mover, o commit mostra só "rename (100%)" — se o arquivo ganhou o status `[Concluído]`
  **no mesmo movimento**, o `git mv` não commita a edição do conteúdo; faça `git add`
  do arquivo depois para incluir a marcação de status no mesmo commit (ou commit separado).
- **Pitfall de staging:** `git mv` já deixa o rename STAGED (status `R`). NÃO rode `git add`
  no caminho ANTIGO (`bugs/...`) — falha com `fatal: pathspec ... did not match any files`.
  Se precisar incluir edição de conteúdo no mesmo commit, `git add` apenas o caminho NOVO
  (`processed/...`) e commite; o rename já está staged.

## Pitfall: ferramentas de escrita mascarando conteúdo

Ao escrever exemplos com campos que parecem secrets (ex: `{ "token": "...", "password": "..." }`),
a ferramenta de escrita/file pode mascarar os valores para `***` no arquivo gravado.
Para placeholders em documentação, use tokens que não pareçam credenciais reais
(ex: `"token": "TOKEN_DO_EMAIL"`, `"password": "NOVA_SENHA"`) e verifique o arquivo
lendo bytes crus (`open(p,"rb").read()`) se suspeitar de masking.

## Marcar feature como Concluída na inbox

Se uma feature foi implementada e mergeada mas o `.md` da inbox não tem `**Status:**`,
adicionar a linha `**Status:** [Concluído]` logo após o bloco de cabeçalho (Data/Origem),
depois `git mv` para processed e commit.

## Pitfall: arquivo de roadmap perdeu conteúdo — reconstruir do histórico git

Sintoma: `.hermes/roadmap/iniciativas.md` (ou tasks.md) tem "buracos" — seções que
viraram só um cabeçalho-resumo (`## INI-01 a INI-13: Fundação do Sistema` sem bullets),
ou números de INI que pulam (INI-44 → INI-61). Isso acontece quando um commit de feature
**substitui** o arquivo inteiro por uma versão resumida em vez de fazer append.

Procedimento de recuperação (não reescrever do zero — o conteúdo existe no git):

1. **Diagnosticar o commit que quebrou:** `git log --oneline --follow -- <arquivo>` e
   comparar o tamanho (`git show <commit>:<arquivo> | wc -c`) entre commits. O commit
   onde o tamanho despenca é o culpado.
2. **Mapear onde cada faixa de INI vive:** o conteúdo detalhado pode estar espalhado por
   VÁRIOS commits históricos, não só o anterior ao que quebrou. Ex.: INI-01..14 num
   commit, INI-15..60 (tabela) noutro, INI-61 no `tasks.md`, INI-62..70 noutro, INI-71..79
   no arquivo atual. Use `git show <commit>:<arquivo>` para extrair cada bloco.
3. **Reconstruir em ordem sequencial:** montar o arquivo novo concatenando os blocos na
   ordem numérica de INI (não na ordem em que aparecem nos commits — o `9e2e8b3` tinha
   INI-66/65 antes de INI-64, o que quebraria a sequência se copiado cru).
4. **Verificar cobertura:** `re.findall(r"INI-(\d+)", txt)` e conferir que a lista de
   números está contígua (INI-01..79). Alguns números podem nunca ter tido seção própria
   (ex: INI-36/38/39 só referenciados em tasks.md) — isso é normal, não é buraco.
5. **Commit em branch própria** (`docs/restaura-<arquivo>-roadmap`), merge com autorização.

Nota: `git log --follow` é essencial — sem `--follow` o git não rastreia o arquivo através
de renames e o histórico parece começar tarde demais.
