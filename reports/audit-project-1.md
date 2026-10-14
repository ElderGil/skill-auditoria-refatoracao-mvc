================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (flask-cors 5.0.1, sqlite3)
Files:   4 analyzed | ~780 lines of code (664 não vazias)
Grade:   A monólito

## Summary
CRITICAL: 7 | HIGH: 8 | MEDIUM: 6 | LOW: 5 | Total: 26

## Findings

### [CRITICAL] #1 SQL montado por concatenação com entrada do cliente (AP01)
File: models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 289-299
Description: Todas as consultas de models.py concatenam valores de request (nome, descrição, categoria, e-mail, senha, termo de busca, status) direto na string SQL.
Impact: Login sem senha, leitura de qualquer tabela via `UNION` na busca, alteração de dados; entrada legítima com apóstrofo quebra com 500.
Evidence: sonda `sonda-sql-login` (e-mail `admin@loja.com' --`, senha qualquer): 200 com os dados do admin. `sonda-apostrofo-produto`: 500, com o erro do SQLite devolvido ao cliente (`near "geral": syntax error`). `sonda-apostrofo-busca`: 500.
Recommendation: placeholders `?` com tupla de parâmetros em toda consulta; filtros dinâmicos da busca montados com lista de cláusulas fixas + parâmetros (playbook T1).

### [CRITICAL] #2 Endpoint que executa SQL arbitrário enviado pelo cliente (AP02)
File: app.py:59-78
Description: `POST /admin/query` executa o campo `sql` do corpo, sem autenticação, e faz commit quando não é SELECT.
Impact: Acesso total ao banco por HTTP: ler senhas, apagar tabelas, criar admin.
Evidence: sondas `admin-query` e `sonda-admin-query-sem-auth`: 200 sem nenhum cabeçalho de credencial.
Recommendation: remover o endpoint (não há versão segura de "execute este SQL") (playbook T13).

### [CRITICAL] #3 Reset do banco sem autenticação (AP06)
File: app.py:47-57
Description: `POST /admin/reset-db` apaga itens, pedidos, produtos e usuários para qualquer chamador.
Impact: Qualquer pessoa com a URL destrói todos os dados.
Evidence: sonda `sonda-reset-sem-auth`: 200, banco esvaziado na cópia do baseline.
Recommendation: exigir token de administrador vindo de variável de ambiente (`ADMIN_TOKEN`, cabeçalho `X-Admin-Token`, comparação em tempo constante); sem token configurado, a rota fica desabilitada (401) (playbook T13).

### [CRITICAL] #4 Senhas em texto puro, comparadas no SQL e devolvidas pela API (AP05)
File: database.py:75-83 (seed com senhas literais), models.py:83, 99 (serialização com `senha`), models.py:110 (comparação na query), models.py:126-129 (gravação)
Description: A senha é gravada como veio, o login compara texto puro dentro do SQL, e `GET /usuarios` e `GET /usuarios/<id>` devolvem o campo `senha` de todos os usuários.
Impact: Qualquer chamador anônimo obtém as senhas de todos os usuários, incluindo a do admin; vazamento do arquivo do banco entrega as senhas prontas.
Evidence: baseline `listar-usuarios` e `buscar-usuario`: o objeto tem as chaves `criado_em, email, id, nome, senha, tipo` (valores não reproduzidos aqui).
Recommendation: hash com `werkzeug.security` (`generate_password_hash`/`check_password_hash`), login busca por e-mail e confere o hash; remover `senha` da serialização; migrar no boot as senhas legadas em texto puro para hash (playbook T3).

### [CRITICAL] #5 Chave secreta no código e devolvida pelo /health (AP03)
File: app.py:7 (`SECRET_KEY`), controllers.py:289 (campo `secret_key` da resposta)
Description: `SECRET_KEY` é literal no código, e o `GET /health` a devolve em claro, junto com `debug` e `db_path`.
Impact: Quem lê o repositório ou chama `/health` pode forjar sessões assinadas pela aplicação.
Evidence: baseline `health`: a resposta tem as chaves `ambiente, counts, database, db_path, debug, secret_key, status, versao` (valor não reproduzido).
Recommendation: `SECRET_KEY` vinda do ambiente (com chave aleatória gerada no boot quando ausente) e removida da resposta do `/health`. **Trocar a chave atual, porque ela já está no histórico do git** (playbook T2).

### [CRITICAL] #6 Debug ligado e servidor exposto em todas as interfaces (AP04)
File: app.py:8, app.py:88
Description: `DEBUG = True` na config e `app.run(host="0.0.0.0", port=5000, debug=True)`.
Impact: O debugger interativo do Werkzeug (execução de código, protegida só por PIN) e os stack traces ficam publicados na rede. Sobe de HIGH para CRITICAL porque se soma ao segredo exposto (#5) e às rotas administrativas abertas (#2, #3).
Evidence: confirmado por leitura (o baseline sobe via `flask run` com `FLASK_DEBUG=0` e não exercita `app.run`).
Recommendation: debug, host e porta vindos do ambiente (`FLASK_DEBUG`, `HOST`, `PORT`), com padrão seguro (debug desligado, `127.0.0.1`, porta 5000) (playbook T2).

### [CRITICAL] #7 God file e camadas misturadas (AP21)
File: models.py:1-314, app.py:47-78, controllers.py:264-290
Description: models.py concentra SQL, serialização e regra de negócio de 4 domínios (produtos, usuários, pedidos, relatórios), incluindo a regra de desconto do relatório (235-273). app.py tem SQL inline nas rotas admin, e controllers.py:264-290 também tem SQL direto no health.
Impact: Nenhuma regra pode ser testada isolada; qualquer mudança em um domínio mexe no arquivo dos outros.
Evidence: confirmado por leitura; inventário: 4 arquivos na raiz, nenhuma pasta de camada.
Recommendation: separar em models (acesso a dados por entidade), controllers (regra) e views/rotas (HTTP) com factory `create_app` (playbook T4).

### [HIGH] #8 Entradas sem validação de tipo e limite gravam dado inválido (AP11)
File: controllers.py:37-54 e 81-90 (produto), 113-121 (busca), 153-158 (usuário), 195-201 (pedido), 240 (status); models.py:139-146
Description: A validação checa presença e não tipo. Quantidade negativa, fracionada ou texto passa ou vira 500; o update de produto não valida categoria nem tamanho do nome (o create valida); `float()` dos filtros da busca não tem guarda.
Impact: Corrompe a regra de negócio (pedido com total negativo devolve estoque), e o cliente recebe 500 sem saber o que corrigir.
Evidence: `sonda-qtd-negativa`: 201, total -449.5, estoque do produto 2 de 50 → 55. `sonda-estoque-fracionado`: 201. `sonda-update-categoria-invalida`: 200 com categoria `xyz` gravada. `sonda-preco-texto`, `sonda-preco-min-texto`, `sonda-nome-numero`, `sonda-qtd-texto`: 500.
Recommendation: validação centralizada por entidade (tipo, inteiro positivo, faixa, tamanho, `strip`), igual para criar e atualizar, com resposta 400 no envelope atual (playbook T7).

### [HIGH] #9 Integridade de dados não garantida (AP24)
File: models.py:133-169 (pedido), models.py:122-131 + database.py:27-35 (e-mail sem UNIQUE), models.py:65-70 (delete físico), models.py:275-283 (status)
Description: O estoque é conferido item a item (item repetido fura o total); `usuario_id` não é verificado; e-mail duplicado é aceito; `PUT /pedidos/<id>/status` responde sucesso para pedido inexistente; apagar um produto deixa itens de pedido órfãos.
Impact: Estoque negativo, pedidos de usuários inexistentes, contas duplicadas e histórico de pedidos com "Desconhecido".
Evidence: `sonda-item-repetido` (5+5 com estoque 8): 201, estoque 8 → -2. `sonda-usuario-inexistente`: 201. `sonda-email-duplicado`: 201. `sonda-status-pedido-inexistente`: 200. Leitura: após `DELETE /produtos/4`, os itens dos pedidos mostram `produto_nome: "Desconhecido"`.
Recommendation: somar quantidades por produto antes de conferir o estoque; validar o usuário; índice UNIQUE em e-mail com 409; 404 quando o pedido não existe; a exclusão de produto com pedidos fica registrada como melhoria (soft delete muda o contrato) (playbook T6, T7).

### [HIGH] #10 Status do pedido sem máquina de estados (AP25)
File: controllers.py:237-252, models.py:275-283, models.py:235-273
Description: Qualquer status válido substitui o atual (cancelado → aprovado). "Devolver estoque" no cancelamento é só um `print`. O relatório soma pedidos cancelados no faturamento.
Impact: Pedido cancelado volta a ser aprovado, o estoque de pedido cancelado nunca volta, e o faturamento fica inflado.
Evidence: `sonda-reabrir-cancelado`: 200. Leitura em cópia descartável: estoque do produto 4 de 15 → 14 no pedido e continua 14 após cancelar; faturamento bruto igual antes e depois do cancelamento (14449.4), com 1 pedido cancelado contado.
Recommendation: tabela de transições permitidas (pendente → aprovado/cancelado; aprovado → enviado/cancelado; enviado → entregue); o cancelamento devolve o estoque na mesma transação; faturamento sem os cancelados (playbook T15).

### [HIGH] #11 Criação de pedido em várias etapas sem transação (AP23)
File: models.py:133-169
Description: Insere o pedido, os itens e baixa o estoque em comandos separados, com um commit só no fim, sobre a conexão global compartilhada; não há rollback em erro e a checagem de estoque não é atômica com a baixa.
Impact: Uma exceção no meio deixa o pedido pela metade, e esse estado pode ser gravado pelo commit de outra requisição. Dois pedidos simultâneos podem vender o mesmo estoque.
Evidence: confirmado por leitura.
Recommendation: transação explícita (`with conn:`), com baixa condicional (`UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?`) e rollback em falha (playbook T6).

### [HIGH] #12 Conexão global compartilhada entre threads (AP09)
File: database.py:4-10
Description: Uma única conexão SQLite em variável global, com `check_same_thread=False`, serve todas as requisições do servidor multithread.
Impact: Condição de corrida entre requisições, transações misturadas (ver #11) e impossibilidade de isolar em teste.
Evidence: confirmado por leitura.
Recommendation: conexão por requisição em `flask.g`, fechada no `teardown_appcontext`; caminho do banco vindo da config (playbook T11).

### [HIGH] #13 Regra de negócio e orquestração no controller (AP22)
File: controllers.py:24-62, 64-96, 188-220, 237-255
Description: Os handlers validam, decidem (categorias válidas, status válidos), disparam "notificações" e montam a resposta; a regra de desconto está no model de dados.
Impact: A mesma regra é escrita duas vezes e diverge (create e update de produto), e não há como testá-la sem HTTP.
Evidence: confirmado por leitura; a divergência é provada por `sonda-update-categoria-invalida`.
Recommendation: controllers com a regra de negócio, rotas finas que só traduzem HTTP ↔ controller (playbook T5).

### [HIGH] #14 Consulta N+1 aninhada na listagem de pedidos (AP17)
File: models.py:171-201, 203-233 (consulta por pedido e por item); models.py:139-166 (consulta por item na criação)
Description: Para cada pedido, uma query de itens; para cada item, uma query do nome do produto. São 1 + P + I consultas.
Impact: A listagem fica mais lenta a cada pedido. Sobe para HIGH porque o laço é aninhado.
Evidence: scan_signals `query-in-loop` (8 sinais); confirmado por leitura.
Recommendation: uma consulta com `JOIN` itens_pedido × produtos para todos os pedidos, agrupada em memória (playbook T10).

### [HIGH] #15 Login não emite credencial; rotas de escrita e dados de terceiros sem autenticação (AP06)
File: controllers.py:167-186 (login), app.py:14-16, 18-19, 24-26
Description: `/login` responde 200 sem token nem sessão. Criar, alterar e apagar produto, mudar status de pedido, listar todos os usuários e todos os pedidos não exigem identidade.
Impact: Qualquer chamador altera catálogo e pedidos e lê dados pessoais (nome, e-mail) de todos os clientes.
Evidence: baseline: `deletar-produto`, `status-aprovado`, `listar-usuarios` e `listar-pedidos` respondem 200 sem credencial.
Recommendation: login emitindo token e um decorator `@requer_admin`/`@requer_login`. **Isso muda o contrato da API** (todos os clientes passam a enviar credencial), então pela regra 5 da skill fica em "Proposed improvements" e fora da Fase 3, salvo decisão sua. Na Fase 3, só as rotas `/admin/*` passam a exigir token (#2, #3).

### [MEDIUM] #16 Tratamento de erro que vaza detalhe interno e transforma erro de cliente em 500 (AP08)
File: app.py:77-78; controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292; controllers.py:169-170, 239-240 (`get_json()` seguido de `.get` sem checar `None`)
Description: Todo handler tem `except Exception` que devolve `str(e)` ao cliente; corpo ausente ou não-JSON vira `AttributeError`/`UnsupportedMediaType` e cai no 500.
Impact: Mensagens internas do SQLite e do Python chegam ao cliente; erro de cliente aparece como falha do servidor.
Evidence: `sonda-login-sem-json`: 500. `sonda-status-sem-corpo`: 500. `sonda-apostrofo-produto`: 500 com o texto do erro do SQLite.
Recommendation: error handlers centrais (`ValidationError` → 400, `NotFound` → 404, `Conflict` → 409, exceção inesperada → 500 genérico com log), leitura de JSON tolerante (playbook T8).

### [MEDIUM] #17 Efeitos colaterais fingidos dentro do handler HTTP (AP12)
File: controllers.py:208-210, 247-250
Description: "ENVIANDO EMAIL/SMS/PUSH" e "Devolver estoque" são `print` no meio do handler.
Impact: O fluxo finge notificar, e não há ponto para trocar ou testar o canal.
Evidence: scan_signals `fake-side-effect` (5 sinais); confirmado por leitura.
Recommendation: serviço `Notificador` com interface única, chamado pelo controller depois do commit; a devolução de estoque passa a ser real (#10) (playbook T5).

### [MEDIUM] #18 Lógica duplicada que já divergiu (AP19)
File: models.py:12-21, 31-40, 304-313 (serialização de produto ×3); models.py:79-86, 95-102 (usuário ×2); models.py:171-201, 203-233 (pedidos ×2); controllers.py:28-50, 72-90 (validação de produto ×2, divergente)
Description: Serialização e validação copiadas em vários lugares.
Impact: As cópias já divergem: o update não valida categoria nem o tamanho do nome.
Evidence: scan_signals `duplicate-block` (6 sinais); `sonda-update-categoria-invalida`.
Recommendation: um serializador por entidade e um validador por entidade (playbook T5).

### [MEDIUM] #19 Configuração e bootstrap inline, porta fixa, sem factory (AP14)
File: app.py:6-9, 80-88; database.py:5; controllers.py:285-289
Description: Config literal no módulo, porta 5000 fixa, caminho do banco fixo, e versão e ambiente "producao" literais no health.
Impact: Não há como subir com outro banco, porta ou config (teste, deploy) sem editar código.
Evidence: inventário: `hardcoded_ports: [5000]`. O baseline precisou de `flask --app app run -p` porque `python app.py` ignora `PORT`.
Recommendation: `config.py` lendo do ambiente + `create_app()`; `python app.py` continua funcionando (playbook T4).

### [MEDIUM] #20 CORS aberto para qualquer origem (AP10)
File: app.py:9
Description: `CORS(app)` sem `origins`.
Impact: Qualquer site chama a API pelo navegador do usuário.
Evidence: scan_signals `cors-open`.
Recommendation: origens permitidas vindas de `CORS_ORIGINS`. O padrão `*` é mantido para não quebrar clientes atuais e está documentado no `.env.example` (playbook T2).

### [MEDIUM] #21 Dependências com vulnerabilidades conhecidas (AP27)
File: requirements.txt:1-2
Description: pip-audit: flask 3.1.1 tem CVE-2026-27205 (falta `Vary: Cookie` em alguns acessos a `session`; corrigida em 3.1.3); flask-cors 5.0.1 tem CVE-2024-6866, CVE-2024-6844 e CVE-2024-6839 (casamento de caminho incorreto nas regras de CORS; corrigidas em 6.0.0).
Impact: Baixo nesta aplicação (não usa `session` e aplica CORS global), mas são dependências de runtime com correção disponível. MEDIUM porque nenhuma é crítica/alta no contexto de uso.
Evidence: saída do `pip-audit -r requirements.txt` (8 entradas, 4 IDs únicos).
Recommendation: flask → 3.1.3 (mesma major). flask-cors → 6.0.x: é troca de major, mas é a única versão com a correção, e o uso aqui (`CORS(app, origins=...)`) não muda; validar com o gate.

### [LOW] #22 print como mecanismo de log (AP13)
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: 19 `print` fazendo papel de log.
Impact: Sem nível, sem destino configurável, sem formato.
Evidence: scan_signals `print-logging` (19 sinais).
Recommendation: módulo `logging` com logger por módulo (playbook T14).

### [LOW] #23 E-mail de usuário escrito em log (AP07)
File: controllers.py:161, 179, 182
Description: Criação de usuário e login (sucesso e falha) registram o e-mail em claro.
Impact: Dado pessoal em log (LGPD); o log de login falho com e-mail facilita enumeração.
Evidence: scan_signals `sensitive-log`; confirmado por leitura.
Recommendation: logar o id do usuário ou o evento, sem e-mail (playbook T14).

### [LOW] #24 Literais de negócio repetidos e magic numbers (AP20)
File: controllers.py:52, 242; models.py:247-262; controllers.py:285-289
Description: Listas de categorias e de status inline; faixas de desconto (1000/5000/10000 e 2%/5%/10%) soltas no código; versão "1.0.0" repetida.
Impact: Mudar uma regra exige caçar literais.
Evidence: confirmado por leitura.
Recommendation: constantes nomeadas no model/controller do domínio.

### [LOW] #25 Imports sem uso (AP18)
File: database.py:2 (`os`), models.py:2 (`sqlite3`)
Description: Módulos importados e nunca usados.
Impact: Ruído; esconde o que o arquivo realmente usa.
Evidence: scan_signals `unused-import`.
Recommendation: remover.

### [LOW] #26 Nome que sombreia builtin (AP26)
File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89
Description: Parâmetros e variáveis chamados `id`, que sombreiam o builtin.
Impact: Legibilidade e risco de bug sutil.
Evidence: confirmado por leitura.
Recommendation: `produto_id`/`usuario_id` internamente. O nome do parâmetro de rota `<int:id>` é interno ao Flask e pode mudar sem afetar o contrato.

## Deprecated APIs
Nenhum uso de API deprecated foi encontrado no código: o scan_signals não deu sinal de AP16, e a leitura não achou nenhum item da tabela do AP16 (sem `before_first_request`, `flask.escape`, `JSONEncoder`, `utcnow`, `Model.query`). Versões antigas de dependência estão no achado #21.
Fonte: tabela do catálogo (AP16). O Context7 não foi consultado porque a permissão da ferramenta não foi concedida nesta sessão.

## Dependencies
pip-audit (requirements.txt): 4 vulnerabilidades únicas em 2 pacotes.
- flask 3.1.1: CVE-2026-27205 / GHSA-68rp-wp8r-4726, corrigida em 3.1.3
- flask-cors 5.0.1: CVE-2024-6866, CVE-2024-6844, CVE-2024-6839, corrigidas em 6.0.0
Dependências declaradas e todas importadas (flask, flask_cors).

## Baseline (estado atual dos endpoints)
49 requisições (31 de caminho feliz cobrindo os 19 endpoints + 18 sondas) | 8 com 5xx | 0 derrubaram o processo
- sonda-sql-login: 200 (login como admin sem senha)
- sonda-admin-query-sem-auth: 200 (SQL arbitrário sem credencial)
- sonda-reset-sem-auth: 200 (banco apagado sem credencial)
- sonda-qtd-negativa: 201 (total -449.5, estoque 50 → 55)
- sonda-item-repetido: 201 (estoque 8 → -2)
- sonda-usuario-inexistente: 201 · sonda-email-duplicado: 201 · sonda-estoque-fracionado: 201
- sonda-status-pedido-inexistente: 200 · sonda-reabrir-cancelado: 200 · sonda-update-categoria-invalida: 200
- 500: sonda-apostrofo-produto, sonda-apostrofo-busca, sonda-preco-texto, sonda-preco-min-texto, sonda-nome-numero, sonda-login-sem-json, sonda-qtd-texto, sonda-status-sem-corpo

## Proposed improvements (not defects)
- Autenticação real (achado #15): login emitindo token e proteção das rotas de escrita e de dados de terceiros. Fica fora porque muda o contrato para todos os clientes.
- Soft delete de produto (`ativo = 0`) no lugar do DELETE físico, preservando o histórico de pedidos. Fica fora porque muda a semântica do `DELETE` e do `GET /produtos`.
- Restringir `CORS_ORIGINS` a domínios conhecidos em produção (o padrão continua `*` para não quebrar clientes).
- Paginação em `GET /produtos`, `/usuarios` e `/pedidos`.
- Suíte de testes automatizados (pytest) sobre os controllers, agora testáveis sem HTTP.
- Migrar o schema para FKs declaradas (`FOREIGN KEY ... ON DELETE RESTRICT`) com `PRAGMA foreign_keys=ON`. Exige migração de dados existentes.

## Phase 3 plan
- Target structure (o detalhe final segue o guia da stack Flask, lido na Fase 3):
  app.py (entrada: `python app.py`) · config.py · database.py (conexão por requisição, schema, seed, migração de senhas)
  models/ (produto, usuario, pedido: SQL parametrizado e serialização)
  controllers/ (produto, usuario, pedido, relatorio, sistema: validação e regra de negócio)
  views/ (blueprints HTTP finos: produtos, usuarios, pedidos, relatorios, sistema, admin)
  services/notificacao.py · errors.py (exceções de domínio + handlers JSON)
- Intentional behavior changes:
  - `/health` sem `secret_key` (#5); `/usuarios` e `/usuarios/<id>` sem `senha` (#4)
  - `/admin/query` removido → 404 (#2); `/admin/reset-db` exige `X-Admin-Token` = `ADMIN_TOKEN` → 401 sem ele (#3)
  - login por injeção → 401; apóstrofo em nome e busca passa a funcionar (#1)
  - tipos e limites inválidos → 400 (#8); corpo ausente ou não-JSON → 400 (#16)
  - e-mail duplicado → 409; usuário inexistente no pedido → 400; status de pedido inexistente → 404; item repetido somado no estoque → 400 (#9)
  - transição inválida de status → 400; cancelamento devolve estoque; faturamento do relatório exclui cancelados (#10)
  - erro 500 com mensagem genérica, sem `str(e)` (#16)
  - `python app.py` lê `PORT`, `HOST` e `FLASK_DEBUG` do ambiente (padrão: 127.0.0.1:5000, debug desligado) (#6, #19)
- Out of scope: autenticação das rotas de cliente/escrita (#15, mudança de contrato), soft delete, paginação, FKs no schema (ver melhorias propostas). Nenhum commit é feito.

================================
Total: 26 findings
================================
