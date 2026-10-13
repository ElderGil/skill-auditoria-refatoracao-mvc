# Skill de auditoria e refatoração arquitetural (`refactor-arch`)

Execução do desafio 03 do MBA em Engenharia de Software com IA da Full Cycle. Este repositório é um fork de [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill), onde está o enunciado original.

A skill `/refactor-arch` do Claude Code analisa um projeto, audita contra um catálogo de anti-patterns, pede confirmação e refatora para MVC, validando que a aplicação continua de pé. Ela foi aplicada a três projetos legados:

| # | Projeto | Stack | Ponto de partida |
|---|---|---|---|
| 1 | `code-smells-project/` | Python + Flask 3.1, SQLite com SQL à mão | Monólito em 4 arquivos |
| 2 | `ecommerce-api-legacy/` | Node.js + Express 4, SQLite em memória | God class com callbacks aninhados |
| 3 | `task-manager-api/` | Python + Flask 3.0, Flask-SQLAlchemy | Camadas existem, regra de negócio nas rotas |

## Análise Manual

Li os três projetos antes de escrever a skill e confirmei cada comportamento rodando a aplicação numa cópia isolada, com requisição real. Foram duas passadas. A primeira leu o código e testou o óbvio. A segunda releu linha a linha e provocou cada endpoint com entrada hostil: tipo errado, item repetido, transição de estado inválida, recurso inexistente, corpo malformado e campo privilegiado no corpo. Os itens marcados com ² saíram da segunda passada.

A escala é a do enunciado: **CRITICAL** quebra o funcionamento, expõe dado sensível ou destrói a separação de camadas; **HIGH** viola MVC/SOLID e trava manutenção e teste; **MEDIUM** é padronização, duplicação ou performance; **LOW** é legibilidade, nomes e magic numbers.

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| 1 — code-smells-project | 6 | 7 | 7 | 3 | 23 |
| 2 — ecommerce-api-legacy | 4 | 6 | 5 | 3 | 18 |
| 3 — task-manager-api | 4 | 4 | 8 | 3 | 19 |

Dependências, por ferramenta de auditoria: `pip-audit` aponta 8 vulnerabilidades conhecidas no projeto 1 (flask 3.1.1, flask-cors 5.0.1) e 22 no projeto 3 (flask, flask-cors 4.0.0, marshmallow, requests, python-dotenv); `npm audit` aponta 14 no projeto 2 (2 critical, 8 high), incluindo `tar`, `proxy-addr`, `path-to-regexp` e a cadeia do `sqlite3`.

### Projeto 1 — code-smells-project (Flask, e-commerce)

`app.py` (88 linhas), `controllers.py` (292), `models.py` (314) e `database.py` (86). Sem camada de serviço nem ORM; todo SQL é montado por concatenação de strings. 19 endpoints para produtos, usuários, pedidos e relatório de vendas.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `models.py:110` e outras 18 queries | **SQL injection em todo o acesso a dados.** As queries são montadas com `+`. No login, a senha `x' OR '1'='1` entra como admin sem saber a senha. | Login com essa senha → 200 como admin. Busca por `O'Brien` → 500 com erro de SQL. |
| 2 | CRITICAL | `app.py:59-78` | **`/admin/query` executa qualquer SQL recebido no corpo, sem autenticação.** Quem chega na API lê, altera ou apaga o banco inteiro. | `SELECT email, senha FROM usuarios` → todas as senhas. |
| 3 | CRITICAL | `app.py:47-57` | ² **`/admin/reset-db` sem autenticação apaga todas as tabelas.** Um POST anônimo zera a loja. | POST → 200; `GET /produtos` volta vazio. |
| 4 | CRITICAL | `database.py:76-78`, `models.py:83,99` | **Senhas em texto puro, devolvidas pela API.** Um vazamento do banco ou da listagem de usuários entrega as credenciais prontas para uso. | `GET /usuarios` traz o campo `senha` com o valor original. |
| 5 | CRITICAL | `app.py:7-8,88`, `controllers.py:289` | **SECRET_KEY fixa no código e debug ligado em `0.0.0.0`.** O `/health` devolve a chave no JSON público, o que permite forjar sessões assinadas. O debug expõe o debugger interativo do Werkzeug na rede, protegido só por PIN. | `GET /health` → `secret_key` e `"ambiente": "producao"`. |
| 6 | CRITICAL | `app.py`, `controllers.py`, `models.py` | **Sem separação de camadas.** `app.py` mistura rotas com dois handlers que fazem SQL; o controller valida, orquestra e monta resposta; `models.py` concentra quatro domínios. Não há como testar uma regra isolada nem mudar uma parte sem mexer nas outras. | Leitura. |
| 7 | HIGH | todas as rotas | ² **Nenhuma autenticação nem autorização.** O login só devolve os dados do usuário, sem token nem sessão. Qualquer pessoa lista usuários e pedidos e muda o status de um pedido. | `GET /usuarios`, `GET /pedidos` e `PUT /pedidos/1/status` anônimos → 200. |
| 8 | HIGH | `models.py:133-169` | **Pedido criado sem transação.** Insere o pedido, depois os itens, depois baixa o estoque, em passos soltos. Uma falha no meio deixa pedido sem item ou estoque errado, e duas compras simultâneas vendem a mesma unidade. | Leitura. |
| 9 | HIGH | `models.py:139-146` | ² **Estoque checado item a item, não pelo total.** O mesmo produto repetido no pedido passa em cada checagem e vende mais do que existe. | Estoque 10, dois itens de 6 do mesmo produto → 201 e estoque -2. |
| 10 | HIGH | `models.py:144,146,164`, `controllers.py:188-201` | **Quantidade não validada.** Quantidade negativa passa e o estoque aumenta; zero cria pedido de valor zero; fração grava estoque quebrado; texto ou campo ausente derruba a requisição. | `-5` → 201, total -29999.94, estoque 10→15. ² `0` → total 0; `0.5` → estoque 49.5; `"2"` e campo ausente → 500. |
| 11 | HIGH | `controllers.py:237-252`, `models.py:275-283` | ² **Status do pedido sem máquina de estados.** Qualquer transição vale, inclusive cancelado → aprovado. Cancelar não devolve o estoque (só imprime "Devolver estoque"). Pedido inexistente responde sucesso. | `PUT /pedidos/9999/status` → 200; cancelado → aprovado → 200; estoque não volta. |
| 12 | HIGH | `controllers.py:195-203`, `models.py:149` | **Usuário do pedido não é validado.** Cria pedido para um `usuario_id` que não existe, gerando dado órfão no faturamento. | `usuario_id: 99999` → 201. |
| 13 | HIGH | `models.py:171-233` | **Consulta N+1.** A listagem de pedidos faz uma query por pedido e outra por item para buscar o nome do produto. O tempo cresce com o histórico. | Leitura. |
| 14 | MEDIUM | `models.py:235-273` | ² **Relatório de vendas soma pedidos cancelados** e calcula desconto sobre esse total; a regra de faixas de desconto está na camada de dados. Dinheiro é guardado como `REAL` (ponto flutuante). O número que a gestão vê está errado. | Com um pedido cancelado, ele entra no `faturamento_bruto`. |
| 15 | MEDIUM | `database.py:27-34`, `models.py:122-131` | ² **E-mail sem unicidade.** O cadastro aceita e-mail repetido, e o login passa a depender de qual linha o banco devolve primeiro. | `POST /usuarios` com `admin@loja.com` → 201. |
| 16 | MEDIUM | `controllers.py:98-107`, `models.py:65-70` | ² **Delete físico de produto apaga o histórico.** O item do pedido antigo passa a aparecer como "Desconhecido". A coluna `ativo` existe e nenhuma consulta usa. | Depois do delete, o pedido mostra `"produto_nome": "Desconhecido"`. |
| 17 | MEDIUM | `controllers.py:37-54` e `:81-90` | **Validação duplicada e divergente.** Atualizar produto não checa tamanho do nome nem categoria, que o cadastro checa. A mesma regra em dois lugares já se desencontrou. | Leitura. |
| 18 | MEDIUM | `controllers.py:39,83,119-121,169-170,239-240` | **Tipo e corpo não validados.** Preço como texto, `preco_max=abc` ou login sem corpo JSON viram erro 500 em vez de 400. O cliente não sabe o que corrigir. | `preco: "abc"` → 500; ² `preco_max=abc` → 500; login sem JSON → 500. |
| 19 | MEDIUM | `controllers.py:208-210,248-250` | **Notificação fingida no controller.** E-mail, SMS e push são `print`. Nada é enviado, e a notificação está acoplada ao fluxo HTTP. | Leitura. |
| 20 | MEDIUM | `database.py:4,9`, `app.py:9` | **Conexão global compartilhada** entre threads (`check_same_thread=False`) e CORS aberto para qualquer origem. Concorrência e origem sem controle. | Leitura. |
| 21 | LOW | `controllers.py` (17 ocorrências) | **`except Exception` devolvendo `str(e)` ao cliente**, que vê detalhe interno, e `print` como log, inclusive com o e-mail de quem tenta logar. | Busca por `O'Brien` expõe o erro de SQL. |
| 22 | LOW | `controllers.py:28,56` e outros | Variável `id` sombreando a função nativa; listas de categorias e status repetidas no meio do código, sem constante. | Leitura. |
| 23 | LOW | `models.py:2`, `database.py:2,5`, `controllers.py:118-121` | ² Imports sem uso; caminho relativo `loja.db` (o banco muda conforme a pasta de onde se roda); `preco_min=0` é ignorado porque zero conta como "vazio". | Leitura. |

### Projeto 2 — ecommerce-api-legacy (Express, LMS com checkout)

`app.js` (14 linhas), `AppManager.js` (141) e `utils.js` (25). A classe `AppManager` cria o banco, faz o seed, registra as rotas e implementa toda a regra. 3 endpoints: checkout, relatório financeiro e exclusão de usuário.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `AppManager.js:46,68` | ² **Uma requisição derruba o servidor.** `card` ou `pwd` enviados como número quebram `cc.startsWith` e `Buffer.from(pwd)` dentro do callback do SQLite. O Express 4 não captura erro lançado em callback assíncrono, e o processo Node termina. | `card` numérico → sem resposta, processo encerrado; `pwd: 123` → idem. |
| 2 | CRITICAL | `utils.js:2-6` | **Credenciais de produção no código**: senha do banco, chave `pk_live` do gateway e usuário de SMTP. Quem tem acesso ao repositório tem acesso a tudo. | Leitura. |
| 3 | CRITICAL | `AppManager.js:45` | **Número do cartão e chave do gateway impressos no log.** Log costuma ir para ferramentas com acesso amplo; isso quebra qualquer exigência de PCI. | Log real com o cartão completo e a chave `pk_live`. |
| 4 | CRITICAL | `utils.js:17-23` | **`badCrypto` não é hash.** Repete o base64 dos dois primeiros caracteres da senha e corta em 10. É reversível e senhas diferentes colidem. | Leitura. |
| 5 | HIGH | `AppManager.js:40,73-75` | ² **Checkout com e-mail existente usa a conta sem pedir senha.** Quem sabe o e-mail de alguém matricula e cobra em nome dessa pessoa; o nome enviado é ignorado. | Checkout com o e-mail do usuário do seed, sem senha → 200, e ele aparece matriculado no curso. |
| 6 | HIGH | `AppManager.js:80,131` | ² **Rotas administrativas abertas.** O relatório financeiro expõe nome de aluno e valor pago; `DELETE /api/users/:id` apaga qualquer usuário. | Ambos anônimos → 200. |
| 7 | HIGH | `AppManager.js:46-48` | **O "pagamento" é `cc.startsWith("4")`.** Qualquer texto que comece com 4 é aprovado, sem gateway e sem validação. Pagamento recusado não deixa registro. | `card: "4-nao-e-cartao"` → 200 e pagamento `PAID`. |
| 8 | HIGH | `AppManager.js:28-78` | **Checkout sem idempotência nem transação.** Repetir o POST cria matrícula e cobrança duplicadas; falha entre matrícula, pagamento e auditoria deixa registro pela metade. | Mesmo payload duas vezes → 2 matrículas. |
| 9 | HIGH | `AppManager.js:131-137` | **Excluir usuário deixa matrículas e pagamentos órfãos** (a própria resposta admite). ² O erro é ignorado e o número de linhas afetadas não é checado: usuário inexistente também responde sucesso. | `DELETE /api/users/1` → 200 "…ficaram sujos no banco"; ² `/users/9999` → 200. |
| 10 | HIGH | `AppManager.js` inteiro | **God class com callbacks aninhados.** Banco, seed, rotas e regra na mesma classe; checkout com quatro níveis de callback e `self`/`this` misturados. Nada pode ser testado nem trocado isoladamente. | Leitura. |
| 11 | MEDIUM | `AppManager.js:80-129` | **Relatório com N+1 e contadores manuais** para esperar os callbacks. ² Nenhum `err` é checado: se uma query falhar, `enrollments.length` lança e derruba o processo. A ordem dos alunos muda a cada chamada. | Uma query por curso, por matrícula, por usuário e por pagamento. |
| 12 | MEDIUM | `AppManager.js:35,68` | **Validação de entrada fraca.** Checa presença, não tipo nem formato de e-mail e cartão. ² Sem `pwd`, a conta nasce com a senha padrão `123456`. | ² Checkout sem `pwd` → 200, usuário criado com senha conhecida. |
| 13 | MEDIUM | `app.js:6` | ² **JSON malformado devolve página HTML com stack trace** e o caminho absoluto do servidor, porque o handler de erro padrão do Express roda sem `NODE_ENV=production`. | Corpo `{"usr":` → 400 em HTML com `SyntaxError … at JSON.parse`. |
| 14 | MEDIUM | `utils.js:9-14`, `AppManager.js:2` | **Estado global mutável** exportado (`globalCache`, `totalRevenue`, este nunca usado). ² O cache cresce a cada checkout e nunca é limpo. | Leitura. |
| 15 | MEDIUM | `AppManager.js:29-33` | **Contrato com nomes crípticos** (`usr`, `eml`, `pwd`, `c_id`). Ruim, mas é o contrato que os clientes usam; a refatoração preserva. | `api.http`. |
| 16 | LOW | vários | Erro tratado de forma inconsistente (texto puro misturado com JSON, `"Erro DB"` genérico), `console.log` no lugar de logger, erro do insert de auditoria ignorado. | Leitura. |
| 17 | LOW | `AppManager.js:29-33`, `utils.js:6,19,22` | Variáveis de uma letra (`u`, `e`, `p`, `cc`); `10000` e `substring(0, 10)` sem nome; porta 3000 fixa no código. | Leitura. |
| 18 | LOW | `package.json` | ² **Dependências na linha antiga.** `express ^4` (a atual é 5.3.0); `sqlite3 ^5` (a atual é 6.0.1) puxa `prebuild-install`, marcado como descontinuado. | `npm view` e aviso de `deprecated` na instalação. |

### Projeto 3 — task-manager-api (Flask com camadas parciais)

Já tem `models/`, `routes/` (blueprints), `services/` e `utils/`, cerca de 1.150 linhas e mais de 20 endpoints. O problema é que a regra de negócio está nas rotas, os models são anêmicos e o único serviço, `NotificationService`, nunca é chamado. `marshmallow` e `requests` estão no `requirements.txt` sem uso.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `user_routes.py:52,71-78,119-122` | ² **Escalada de privilégio por atribuição em massa.** O cadastro aceita `role: "admin"` de qualquer um, e o update muda o `role` de qualquer usuário. Sem autenticação, qualquer pessoa vira admin. | ² Cadastro com `role: admin` → 201; `PUT /users/2 {"role": "admin"}` → 200. |
| 2 | CRITICAL | `models/user.py:29,32` | **Senha com MD5 sem salt.** Quebra em segundos com tabela pronta; senhas iguais geram o mesmo hash. | O hash de `/users/1` é o MD5 de `1234`. |
| 3 | CRITICAL | `models/user.py:16-25`, `user_routes.py:85,209` | **`to_dict()` inclui a senha**, que sai em `GET /users/<id>`, no cadastro e no login. Somado ao MD5, entrega a senha. | O campo `password` aparece nas três respostas. |
| 4 | CRITICAL | `app.py:13,34`, `services/notification_service.py:10` | **SECRET_KEY e senha de SMTP fixas no código**, e debug ligado em `0.0.0.0` (debugger do Werkzeug na rede). | Leitura. |
| 5 | HIGH | `user_routes.py:185-211` | **Autenticação de fachada.** O login devolve `"fake-jwt-token-" + id`, nenhuma rota valida token e `is_admin()` nunca é chamado. Relatórios administrativos ficam abertos. | `GET /reports/summary` anônimo → 200. |
| 6 | HIGH | `task_routes.py:96,113,182,261,264`, `user_routes.py:125` | **Erro 500 por tipo não tratado.** `priority` como texto, `search?priority=xyz`, ² título numérico, `tags` com item que não é texto e `active: "false"` derrubam a requisição. Deveria ser 400 com mensagem. | `priority: "alta"` → 500; ² `title: 12345` → 500 em HTML; `active: "false"` → 500. |
| 7 | HIGH | `task_routes.py:11-63`, `user_routes.py:153-183`, `report_routes.py` | **Regra de negócio e serialização nas rotas.** A regra de "atrasada" está copiada em cinco lugares, enquanto `Task.is_overdue()` existe e ninguém usa; o `to_dict` é reescrito à mão. Mudar a regra exige achar todas as cópias. | Leitura e contagem das cópias. |
| 8 | HIGH | `task_routes.py:41-57`, `report_routes.py:53-68`, `user_routes.py:22,35` | **Consultas N+1.** `GET /tasks` busca usuário e categoria a cada task; o relatório consulta por usuário; `GET /users` carrega as tasks de cada um. Nenhum join nem carregamento antecipado. | Leitura. |
| 9 | MEDIUM | 16 ocorrências em `routes/` | **`except:` sem tipo** engolindo qualquer erro e devolvendo "Erro interno". A causa real some. | Leitura. |
| 10 | MEDIUM | `task_routes.py:93,113`, `report_routes.py:180`, `helpers.py:52` | ² **Valores inválidos aceitos e gravados.** `priority: 2.7` numa coluna inteira, título só com espaços, cor `"vermelho-escuro-demais"` (o `is_valid_color` existe e não é usado). Dado ruim entra no banco. | ² As três requisições → 201. |
| 11 | MEDIUM | `task_routes.py:31,72,285`, `report_routes.py:35,133` | ² **Task que vence hoje já aparece como atrasada.** O prazo vira meia-noite e é comparado com o horário atual em UTC, sem fuso. | ² `due_date` com a data de hoje → `"overdue": true`. |
| 12 | MEDIUM | `utils/helpers.py:57-108`, `services/notification_service.py` | **Código morto e duplicado.** `process_task_data` valida tudo e a rota reimplementa à mão; ² o serviço de notificação nunca é instanciado; duas dependências sem uso. | Nenhuma chamada no código. |
| 13 | MEDIUM | `task_routes.py:296`, `report_routes.py:67,151` | **Cálculo de percentual repetido**, com a proteção contra divisão por zero reescrita em cada lugar, enquanto `calculate_percentage` existe. | Leitura. |
| 14 | MEDIUM | `app.py:15` | **CORS aberto para qualquer origem**, numa API que deveria exigir autenticação. | Leitura. |
| 15 | MEDIUM | `app.py:11,30-31` | **Configuração e criação do banco no import do módulo**, sem factory (`create_app`) e sem migrations. Dificulta teste e troca de ambiente. | Leitura. |
| 16 | MEDIUM | 23 usos de `datetime.utcnow`, 57 de `Model.query` | **APIs deprecated e legadas.** `datetime.utcnow()` é deprecated desde o Python 3.12 (trocar por `datetime.now(timezone.utc)`). A documentação do Flask-SQLAlchemy marca toda a interface `Model.query` como legada; o equivalente é `db.session.get(Model, id)` e `db.session.execute(db.select(...))`. Quebram em um upgrade. | `DeprecationWarning` e `LegacyAPIWarning` emitidos ao rodar; documentação oficial. |
| 17 | LOW | `models/*`, `routes/*` | Imports sem uso (`os`, `sys`, `json`, `time`, `math`, `hashlib`) e `if/else` que devolve booleano em vez de retornar a expressão. | Leitura. |
| 18 | LOW | `user_routes.py:61,106`, `helpers.py:21` | Regex de e-mail repetida em três lugares; números soltos (`4`, `200`, `5`) quando as constantes já existem em `helpers.py`. | Leitura. |
| 19 | LOW | `report_routes.py:157-223` | ² CRUD de categorias dentro do blueprint de relatórios; `PUT /categories/<id>` não checa o corpo e responde erro em HTML, fora do padrão JSON da API. | ² Sem corpo → 415 em HTML. |

### O que a análise ensinou para a skill

Ler o código acha a maior parte dos problemas. O que faltava apareceu ao provocar cada endpoint com uma lista fixa de entradas, que entrou na skill como referência:

1. tipo errado em cada campo (número no lugar de texto e o contrário, lista com item de outro tipo, booleano como texto);
2. o mesmo item repetido numa lista;
3. limites: zero, negativo, fração, vazio, só espaços, tamanho máximo;
4. recurso inexistente em update, delete e mudança de status;
5. transição de estado inválida e efeito colateral que não acontece;
6. campo privilegiado no corpo (`role`, `active`);
7. rota administrativa ou destrutiva sem autenticação;
8. corpo ausente ou malformado, e se o erro vaza stack trace;
9. identidade inferida de dado público, como e-mail;
10. data sem horário comparada com horário em UTC;
11. agregação que conta estados que não deveriam contar.
