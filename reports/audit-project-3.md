================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, SQLite)
Files:   15 analyzed | ~969 lines of code (1158 lines)
Grade:   B — camadas parciais (models/routes/services/utils existem; regra, validação, consulta e serialização ficam nas rotas)

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 9 | LOW: 6 | Total: 24

## Findings

### [CRITICAL] #1 Autenticação falsa e nenhuma autorização: qualquer pessoa vira admin ou toma contas (AP06)
File: routes/user_routes.py:52, 71-78, 92-125, 134-151, 207-211; routes/report_routes.py:211-223; models/user.py:34-38
Description: `/login` devolve um token previsível (`fake-jwt-token-<id>`) que nenhuma rota confere. `POST /users` aceita `role` do corpo; `PUT /users/<id>` aceita `role`, `active`, `email` e `password` de qualquer usuário sem credencial; `DELETE /users/<id>` e `DELETE /categories/<id>` são anônimos. `User.is_admin()` existe e nunca é chamado.
Impact: escalada de privilégio (criar admin, promover-se), tomada de conta (trocar a senha do admin e logar como ele), exclusão de usuários com todas as suas tasks por qualquer cliente.
Evidence: sondas do baseline — `sonda-cria-admin-anonimo` 201, `sonda-promove-sem-auth` 200, `sonda-troca-senha-de-outro` 200 (senha do usuário 1 trocada), `sonda-exclui-categoria-anonimo` 200, `sonda-exclui-usuario-anonimo` 200; `login` devolve `"token":"fake-jwt-token-4"`.
Recommendation: token assinado e com validade (itsdangerous, já vem com o Flask) emitido no login; middleware `auth` com `require_auth`/`require_admin`; `PUT /users/<id>` exige o próprio usuário ou admin; `role`/`active` e role diferente de `user` na criação exigem admin; `DELETE /users` e `DELETE /categories` exigem admin. (playbook T13)

### [CRITICAL] #2 Senha com MD5 sem salt e hash devolvido pela API (AP05)
File: models/user.py:21 (to_dict), 27-32 (set_password/check_password)
Description: `set_password` grava `md5(senha)` sem salt; `to_dict()` inclui o campo `password`, usado em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login`.
Impact: qualquer cliente lê o hash de qualquer usuário; MD5 sem salt cai com tabela pronta, entregando as senhas.
Evidence: baseline `obter-usuario` e `login` — corpo com `password` de 32 caracteres hexadecimais (valor não reproduzido).
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash`; aceitar hash MD5 legado só para migrar no próximo login; remover `password` da serialização. (playbook T3)

### [CRITICAL] #3 Credenciais e chave no código (AP03)
File: app.py:13 (`SECRET_KEY`); services/notification_service.py:7-10 (`email_user`, `email_password`); seed.py:19, 26, 33 (senhas dos usuários de seed)
Description: a chave da aplicação e a credencial SMTP estão literais no código versionado; o seed grava senhas literais.
Impact: quem lê o repositório tem a credencial do e-mail e a chave que vai assinar tokens (achado #1).
Evidence: `scan_signals.py` (hardcoded-secret ×3) e leitura. Valores não reproduzidos.
Recommendation: `SECRET_KEY` e `SMTP_*` lidos do ambiente (`.env.example` sem valores); sem `SECRET_KEY`, gerar chave aleatória por processo e avisar no log. As senhas do seed são fixture de desenvolvimento: passam a vir de `SEED_PASSWORD` (com padrão de dev documentado). (playbook T2)

### [CRITICAL] #4 Rotas acumulam todas as camadas (AP21)
File: routes/task_routes.py:11-299, routes/user_routes.py:10-211, routes/report_routes.py:12-223
Description: cada handler lê a requisição, valida, consulta o banco, aplica a regra e monta o JSON à mão; não há controllers. `report_routes.py` mistura dois domínios (relatórios e CRUD de categorias).
Impact: nenhuma regra pode ser testada sem HTTP e banco; qualquer mudança de regra exige editar várias rotas (ver #7 e #15).
Evidence: confirmado por leitura (733 linhas de rotas, 0 controllers).
Recommendation: views (blueprints finos) → controllers (orquestração) → models (regra e serialização); categorias em blueprint próprio. (playbook T4)

### [HIGH] #5 Debug ligado e servidor em todas as interfaces (AP04)
File: app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` no entry point documentado (`python app.py`).
Impact: o debugger do Werkzeug executa código Python no servidor e fica acessível na rede; stack traces vazam estrutura interna.
Evidence: `scan_signals.py` (debug-on, bind-all) e leitura.
Recommendation: `FLASK_DEBUG`, `HOST` (padrão 127.0.0.1) e `PORT` vindos do ambiente. (playbook T2)

### [HIGH] #6 Chave estrangeira gravada sem existir (AP24)
File: routes/task_routes.py:186-198 (também 116-124)
Description: `user_id`/`category_id` só são conferidos quando "verdadeiros"; `0` pula a checagem e é gravado. O SQLite roda sem `PRAGMA foreign_keys`.
Impact: task fica apontando para usuário/categoria inexistente; some dos relatórios por usuário e da contagem por categoria.
Evidence: sonda `sonda-update-categoria-zero` — 200 com `"category_id":0` gravado. (Exclusão de categoria NÃO gera órfão: o relacionamento anula o FK — `task-apos-excluir-categoria` volta com `category_id: null`; hipótese descartada.)
Recommendation: checar `is not None` e buscar a entidade; 404 se não existir. (playbook T6/T7)

### [HIGH] #7 Regra de negócio nas rotas e métodos de domínio ignorados (AP22)
File: routes/task_routes.py:30-39, 71-80, 110-114, 176-184, 275-296; routes/user_routes.py:61-72, 105-122, 171-180; routes/report_routes.py:19-68, 119-151; models/task.py:38-60 e models/user.py:34-38 (não usados)
Description: atraso, taxa de conclusão, validação de status/prioridade/role e unicidade de e-mail são decididos nos handlers, enquanto `Task.is_overdue`, `validate_status`, `validate_priority` e `User.is_admin` existem e não são chamados.
Impact: a regra diverge entre rotas (ex.: `/users/<id>/tasks` serializa campos diferentes de `/tasks`), e não há onde testá-la.
Evidence: confirmado por leitura.
Recommendation: regra no model (`Task.is_overdue`, transições, validação), agregações no controller de relatório. (playbook T5)

### [HIGH] #8 Entrada sem validação de tipo e limite: 500 e dado inválido gravado (AP11)
File: routes/task_routes.py:87-114, 162-213, 242-264; routes/user_routes.py:44-65, 98-125, 187-202; routes/report_routes.py:169-202
Description: comparações e `len()` direto no valor da requisição; `int()` em query string sem tratamento; booleano/cor/nome sem checagem; título só com espaços aceito; corpo que não é objeto quebra `.get`.
Impact: dado inválido entra no banco (prioridade 2.5 some de `tasks_by_priority`; título em branco; cor arbitrária) e o cliente recebe 500 HTML sem saber o que corrigir.
Evidence: sondas — 500 em `sonda-title-numero`, `sonda-priority-texto`, `sonda-tags-numeros`, `sonda-corpo-lista`, `sonda-update-priority-texto`, `sonda-busca-priority-texto`, `sonda-busca-user-texto`, `sonda-usuario-senha-numero`, `sonda-login-senha-numero`, `sonda-active-texto`, `sonda-categoria-corpo-null`; 201 gravando dado inválido em `sonda-priority-fracao` (`"priority":2.5`), `sonda-titulo-em-branco`, `sonda-categoria-cor-invalida`.
Recommendation: `utils/validators.py` compartilhado entre criar e atualizar; 400 com mensagem no envelope `{"error": ...}`. (playbook T7)

### [HIGH] #9 Dependências com vulnerabilidade conhecida (AP27)
File: requirements.txt:1-6
Description: `pip-audit` aponta 22 avisos em 5 pacotes: flask 3.0.0 (corrigido em 3.1.3), flask-cors 4.0.0 (4.0.1/4.0.2/6.0.0), requests 2.31.0, marshmallow 3.20.1, python-dotenv 1.0.0.
Impact: Flask e Flask-CORS atendem toda requisição. O `pip-audit` não informa severidade; tratado como HIGH por estar no caminho de runtime.
Evidence: saída do `pip-audit -r requirements.txt` (seção Dependencies).
Recommendation: flask 3.1.3, flask-cors 6.0.x (uso é só `CORS(app, origins=...)`; o gate confirma), python-dotenv 1.2.2; remover `requests` e `marshmallow`, que não são importados.

### [MEDIUM] #10 Erro engolido e páginas de erro HTML numa API JSON (AP08)
File: routes/task_routes.py:62, 137, 151, 204, 221, 236; routes/user_routes.py:87, 130, 149; routes/report_routes.py:186, 207, 221; utils/helpers.py:46, 49, 88; services/notification_service.py:23
Description: 12 `except:` e 4 `except Exception` que escondem a causa; não há error handler, então 400/404/405/415/500 do Flask saem como HTML.
Impact: cliente da API recebe HTML; falhas reais somem dos logs.
Evidence: sondas `sonda-json-quebrado` (400 html), `sonda-sem-content-type` (415 html), `sonda-rota-inexistente` (404 html), `sonda-metodo-nao-permitido` (405), as 11 respostas 500 HTML do #8.
Recommendation: `middlewares/error_handler.py` com `AppError` e handlers JSON usando a chave `error`; capturar só exceções específicas. (playbook T8)

### [MEDIUM] #11 Configuração e bootstrap no import, sem factory (AP14)
File: app.py:9-31
Description: URI do banco, chave e CORS escritos no módulo; `db.create_all()` roda no import; porta 5000 fixa.
Impact: impossível subir com outro banco/porta (teste, deploy) sem editar código.
Evidence: leitura; inventário (`hardcoded_ports: [5000]`).
Recommendation: `create_app()` como composition root e `config/settings.py` lendo o ambiente. (playbook T4)

### [MEDIUM] #12 CORS aberto para qualquer origem (AP10)
File: app.py:15
Description: `CORS(app)` sem lista de origens.
Impact: qualquer site chama a API a partir do navegador do usuário.
Evidence: `scan_signals.py` (cors-open).
Recommendation: origens em `CORS_ORIGINS`; sem valor, CORS desligado. (playbook T2)

### [MEDIUM] #13 APIs legadas/deprecated (AP16)
File: ver seção Deprecated APIs (78 ocorrências)
Description: `datetime.utcnow()` (deprecated no Python 3.12; ambiente usa 3.14), `Model.query` e `Model.query.get()` (legados no SQLAlchemy 2.0 / Flask-SQLAlchemy 3).
Impact: avisos hoje, quebra na remoção; `query.get` emite `LegacyAPIWarning`.
Evidence: `scan_signals.py`; Context7 (docs Flask-SQLAlchemy stable: "The legacy query interface ... prefer session.execute(select(...))").
Recommendation: helper `utcnow()` (UTC sem tzinfo, preservando o formato das datas no JSON), `db.session.get`, `db.select`. (playbook T12)

### [MEDIUM] #14 Consultas N+1 (AP17)
File: routes/task_routes.py:41-57 (2 queries por task); routes/user_routes.py:22 (`len(u.tasks)` por usuário); routes/report_routes.py:55-56 (tasks por usuário), 161-163 (count por categoria)
Description: consulta dentro de laço em listagens e relatórios.
Impact: número de queries cresce com os dados (`GET /tasks` faz 1 + até 2 por task; o identity map só poupa usuários/categorias já carregados; `/reports/summary` faz 1 por usuário).
Evidence: `scan_signals.py` (query-in-loop ×5) e leitura.
Recommendation: `selectinload`/join e contagens agrupadas (`GROUP BY`). (playbook T10)

### [MEDIUM] #15 Lógica duplicada (AP19)
File: regra de atraso em routes/task_routes.py:30-39, 71-80, 283-287; routes/user_routes.py:171-180; routes/report_routes.py:33-37, 132-135; models/task.py:50-60. Serialização de task em routes/task_routes.py:17-28, routes/user_routes.py:162-169, models/task.py:23-36. Validação de task em criar (task_routes.py:92-144), atualizar (166-213) e utils/helpers.py:57-108 (não usado).
Description: a mesma regra copiada 7 vezes; três serializações de task; três versões da validação.
Impact: as cópias já divergem (`/users/<id>/tasks` omite `tags`, `user_id`, `updated_at`).
Evidence: `scan_signals.py` (duplicate-block ×2) e leitura.
Recommendation: uma regra no model, um serializador, um validador. (playbook T5)

### [MEDIUM] #16 Task marcada como atrasada no próprio dia do prazo (AP25)
File: routes/task_routes.py:136, 203 (prazo gravado à meia-noite) com as comparações do #15
Description: `due_date` vem como `YYYY-MM-DD` e vira 00:00; a regra compara com `utcnow()`, então uma task com prazo "hoje" fica atrasada desde 00:00 UTC do dia.
Impact: `overdue`, `/tasks/stats` e relatórios contam como atrasada uma task ainda no prazo.
Evidence: confirmado por leitura (entrada hostil #10).
Recommendation: comparar a data do prazo com a data de hoje em UTC (`due_date.date() < hoje`), dentro de `Task.is_overdue`. (playbook T15)

### [MEDIUM] #17 "Concluídas nos últimos 7 dias" conta qualquer edição de task concluída (AP25)
File: routes/report_routes.py:48-51
Description: a métrica usa `updated_at`, que muda em qualquer edição; não existe data de conclusão.
Impact: relatório superestima produtividade recente.
Evidence: confirmado por leitura (entrada hostil #11).
Recommendation: coluna `completed_at` preenchida na transição para `done`. Exige migração de esquema (o projeto só tem `create_all`, que não altera tabela existente) — fica em melhorias propostas, não na Fase 3.

### [MEDIUM] #18 Serviço de notificação sem uso, com SMTP fixo no código (AP12/AP18)
File: services/notification_service.py:1-48
Description: `NotificationService` nunca é instanciado; abre conexão SMTP dentro do método e guarda notificações numa lista em memória.
Impact: camada morta que parece funcionar; quando ligada, acoplaria o handler HTTP ao SMTP.
Evidence: `grep NotificationService` só encontra a definição; `scan_signals.py` (fake-side-effect).
Recommendation: manter como serviço com config do ambiente e `logging`; ligar a um evento/fila fica em melhorias propostas (mudaria comportamento). (playbook T5)

### [LOW] #19 Código morto: imports, helpers e dependências sem uso (AP18)
File: app.py:7; models/task.py:3; routes/task_routes.py:7; routes/user_routes.py:6; routes/report_routes.py:7-8; utils/helpers.py:3-7, 9-116; requirements.txt (marshmallow, requests)
Description: 18 imports sem uso; `utils/helpers.py` inteiro sem chamador; 2 dependências nunca importadas.
Evidence: `scan_signals.py` (unused-import ×18) e `grep`.
Recommendation: remover; aproveitar a validação útil no novo `validators.py`.

### [LOW] #20 print como log (AP13)
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41; seed.py:93-96
Description: 15 `print` sem nível nem destino.
Evidence: `scan_signals.py`.
Recommendation: `logging` com nível configurável (no seed o `print` é saída de CLI e pode ficar). (playbook T14)

### [LOW] #21 Dado pessoal em log (AP07)
File: services/notification_service.py:21, 24; routes/user_routes.py:83; routes/task_routes.py:149
Description: e-mail do destinatário, nome do usuário e título da task impressos.
Evidence: `scan_signals.py` (sensitive-log ×2) e leitura.
Recommendation: logar só IDs. (playbook T14)

### [LOW] #22 Literais repetidos e magic numbers (AP20)
File: lista de status em models/task.py:39, routes/task_routes.py:110, 177, utils/helpers.py:75, 110; roles em routes/user_routes.py:71, 120, utils/helpers.py:111; regex de e-mail em routes/user_routes.py:61, 106, utils/helpers.py:21; limites 1/5, 3/200, 4 espalhados
Recommendation: constantes no model (`Task.STATUSES`, `User.ROLES`, limites).

### [LOW] #23 Nomes sem significado (AP26)
File: routes/report_routes.py:24-28 (`p1`..`p5`), laços com `t`, `u`, `c`, `cat` em todas as rotas
Recommendation: nomes descritivos no código reescrito (campos do contrato preservados).

### [LOW] #24 Curingas do LIKE não escapados na busca (AP11)
File: routes/task_routes.py:250-255
Description: `q` vai para `like(f'%{q}%')` parametrizado (sem injeção SQL), mas `%` e `_` funcionam como curinga: `q=%` devolve tudo.
Recommendation: `contains(q, autoescape=True)`.

Checked without findings: SQL injection (AP01: só ORM parametrizado), execução de código do cliente (AP02), estado global mutável (AP09: a lista do NotificationService é de instância e o serviço não é usado), transação (AP23: exclusão de usuário e tasks num commit só), exclusão de categoria (relacionamento anula o FK).

## Deprecated APIs
| Uso | Onde | Equivalente moderno | Fonte |
|---|---|---|---|
| `datetime.utcnow()` | models/*.py (defaults), routes/*.py, utils/helpers.py:38 (22 ocorrências) | `datetime.now(timezone.utc)` (helper que remove tzinfo para manter o formato e a comparação com colunas naive) | tabela do catálogo + Python 3.12 changelog |
| `Model.query.get(id)` | routes/*.py (16 ocorrências) | `db.session.get(Model, id)` | tabela do catálogo + Context7 (Flask-SQLAlchemy stable) |
| `Model.query.filter_by/count/all` | routes/*.py, seed.py (40 ocorrências) | `db.session.execute(db.select(Model)...)`, `db.session.scalar(db.select(func.count())...)` | Context7: "legacy query interface ... prefer session.execute(select(...))" |

## Dependencies
`pip-audit -r requirements.txt` (rede disponível): 22 avisos em 5 pacotes — flask 3.0.0 → 3.1.3; flask-cors 4.0.0 → 4.0.1/4.0.2/6.0.0; requests 2.31.0 → 2.33.0 (não usado); marshmallow 3.20.1 → 3.26.2 (não usado); python-dotenv 1.0.0 → 1.2.2. Severidade não informada pela ferramenta. Ambiente: Python 3.14.8, instalação sem erro.

## Baseline (estado atual dos endpoints)
59 requisições | 11 5xx/sem resposta | 0 derrubaram o processo
- Caminho feliz: 22 endpoints respondem (200/201), erros de negócio 400/401/404/409 em JSON.
- Autorização (#1): criar admin anônimo 201; promover sem auth 200; trocar senha de outro 200; excluir categoria/usuário anônimo 200.
- Exposição de senha (#2): `GET /users/1`, `POST /users`, `PUT /users/2`, `POST /login` devolvem `password` (hash MD5).
- Tipo/limite (#8): 11 respostas 500 HTML; 3 gravações inválidas (prioridade 2.5, título em branco, cor arbitrária).
- FK (#6): `category_id: 0` gravado com 200.
- Erros HTML (#10): 400, 404, 405, 415 e 500 em HTML.

## Proposed improvements (not defects)
- Exigir login e dono nas rotas de task (`PUT/DELETE /tasks/<id>`) e em `POST/PUT /categories` — muda o contrato dos clientes atuais.
- `completed_at` e máquina de estados para `status` (hoje qualquer transição é aceita, inclusive `cancelled → done`); o projeto não define transições proibidas e reabrir task é legítimo, então fica como decisão de produto, com migração (#17).
- Ferramenta de migração (Flask-Migrate/Alembic) no lugar de `create_all`.
- Política de senha mais forte (mínimo atual de 4 caracteres) e e-mail normalizado em minúsculas — mudam respostas atuais.
- Exclusão lógica de usuário (hoje apaga as tasks dele, perdendo histórico).
- Paginação em `/tasks`, `/users`, `/categories`.
- Notificação de atribuição via fila/evento usando o `NotificationService`.

## Phase 3 plan
- Target structure:
  ```
  app.py                 # entry fino: create_app(); app.run(HOST/PORT/FLASK_DEBUG)
  seed.py                # via create_app()
  requirements.txt  .env.example  README.md
  src/
    app.py               # create_app: config, db, CORS, blueprints, error handlers, create_all
    config/settings.py
    database.py
    models/              task_model.py, user_model.py, category_model.py
    controllers/         task_controller.py, user_controller.py, category_controller.py, report_controller.py, auth_controller.py
    views/               task_routes.py, user_routes.py, category_routes.py, report_routes.py, auth_routes.py, health_routes.py
    services/            notification_service.py, token_service.py
    middlewares/         error_handler.py, auth.py
    utils/               validators.py, time.py
  ```
- Intentional behavior changes: `password` sai das respostas (#2); token do login vira token assinado (campo `token` continua string) (#1); 401/403 para criar usuário com role privilegiado, alterar usuário sem ser ele ou admin, alterar `role`/`active` sem ser admin, excluir usuário/categoria sem ser admin (#1); 400 para tipos/limites inválidos (#8); 404 para FK inexistente com valor 0 (#6); erros em JSON em vez de HTML, mesmos status (#10); `overdue` falso no dia do prazo (#16); busca trata `%`/`_` como texto (#24); bind padrão 127.0.0.1 e debug desligado (#5); CORS só com `CORS_ORIGINS` (#12).
- Out of scope: itens de "Proposed improvements"; métrica de concluídas (#17) por exigir migração.

================================
Total: 24 findings
================================
