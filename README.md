# Skill de auditoria e refatoração arquitetural (`refactor-arch`)

Desafio 03 do MBA em Engenharia de Software com IA da Full Cycle. Este repositório é um fork de [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill), onde está o enunciado original.

A ideia é simples: uma skill do Claude Code, a `/refactor-arch`, que lê um projeto legado, aponta o que está errado com arquivo e linha, para e pergunta se pode seguir, e só então refatora para MVC. No final ela sobe a aplicação e chama os endpoints de novo para provar que nada quebrou. Rodei a mesma versão da skill nos três projetos, sem mudar uma vírgula entre um e outro:

| # | Projeto | Stack | Ponto de partida |
|---|---|---|---|
| 1 | `code-smells-project/` | Python + Flask 3.1, SQLite com SQL à mão | Monólito em 4 arquivos |
| 2 | `ecommerce-api-legacy/` | Node.js + Express 4, SQLite em memória | God class com callbacks aninhados |
| 3 | `task-manager-api/` | Python + Flask 3.0, Flask-SQLAlchemy | Camadas existem, regra de negócio nas rotas |

## Análise Manual

Antes de escrever uma linha da skill, li os três projetos e confirmei cada problema rodando a aplicação numa cópia isolada, com requisição de verdade. Achismo não entra na lista.

Foram duas passadas. Na primeira li o código e testei o óbvio. Na segunda reli linha a linha e provoquei cada endpoint com entrada hostil: tipo errado, item repetido, transição de estado que não deveria existir, recurso que não existe, corpo malformado e campo privilegiado no corpo. O que saiu da segunda passada está marcado com ². E foi bastante coisa, o que já diz muito sobre ler código sem executar.

Usei a escala do enunciado. CRITICAL quebra o funcionamento, expõe dado sensível ou destrói a separação de camadas. HIGH viola MVC/SOLID e trava manutenção e teste. MEDIUM é padronização, duplicação ou performance. LOW é legibilidade, nomes e magic numbers.

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| 1. code-smells-project | 6 | 7 | 7 | 3 | 23 |
| 2. ecommerce-api-legacy | 4 | 6 | 5 | 3 | 18 |
| 3. task-manager-api | 4 | 4 | 8 | 3 | 19 |

Também rodei as ferramentas de auditoria de dependência. O `pip-audit` aponta 4 vulnerabilidades no projeto 1 (flask 3.1.1 e flask-cors 5.0.1; a ferramenta lista cada uma duas vezes, por isso aparecem 8 linhas) e 22 avisos no projeto 3 (flask, flask-cors 4.0.0, marshmallow, requests e python-dotenv). O `npm audit` aponta 14 no projeto 2, duas críticas, em pacotes como `tar`, `proxy-addr` e `path-to-regexp` e na cadeia de instalação do `sqlite3`.

### Projeto 1: code-smells-project (Flask, e-commerce)

`app.py` (88 linhas), `controllers.py` (292), `models.py` (314) e `database.py` (86). Sem camada de serviço nem ORM; todo SQL é montado por concatenação de strings. 19 endpoints para produtos, usuários, pedidos e relatório de vendas.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `models.py:110` e outras 18 queries | SQL injection em todo o acesso a dados. As queries são montadas com `+`. No login, a senha `x' OR '1'='1` entra como admin sem saber a senha. | Login com essa senha → 200 como admin. Busca por `O'Brien` → 500 com erro de SQL. |
| 2 | CRITICAL | `app.py:59-78` | `/admin/query` executa qualquer SQL recebido no corpo, sem autenticação. Quem chega na API lê, altera ou apaga o banco inteiro. | `SELECT email, senha FROM usuarios` → todas as senhas. |
| 3 | CRITICAL | `app.py:47-57` | ² `/admin/reset-db` sem autenticação apaga todas as tabelas. Um POST anônimo zera a loja. | POST → 200; `GET /produtos` volta vazio. |
| 4 | CRITICAL | `database.py:76-78`, `models.py:83,99` | Senhas em texto puro, devolvidas pela API. Um vazamento do banco ou da listagem de usuários entrega as credenciais prontas para uso. | `GET /usuarios` traz o campo `senha` com o valor original. |
| 5 | CRITICAL | `app.py:7-8,88`, `controllers.py:289` | SECRET_KEY fixa no código e debug ligado em `0.0.0.0`. O `/health` devolve a chave no JSON público, o que permite forjar sessões assinadas. O debug expõe o debugger interativo do Werkzeug na rede, protegido só por PIN. | `GET /health` → `secret_key` e `"ambiente": "producao"`. |
| 6 | CRITICAL | `app.py`, `controllers.py`, `models.py` | Sem separação de camadas. `app.py` mistura rotas com dois handlers que fazem SQL; o controller valida, orquestra e monta resposta; `models.py` concentra quatro domínios. Não há como testar uma regra isolada nem mudar uma parte sem mexer nas outras. | Leitura. |
| 7 | HIGH | todas as rotas | ² Nenhuma autenticação nem autorização. O login só devolve os dados do usuário, sem token nem sessão. Qualquer pessoa lista usuários e pedidos e muda o status de um pedido. | `GET /usuarios`, `GET /pedidos` e `PUT /pedidos/1/status` anônimos → 200. |
| 8 | HIGH | `models.py:133-169` | Pedido criado sem transação. Insere o pedido, depois os itens, depois baixa o estoque, em passos soltos. Uma falha no meio deixa pedido sem item ou estoque errado, e duas compras simultâneas vendem a mesma unidade. | Leitura. |
| 9 | HIGH | `models.py:139-146` | ² Estoque checado item a item, não pelo total. O mesmo produto repetido no pedido passa em cada checagem e vende mais do que existe. | Estoque 10, dois itens de 6 do mesmo produto → 201 e estoque -2. |
| 10 | HIGH | `models.py:144,146,164`, `controllers.py:188-201` | Quantidade não validada. Quantidade negativa passa e o estoque aumenta; zero cria pedido de valor zero; fração grava estoque quebrado; texto ou campo ausente derruba a requisição. | `-5` → 201, total -29999.94, estoque 10→15. ² `0` → total 0; `0.5` → estoque 49.5; `"2"` e campo ausente → 500. |
| 11 | HIGH | `controllers.py:237-252`, `models.py:275-283` | ² Status do pedido sem máquina de estados. Qualquer transição vale, inclusive cancelado → aprovado. Cancelar não devolve o estoque (só imprime "Devolver estoque"). Pedido inexistente responde sucesso. | `PUT /pedidos/9999/status` → 200; cancelado → aprovado → 200; estoque não volta. |
| 12 | HIGH | `controllers.py:195-203`, `models.py:149` | Usuário do pedido não é validado. Cria pedido para um `usuario_id` que não existe, gerando dado órfão no faturamento. | `usuario_id: 99999` → 201. |
| 13 | HIGH | `models.py:171-233` | Consulta N+1. A listagem de pedidos faz uma query por pedido e outra por item para buscar o nome do produto. O tempo cresce com o histórico. | Leitura. |
| 14 | MEDIUM | `models.py:235-273` | ² Relatório de vendas soma pedidos cancelados e calcula desconto sobre esse total; a regra de faixas de desconto está na camada de dados. Dinheiro é guardado como `REAL` (ponto flutuante). O número que a gestão vê está errado. | Com um pedido cancelado, ele entra no `faturamento_bruto`. |
| 15 | MEDIUM | `database.py:27-34`, `models.py:122-131` | ² E-mail sem unicidade. O cadastro aceita e-mail repetido, e o login passa a depender de qual linha o banco devolve primeiro. | `POST /usuarios` com `admin@loja.com` → 201. |
| 16 | MEDIUM | `controllers.py:98-107`, `models.py:65-70` | ² Delete físico de produto apaga o histórico. O item do pedido antigo passa a aparecer como "Desconhecido". A coluna `ativo` existe e nenhuma consulta usa. | Depois do delete, o pedido mostra `"produto_nome": "Desconhecido"`. |
| 17 | MEDIUM | `controllers.py:37-54` e `:81-90` | Validação duplicada e divergente. Atualizar produto não checa tamanho do nome nem categoria, que o cadastro checa. A mesma regra em dois lugares já se desencontrou. | Leitura. |
| 18 | MEDIUM | `controllers.py:39,83,119-121,169-170,239-240` | Tipo e corpo não validados. Preço como texto, `preco_max=abc` ou login sem corpo JSON viram erro 500 em vez de 400. O cliente não sabe o que corrigir. | `preco: "abc"` → 500; ² `preco_max=abc` → 500; login sem JSON → 500. |
| 19 | MEDIUM | `controllers.py:208-210,248-250` | Notificação fingida no controller. E-mail, SMS e push são `print`. Nada é enviado, e a notificação está acoplada ao fluxo HTTP. | Leitura. |
| 20 | MEDIUM | `database.py:4,9`, `app.py:9` | Conexão global compartilhada entre threads (`check_same_thread=False`) e CORS aberto para qualquer origem. Concorrência e origem sem controle. | Leitura. |
| 21 | LOW | `controllers.py` (17 ocorrências) | `except Exception` devolvendo `str(e)` ao cliente, que vê detalhe interno, e `print` como log, inclusive com o e-mail de quem tenta logar. | Busca por `O'Brien` expõe o erro de SQL. |
| 22 | LOW | `controllers.py:28,56` e outros | Variável `id` sombreando a função nativa; listas de categorias e status repetidas no meio do código, sem constante. | Leitura. |
| 23 | LOW | `models.py:2`, `database.py:2,5`, `controllers.py:118-121` | ² Imports sem uso; caminho relativo `loja.db` (o banco muda conforme a pasta de onde se roda); `preco_min=0` é ignorado porque zero conta como "vazio". | Leitura. |

### Projeto 2: ecommerce-api-legacy (Express, LMS com checkout)

`app.js` (14 linhas), `AppManager.js` (141) e `utils.js` (25). A classe `AppManager` cria o banco, faz o seed, registra as rotas e implementa toda a regra. 3 endpoints: checkout, relatório financeiro e exclusão de usuário.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `AppManager.js:46,68` | ² Uma requisição derruba o servidor. `card` ou `pwd` enviados como número quebram `cc.startsWith` e `Buffer.from(pwd)` dentro do callback do SQLite. O Express 4 não captura erro lançado em callback assíncrono, e o processo Node termina. | `card` numérico → sem resposta, processo encerrado; `pwd: 123` → idem. |
| 2 | CRITICAL | `utils.js:2-6` | Credenciais de produção no código: senha do banco, chave `pk_live` do gateway e usuário de SMTP. Quem tem acesso ao repositório tem acesso a tudo. | Leitura. |
| 3 | CRITICAL | `AppManager.js:45` | Número do cartão e chave do gateway impressos no log. Log costuma ir para ferramentas com acesso amplo; isso quebra qualquer exigência de PCI. | Log real com o cartão completo e a chave `pk_live`. |
| 4 | CRITICAL | `utils.js:17-23` | `badCrypto` não é hash. Repete o base64 dos dois primeiros caracteres da senha e corta em 10. É reversível e senhas diferentes colidem. | Leitura. |
| 5 | HIGH | `AppManager.js:40,73-75` | ² Checkout com e-mail existente usa a conta sem pedir senha. Quem sabe o e-mail de alguém matricula e cobra em nome dessa pessoa; o nome enviado é ignorado. | Checkout com o e-mail do usuário do seed, sem senha → 200, e ele aparece matriculado no curso. |
| 6 | HIGH | `AppManager.js:80,131` | ² Rotas administrativas abertas. O relatório financeiro expõe nome de aluno e valor pago; `DELETE /api/users/:id` apaga qualquer usuário. | Ambos anônimos → 200. |
| 7 | HIGH | `AppManager.js:46-48` | O "pagamento" é `cc.startsWith("4")`. Qualquer texto que comece com 4 é aprovado, sem gateway e sem validação. Pagamento recusado não deixa registro. | `card: "4-nao-e-cartao"` → 200 e pagamento `PAID`. |
| 8 | HIGH | `AppManager.js:28-78` | Checkout sem idempotência nem transação. Repetir o POST cria matrícula e cobrança duplicadas; falha entre matrícula, pagamento e auditoria deixa registro pela metade. | Mesmo payload duas vezes → 2 matrículas. |
| 9 | HIGH | `AppManager.js:131-137` | Excluir usuário deixa matrículas e pagamentos órfãos (a própria resposta admite). ² O erro é ignorado e o número de linhas afetadas não é checado: usuário inexistente também responde sucesso. | `DELETE /api/users/1` → 200 "…ficaram sujos no banco"; ² `/users/9999` → 200. |
| 10 | HIGH | `AppManager.js` inteiro | God class com callbacks aninhados. Banco, seed, rotas e regra na mesma classe; checkout com quatro níveis de callback e `self`/`this` misturados. Nada pode ser testado nem trocado isoladamente. | Leitura. |
| 11 | MEDIUM | `AppManager.js:80-129` | Relatório com N+1 e contadores manuais para esperar os callbacks. ² Nenhum `err` é checado: se uma query falhar, `enrollments.length` lança e derruba o processo. A ordem dos alunos muda a cada chamada. | Uma query por curso, por matrícula, por usuário e por pagamento. |
| 12 | MEDIUM | `AppManager.js:35,68` | Validação de entrada fraca. Checa presença, não tipo nem formato de e-mail e cartão. ² Sem `pwd`, a conta nasce com a senha padrão `123456`. | ² Checkout sem `pwd` → 200, usuário criado com senha conhecida. |
| 13 | MEDIUM | `app.js:6` | ² JSON malformado devolve página HTML com stack trace e o caminho absoluto do servidor, porque o handler de erro padrão do Express roda sem `NODE_ENV=production`. | Corpo `{"usr":` → 400 em HTML com `SyntaxError … at JSON.parse`. |
| 14 | MEDIUM | `utils.js:9-14`, `AppManager.js:2` | Estado global mutável exportado (`globalCache`, `totalRevenue`, este nunca usado). ² O cache cresce a cada checkout e nunca é limpo. | Leitura. |
| 15 | MEDIUM | `AppManager.js:29-33` | Contrato com nomes crípticos (`usr`, `eml`, `pwd`, `c_id`). Ruim, mas é o contrato que os clientes usam; a refatoração preserva. | `api.http`. |
| 16 | LOW | vários | Erro tratado de forma inconsistente (texto puro misturado com JSON, `"Erro DB"` genérico), `console.log` no lugar de logger, erro do insert de auditoria ignorado. | Leitura. |
| 17 | LOW | `AppManager.js:29-33`, `utils.js:6,19,22` | Variáveis de uma letra (`u`, `e`, `p`, `cc`); `10000` e `substring(0, 10)` sem nome; porta 3000 fixa no código. | Leitura. |
| 18 | LOW | `package.json` | ² Dependências na linha antiga. `express ^4` (a atual é 5.3.0); `sqlite3 ^5` (a atual é 6.0.1) puxa `prebuild-install`, marcado como descontinuado. | `npm view` e aviso de `deprecated` na instalação. |

### Projeto 3: task-manager-api (Flask com camadas parciais)

Já tem `models/`, `routes/` (blueprints), `services/` e `utils/`, cerca de 1.150 linhas e mais de 20 endpoints. O problema é que a regra de negócio está nas rotas, os models são anêmicos e o único serviço, `NotificationService`, nunca é chamado. `marshmallow` e `requests` estão no `requirements.txt` sem uso.

| # | Sev | Onde | Problema e por que importa | Evidência |
|---|---|---|---|---|
| 1 | CRITICAL | `user_routes.py:52,71-78,119-122` | ² Escalada de privilégio por atribuição em massa. O cadastro aceita `role: "admin"` de qualquer um, e o update muda o `role` de qualquer usuário. Sem autenticação, qualquer pessoa vira admin. | ² Cadastro com `role: admin` → 201; `PUT /users/2 {"role": "admin"}` → 200. |
| 2 | CRITICAL | `models/user.py:29,32` | Senha com MD5 sem salt. Quebra em segundos com tabela pronta; senhas iguais geram o mesmo hash. | O hash de `/users/1` é o MD5 de `1234`. |
| 3 | CRITICAL | `models/user.py:16-25`, `user_routes.py:85,209` | `to_dict()` inclui a senha, que sai em `GET /users/<id>`, no cadastro e no login. Somado ao MD5, entrega a senha. | O campo `password` aparece nas três respostas. |
| 4 | CRITICAL | `app.py:13,34`, `services/notification_service.py:10` | SECRET_KEY e senha de SMTP fixas no código, e debug ligado em `0.0.0.0` (debugger do Werkzeug na rede). | Leitura. |
| 5 | HIGH | `user_routes.py:185-211` | Autenticação de fachada. O login devolve `"fake-jwt-token-" + id`, nenhuma rota valida token e `is_admin()` nunca é chamado. Relatórios administrativos ficam abertos. | `GET /reports/summary` anônimo → 200. |
| 6 | HIGH | `task_routes.py:96,113,182,261,264`, `user_routes.py:125` | Erro 500 por tipo não tratado. `priority` como texto, `search?priority=xyz`, ² título numérico, `tags` com item que não é texto e `active: "false"` derrubam a requisição. Deveria ser 400 com mensagem. | `priority: "alta"` → 500; ² `title: 12345` → 500 em HTML; `active: "false"` → 500. |
| 7 | HIGH | `task_routes.py:11-63`, `user_routes.py:153-183`, `report_routes.py` | Regra de negócio e serialização nas rotas. A regra de "atrasada" está copiada em cinco lugares, enquanto `Task.is_overdue()` existe e ninguém usa; o `to_dict` é reescrito à mão. Mudar a regra exige achar todas as cópias. | Leitura e contagem das cópias. |
| 8 | HIGH | `task_routes.py:41-57`, `report_routes.py:53-68`, `user_routes.py:22,35` | Consultas N+1. `GET /tasks` busca usuário e categoria a cada task; o relatório consulta por usuário; `GET /users` carrega as tasks de cada um. Nenhum join nem carregamento antecipado. | Leitura. |
| 9 | MEDIUM | 16 ocorrências em `routes/` | `except:` sem tipo engolindo qualquer erro e devolvendo "Erro interno". A causa real some. | Leitura. |
| 10 | MEDIUM | `task_routes.py:93,113`, `report_routes.py:180`, `helpers.py:52` | ² Valores inválidos aceitos e gravados. `priority: 2.7` numa coluna inteira, título só com espaços, cor `"vermelho-escuro-demais"` (o `is_valid_color` existe e não é usado). Dado ruim entra no banco. | ² As três requisições → 201. |
| 11 | MEDIUM | `task_routes.py:31,72,285`, `report_routes.py:35,133` | ² Task que vence hoje já aparece como atrasada. O prazo vira meia-noite e é comparado com o horário atual em UTC, sem fuso. | ² `due_date` com a data de hoje → `"overdue": true`. |
| 12 | MEDIUM | `utils/helpers.py:57-108`, `services/notification_service.py` | Código morto e duplicado. `process_task_data` valida tudo e a rota reimplementa à mão; ² o serviço de notificação nunca é instanciado; duas dependências sem uso. | Nenhuma chamada no código. |
| 13 | MEDIUM | `task_routes.py:296`, `report_routes.py:67,151` | Cálculo de percentual repetido, com a proteção contra divisão por zero reescrita em cada lugar, enquanto `calculate_percentage` existe. | Leitura. |
| 14 | MEDIUM | `app.py:15` | CORS aberto para qualquer origem, numa API que deveria exigir autenticação. | Leitura. |
| 15 | MEDIUM | `app.py:11,30-31` | Configuração e criação do banco no import do módulo, sem factory (`create_app`) e sem migrations. Dificulta teste e troca de ambiente. | Leitura. |
| 16 | MEDIUM | 23 usos de `datetime.utcnow`, 57 de `Model.query` | APIs deprecated e legadas. `datetime.utcnow()` é deprecated desde o Python 3.12 (trocar por `datetime.now(timezone.utc)`). A documentação do Flask-SQLAlchemy marca toda a interface `Model.query` como legada; o equivalente é `db.session.get(Model, id)` e `db.session.execute(db.select(...))`. Quebram em um upgrade. | `DeprecationWarning` e `LegacyAPIWarning` emitidos ao rodar; documentação oficial. |
| 17 | LOW | `models/*`, `routes/*` | Imports sem uso (`os`, `sys`, `json`, `time`, `math`, `hashlib`) e `if/else` que devolve booleano em vez de retornar a expressão. | Leitura. |
| 18 | LOW | `user_routes.py:61,106`, `helpers.py:21` | Regex de e-mail repetida em três lugares; números soltos (`4`, `200`, `5`) quando as constantes já existem em `helpers.py`. | Leitura. |
| 19 | LOW | `report_routes.py:157-223` | ² CRUD de categorias dentro do blueprint de relatórios; `PUT /categories/<id>` não checa o corpo e responde erro em HTML, fora do padrão JSON da API. | ² Sem corpo → 415 em HTML. |

### O que a análise ensinou para a skill

Ler o código acha a maior parte dos problemas. O resto só aparece quando você provoca a aplicação. Por isso a lista de entradas que usei na segunda passada virou uma referência da skill (`hostile-inputs.md`), e ela roda essas sondas em todo projeto:

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

## Construção da Skill

Para desenhar a skill, voltei nas aulas de skills do MBA (IA Labs e Desenvolvimento com IA) e li as duas páginas da Anthropic sobre o assunto: a documentação de skills do Claude Code e o guia de boas práticas de escrita. Três ideias guiaram tudo o que vem abaixo.

- O `SKILL.md` é um roteador, não uma enciclopédia. Ele diz o que fazer em cada fase e manda ler a referência certa na hora certa.
- O que precisa ser exato vira script. A IA pode dizer que procurou em tudo e ter procurado em 30%. O script procura em 100%, sempre do mesmo jeito.
- Ninguém declara sucesso sem prova. A Fase 3 só termina quando a aplicação sobe e cada endpoint responde como antes, a não ser onde a mudança corrige um achado e foi declarada.

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                          # 163 linhas: regras, as 3 fases e o checklist de progresso
├── references/
│   ├── project-analysis.md           # Fase 1: detectar stack, mapear arquitetura, montar o plano de teste
│   ├── antipatterns-catalog.md       # Fase 2: 27 anti-patterns, com sinal de detecção e severidade
│   ├── hostile-inputs.md             # Fase 2: as entradas hostis que viram sondas
│   ├── report-template.md            # Fase 2: formato do relatório
│   ├── mvc-guidelines.md             # Fase 3: o que vai em model, view/rota e controller
│   ├── refactoring-playbook.md       # Fase 3: 15 transformações com código antes/depois
│   └── stacks/flask.md · express.md · generic.md   # Fase 3: só o guia da stack detectada
├── scripts/
│   ├── inventory.py                  # fatos da Fase 1: manifestos, linhas, endpoints, tabelas, entrada
│   ├── scan_signals.py               # sinais da Fase 2 com arquivo:linha (segredo sai mascarado)
│   └── smoke.py                      # baseline antes, compare depois (exit 0 verde, exit 2 vermelho)
└── evals/evals.json                  # o que se espera da skill em cada um dos 3 projetos
```

As cinco áreas que o enunciado pede estão nos cinco primeiros arquivos de `references/`. O `hostile-inputs.md` e os guias de stack foram além do pedido, e explico o porquê mais abaixo.

### Script × IA

Depois da análise, e somando a experiência que tenho na construção de outros agentes de refatoração, optei por separar bem as duas coisas: extrair e conferir é trabalho de script, interpretar é trabalho de IA. Aqui ficou assim:

| Etapa | Quem faz | Por quê |
|---|---|---|
| Inventário (arquivos, linhas, dependências, endpoints, tabelas) | `inventory.py` | É contagem. Tem que dar o mesmo número toda vez. |
| Sinais de anti-pattern com arquivo:linha | `scan_signals.py` | Regex, AST e detectores de N+1, duplicação e import sem uso. Varre tudo. |
| Confirmar se o sinal é problema e dar severidade | IA | Sinal é pista. Precisa ler o trecho para saber se é falso positivo. |
| God class, regra no controller, transação, máquina de estados | IA | Não tem regex que pegue. Só lendo o arquivo inteiro. |
| Sondas (entradas hostis) | IA escreve, `smoke.py` executa | Escolher o que testar é julgamento; executar e registrar é mecânico. |
| Desenhar o MVC e corrigir o código | IA | É o trabalho criativo da refatoração. |
| Validar que nada quebrou | `smoke.py compare` | Exit 0 ou 2, com um bloco por violação. A IA corrige e roda de novo, no máximo 3 vezes, e depois pergunta. |

Os scripts só usam a biblioteca padrão do Python, então rodam em qualquer máquina com `python3`, inclusive para auditar um projeto Node.

### Proteções

Uma skill que reescreve o projeto inteiro precisa de freio. Estas são as travas:

- `disable-model-invocation: true`. O Claude não dispara a skill sozinho; só roda quando alguém digita `/refactor-arch`.
- As Fases 1 e 2 não escrevem nada no projeto. Ambiente, plano, baseline e relatório ficam numa pasta de trabalho fora dele (`$TMPDIR/refactor-arch/<projeto>`).
- Pausa obrigatória no fim da Fase 2. Sem um "y" explícito, não tem Fase 3.
- Antes de mexer, a skill confere se o Git do projeto está limpo e anota o commit, para ter ponto de volta.
- A aplicação sobe numa cópia temporária, numa porta livre, com o banco da cópia. O banco original nunca é tocado.
- Segredo nunca aparece na saída. O relatório cita `arquivo:linha` e o nome da variável, nunca o valor. Conferi isso por script nos 3 relatórios: nenhum valor de chave, senha ou credencial dos projetos aparece neles.
- A skill não faz commit nem push. Quem decide é quem revisa.

### O catálogo de anti-patterns

São 27 entradas, todas com severidade padrão, quando ela sobe ou desce, o sinal que o script emite e qual transformação do playbook corrige. A escolha seguiu um critério simples: cada anti-pattern apareceu em pelo menos um dos três projetos na análise manual, ou é muito comum em código legado da mesma família.

| Grupo | Anti-patterns | Por que entrou |
|---|---|---|
| Segurança | SQL concatenado, SQL vindo do cliente, credencial no código, debug exposto, senha insegura, autenticação ausente ou falsa, dado sensível em log | São os CRITICAL dos três projetos. Login com `' OR '1'='1`, cartão inteiro no log, MD5 sem salt. |
| Robustez | Erro que vaza ou derruba o processo, estado global, CORS aberto, entrada sem validação, efeito colateral fingido, `print` como log, configuração no import | Foi onde as sondas mais acharam coisa: 500 para entrada de cliente, processo Node caindo com um número no lugar de texto. |
| Arquitetura | God class, regra de negócio na rota, várias escritas sem transação, integridade não garantida, status sem máquina de estados | É o coração do MVC. Nenhum desses tem sinal de regex, por isso a skill manda ler os arquivos principais por inteiro. |
| Qualidade | Callback hell, N+1, código morto, lógica duplicada, magic numbers, nomes ruins | Os MEDIUM e LOW que travam a manutenção do dia a dia. |
| Dependências | API deprecated (AP16) e dependência vulnerável (AP27) | O enunciado pede deprecated. O AP16 tem uma tabela com o equivalente moderno (`datetime.utcnow()`, `Model.query.get`, `new Buffer()`, `req.param()` do Express...) e, se o MCP Context7 estiver conectado, a skill confirma na documentação da versão declarada. |

O playbook tem 15 transformações (T1 a T15), cada uma com o código antes e depois em Python e, quando muda, em Node: query parametrizada, config por ambiente, hash de senha, god file para camadas, regra para o controller, transação, validação com 400, error handler central, callback para async/await, N+1 para JOIN, estado global para dependência injetada, API deprecated, rota perigosa removida ou protegida, log sem dado sensível e máquina de estados.

### Como garanti que é agnóstica

- Nada no `SKILL.md` fala de Flask ou Express. A stack sai do `inventory.py`, que lê o manifesto (`requirements.txt`, `package.json`, `pyproject.toml`, `go.mod`...) e o código.
- O conhecimento específico fica em `references/stacks/`, e a skill lê só o guia da stack detectada. Se não for Flask nem Express, cai no `generic.md`, que traz os princípios sem receita pronta.
- A Fase 1 classifica o projeto em três graus: A (monólito), B (camadas parciais) e C (organizado). Cada grau muda o que a Fase 3 faz. O projeto 3 é B, e a skill sabe que lá o trabalho é mover regra para o lugar certo, não criar tudo do zero.
- Os caminhos dos scripts usam `${CLAUDE_SKILL_DIR}`, então a pasta funciona em qualquer projeto sem ajuste.
- As três cópias são idênticas. Conferi com `diff -r` antes de cada commit.

### Desafios e como resolvi

#### A primeira execução real falhou em três pontos

Rodei a skill no projeto 1 e ela não imprimiu o resumo da Fase 1, propôs exigir login em todas as rotas de cliente (fora do escopo) e colocou views e controllers na mesma pasta. Ler o `SKILL.md` não mostrava nada disso. Ajustei o texto, rodei de novo, e as três falhas sumiram. Ou seja, skill se testa rodando, igual código.

#### Corrigir bug × preservar o contrato

As aulas de refatoração dizem para travar o comportamento atual antes de mexer. Só que o desafio pede para corrigir SQL injection, e isso muda o comportamento de propósito. A saída foi o baseline: o `smoke.py` grava como cada endpoint responde hoje, e na Fase 3 a skill só pode mudar uma expectativa no `plan.json` se ligar a mudança a um achado do relatório. Afrouxar o plano para a validação passar é proibido. Conferi isso nos três planos.

#### O escopo tem limite

Corrigir tudo o que é CRITICAL e HIGH às vezes muda a API para quem usa. Exigir login nas rotas de cliente fecha um achado, mas quebra todo cliente atual. A regra 5 da skill separa as duas coisas: o que muda o contrato além do necessário vai para "melhorias propostas" no relatório, não para o código.

#### Porta 5000 ocupada no macOS

O receptor do AirPlay usa a porta 5000, a mesma que os projetos 1 e 3 fixam no código. O `smoke.py` sempre sobe a aplicação numa porta livre e, para o código original que ignora `PORT`, o plano usa `flask --app app run -p <porta>`. Depois da refatoração, `python app.py` passa a ler `PORT`.

#### npm novo bloqueia o script de instalação do `sqlite3`

O npm 11 só roda script de instalação de pacote aprovado, e o `sqlite3` 5 precisa do dele para baixar o binário nativo. Na minha máquina o binário já existia de uma instalação antiga e tudo subiu, o que esconde o problema. Testei numa cópia limpa, sem o binário: o `require('sqlite3')` falha. Deixei no "Como Executar" os dois comandos que resolvem.

#### Pausa em modo não interativo

Com `claude -p` não existe `AskUserQuestion`. A skill imprime a pergunta e encerra o turno, e a confirmação vem retomando a mesma sessão com `--resume <id> "y"`. Foi assim que rodei os três projetos, para ter o log completo de cada execução.

#### `allowed-tools` com `Bash` aberto

A documentação sugere regras estreitas, como `Bash(python3 *)`. Deixei `Bash` aberto porque a skill precisa rodar `pip`, `npm` e `git` do próprio projeto, e o caminho da minha pasta local tem espaços e acento, o que quebra as regras por prefixo. O risco fica limitado porque a skill só roda quando chamada e a Fase 3 depende da confirmação.

#### Context7 sem permissão

Na primeira rodada em modo não interativo, o MCP Context7 estava conectado, mas a ferramenta não estava liberada, e a skill seguiu só com a tabela do catálogo (e disse isso no relatório, como manda a regra). Nos projetos 2 e 3 liberei as duas ferramentas do Context7, e ela confirmou na documentação que o Express 4 do projeto 2 não usa API removida e que `Model.query` é a interface legada do Flask-SQLAlchemy.

## Resultados

Rodei a skill de verdade nos três projetos, com Claude Code 2.1.286 e o modelo Opus 5.5, em modo não interativo (`claude -p "/refactor-arch"`) para guardar o log completo de cada execução. Os relatórios em `reports/` são a saída real da Fase 2, copiados da pasta de trabalho sem edição. O código de cada projeto é a saída real da Fase 3.

### Findings por severidade

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|
| 1. code-smells-project | 7 | 8 | 6 | 5 | 26 | [audit-project-1.md](reports/audit-project-1.md) |
| 2. ecommerce-api-legacy | 6 | 9 | 2 | 4 | 21 | [audit-project-2.md](reports/audit-project-2.md) |
| 3. task-manager-api | 4 | 5 | 9 | 6 | 24 | [audit-project-3.md](reports/audit-project-3.md) |

Comparei com a minha análise manual. Todos os problemas CRITICAL e HIGH que eu achei na mão aparecem nos relatórios da skill. E ela achou coisa que eu não tinha visto, principalmente no projeto 3:

- a busca não escapa `%` e `_`, então `?q=_` devolve todas as tasks;
- o relatório de "concluídas nos últimos 7 dias" conta qualquer task concluída que foi editada na semana, não a que foi concluída na semana;
- `category_id: 0` é gravado como se a categoria existisse.

A diferença de contagem entre a análise manual e o relatório vem mais da forma de agrupar do que de achado novo. A skill junta num achado só o que eu tinha separado em dois, e o contrário também acontece.

### Antes e depois da estrutura

| Projeto | Antes | Depois |
|---|---|---|
| 1 | 4 arquivos na raiz, 780 linhas. `models.py` com 314 linhas e 4 domínios. | `app.py` + `src/` com `config/`, `models/`, `views/`, `controllers/`, `services/`, `middlewares/`, `utils/`. 33 arquivos, 1.133 linhas, o maior com 146. |
| 2 | 3 arquivos, 180 linhas. `AppManager.js` com banco, seed, rotas e regra. | `src/` com `config/`, `database/`, `models/`, `services/`, `controllers/`, `routes/`, `middlewares/`, `utils/` e `createApp.js` como composition root. 23 arquivos, 590 linhas, o maior com 57. |
| 3 | 15 arquivos, 1.158 linhas. Pastas existiam, mas `task_routes.py` (299 linhas) fazia tudo. | `app.py` e `seed.py` + `src/` com `config/`, `models/`, `views/`, `controllers/`, `services/`, `middlewares/`, `utils/`. 35 arquivos, 1.312 linhas, o maior com 154. |

O número de linhas subiu nos três. Faz sentido: entrou validação, tratamento de erro, transação e autenticação que não existiam. O que importa é que nenhum arquivo concentra tudo de novo.

### Validação

O gate da Fase 3 é o `smoke.py compare`: sobe a aplicação refatorada numa cópia limpa, repete as mesmas requisições do baseline e compara status e formato de cada resposta. Depois que a skill terminou, rodei o gate de novo por conta própria, com o mesmo plano, e deu verde nos três.

| Projeto | Requisições conferidas | Sondas corrigidas | Sinais de anti-pattern | Vulnerabilidades em dependências |
|---|---|---|---|---|
| 1 | 49/49 | 19/19 | 121 → 6 (justificados) | 4 → 0 (`pip-audit`) |
| 2 | 18/18, nenhum processo caiu | 12/12 | 36 → 10 (justificados) | 14 → 7 (`npm audit`; as de runtime fecharam, sobram as da instalação do `sqlite3` 5) |
| 3 | 59/59 | 20/20 | 157 → 14 (justificados) | 22 avisos → 0 (`pip-audit`); `marshmallow` e `requests` saíram por não serem usados |

Os logs estão em [`docs/evidencias/`](docs/evidencias/): para cada projeto, a saída do gate (`projeto-N-gate.txt`) e a aplicação rodando a partir de uma cópia limpa, com o comando do README e chamadas de exemplo (`projeto-N-rodando.txt`). Alguns trechos do projeto 2, que antes caía com um número no lugar de texto:

```
$ curl -X POST /api/checkout -d '{"usr":"Joao","eml":"joao@exemplo.com","pwd":"x1","c_id":1,"card":4111222233334444}'
card deve ter de 13 a 19 dígitos
  → HTTP 400
$ curl -X GET /api/admin/financial-report
Não autorizado
  → HTTP 401
```

E do projeto 1, onde o login com injeção de SQL entrava como admin:

```
$ curl -X POST /login -d '{"email":"admin@loja.com' --","senha":"x"}'
{"erro":"Email ou senha inv\u00e1lidos","sucesso":false}
  → HTTP 401
```

### Checklist de validação

| Item | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| **Fase 1** | | | |
| Linguagem detectada | ✅ Python | ✅ JavaScript (Node 24) | ✅ Python |
| Framework detectado | ✅ Flask 3.1.1 | ✅ Express 4 (lock 4.22.1) | ✅ Flask 3.0.0 + Flask-SQLAlchemy |
| Domínio descrito | ✅ e-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Número de arquivos condiz | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2** | | | |
| Segue o template | ✅ | ✅ | ✅ |
| Arquivo e linhas em cada finding | ✅ | ✅ | ✅ |
| Ordenado de CRITICAL a LOW | ✅ | ✅ | ✅ |
| Pelo menos 5 findings | ✅ 26 | ✅ 21 | ✅ 24 |
| APIs deprecated | ✅ checado, nenhum uso | ✅ checado no Context7, nenhum uso | ✅ `datetime.utcnow`, `Model.query` |
| Pausa antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** | | | |
| Estrutura MVC | ✅ | ✅ | ✅ |
| Config extraída, sem valor fixo | ✅ `src/config/settings.py` + `.env.example` | ✅ `src/config/index.js` + `.env.example` | ✅ `src/config/settings.py` + `.env.example` |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/routes separadas | ✅ `src/views/` | ✅ `src/routes/` | ✅ `src/views/` |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `python app.py` | ✅ `npm start` | ✅ `python seed.py && python app.py` |
| Aplicação inicia sem erro | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 19 endpoints | ✅ 3 endpoints | ✅ 22 endpoints |

### Mudanças de comportamento que fiz de propósito

Corrigir falha de segurança muda resposta, não tem para onde correr. Cada mudança abaixo está ligada a um achado do relatório e foi declarada no plano antes do gate rodar:

- **Projeto 1:** `/health` não devolve mais a `secret_key`; `/usuarios` não devolve mais `senha`; `/admin/query` foi removido; `/admin/reset-db` exige `X-Admin-Token`; entrada inválida responde 400 em vez de 500; cancelar pedido devolve o estoque e o faturamento não conta cancelados.
- **Projeto 2:** as duas rotas administrativas exigem `Authorization: Bearer $ADMIN_TOKEN`; checkout com e-mail de outra pessoa exige a senha dela; matrícula repetida responde 409; excluir usuário apaga matrículas e pagamentos junto, sem deixar órfão.
- **Projeto 3:** `password` sai das respostas; o token do login passa a ser assinado e expira; criar usuário com `role` privilegiado, alterar outro usuário ou excluir exige token e permissão; erros saem em JSON.

O que mudaria o contrato além do necessário ficou como proposta no relatório: login nas rotas de cliente, paginação, exclusão lógica, troca de major de dependência, entre outras.

### Como a skill se comportou em cada stack

#### Flask monólito (projeto 1)

Foi onde a skill mais criou estrutura. O guia de Flask levou a uma factory `create_app()` com blueprints, e `python app.py` continuou sendo a entrada, agora lendo `HOST`, `PORT` e `FLASK_DEBUG` do ambiente. A parte mais delicada foi a migração das senhas: o banco antigo tem senha em texto puro, e a skill converteu para hash no boot sem quebrar o login de quem já existia. Ela testou isso numa cópia com um banco no formato antigo.

#### Express (projeto 2)

Aqui o problema era o callback hell. A skill transformou o `sqlite3` em Promise, criou uma transação com fila (o SQLite em memória tem uma conexão só) e trocou tudo por `async/await`. Com isso, um erro lançado dentro da regra chega no error handler em vez de derrubar o processo. O contrato estranho (`usr`, `eml`, `pwd`, `c_id`) ficou como estava, porque é o que os clientes usam.

#### Flask com camadas parciais (projeto 3)

A skill reconheceu o grau B e não jogou nada fora à toa. Os models ganharam a regra que estava nas rotas: a de "atrasada" estava copiada em cinco lugares e virou um `Task.is_overdue()` só. As APIs deprecated foram trocadas pelo equivalente atual, e o import roda com `-W error::DeprecationWarning` sem aviso. O N+1 caiu para um número fixo de queries com `selectinload`.

Choque de realidade: a skill não acertou tudo de primeira. No projeto 2, a primeira rodada do gate deu vermelho por uma limitação do meu `smoke.py`. Ao comparar uma lista, ele junta os itens, e o último sobrescreve os anteriores; como a ordem do relatório financeiro mudou de propósito, o curso sem alunos ficou por último e os campos de aluno "sumiram". A skill investigou, viu que os campos estavam na resposta, mudou a ordem de duas requisições no plano e refez o baseline no código original. Conferi o plano antes e depois: as mesmas 18 requisições, nenhuma expectativa afrouxada. Ficou anotado como melhoria do script.

### Extra: o mesmo projeto em três modelos

A Anthropic recomenda testar uma skill com Haiku, Sonnet e Opus, porque o que funciona num modelo pode não funcionar no outro. Rodei as Fases 1 e 2 no projeto 1, em cópias isoladas, com a mesma skill:

| | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|
| Findings | 26 | 24 | 29 |
| Requisições no baseline (sondas) | 49 (19) | 35 (14) | 39 (19) |
| Anti-patterns distintos do catálogo | 26 | 24 | 26 |
| Tempo | 6min19s | 2min53s | 6min53s |
| Tokens de saída | 41 mil | 26 mil | 88 mil |
| Custo equivalente em API | US$ 2,00 | US$ 0,86 | não informado |
| Imprimiu a Fase 1 e parou na pausa sem mexer no projeto | ✅ | ✅ | ✅ |
| Vazou valor de segredo | não | não | não |

O que tirei disso:

- Os três seguiram o processo. Fase 1 impressa, relatório no template, pausa respeitada, nenhum arquivo alterado e nenhum segredo copiado. Isso é mérito do `SKILL.md` e dos scripts, não do modelo.
- O Sonnet entregou mais por menos. Levou metade do tempo e menos da metade do custo. O que ficou para trás: a falta de autenticação nas rotas de cliente apareceu só como melhoria proposta, não como achado, e o N+1 saiu como MEDIUM, quando o laço aninhado justifica HIGH. Para uma auditoria rápida, serve bem.
- O Haiku achou mais, e isso não quer dizer melhor. Ele quebrou o mesmo problema em dois (máquina de estados, integridade e validação aparecem duas vezes cada), gastou o dobro de tokens do Opus e, para contornar a porta fixa, escreveu um shim que troca o `Flask.run` em tempo de execução, em vez de usar o `flask run -p` que o guia sugere. Também parou para pedir uma decisão que a regra de escopo da skill já respondia.
- O Opus ficou com a classificação mais coerente e foi o único a ir além da sonda para provar um efeito colateral: conferiu numa cópia do banco que o estoque não volta depois do cancelamento. Por isso usei o Opus nas execuções oficiais.

O custo do Haiku não aparece porque a versão do Claude Code que usei ainda não tinha o preço dele na tabela.

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.claude.com/en/docs/claude-code) instalado e logado. Usei a versão 2.1.286 com o modelo Opus 5.5.
- Python 3.9 ou mais novo e `git`. Os scripts da skill só usam a biblioteca padrão; os projetos 1 e 3 pedem o 3.9 por causa do Flask 3.1.
- Para o projeto 2, Node.js 18 ou mais novo (usei o 24).
- Opcional: o MCP [Context7](https://github.com/upstash/context7) conectado no Claude Code, para a skill confirmar APIs deprecated na documentação oficial.

### Rodar a skill

Cada projeto tem a sua cópia da skill em `.claude/skills/refactor-arch/`. Para rodar no estado original, volte o projeto para o commit anterior à refatoração (o `2660340`) numa pasta separada, por exemplo com `git worktree add ../original 2660340`.

```bash
cd code-smells-project            # ou ecommerce-api-legacy, ou task-manager-api
claude "/refactor-arch"
```

A skill imprime o resumo da Fase 1, o relatório da Fase 2 e para em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. Respondendo `y`, ela refatora e valida.

Em modo não interativo, que foi como gerei os relatórios deste repositório:

```bash
claude -p "/refactor-arch" --model claude-opus-5-5 --output-format stream-json --verbose \
  --permission-mode acceptEdits --allowedTools "Bash Read Grep Glob Write Edit" \
  --add-dir "$TMPDIR/refactor-arch" > fase12.jsonl
# pegue o session_id da primeira linha do fase12.jsonl e confirme a Fase 3:
claude -p "y" --resume <session_id> --model claude-opus-5-5 --output-format stream-json --verbose \
  --permission-mode acceptEdits --allowedTools "Bash Read Grep Glob Write Edit" \
  --add-dir "$TMPDIR/refactor-arch" > fase3.jsonl
```

Para liberar o Context7, acrescente `mcp__plugin_context7_context7__resolve-library-id mcp__plugin_context7_context7__query-docs` ao `--allowedTools` (o prefixo muda conforme o nome do servidor na sua instalação).

### Rodar os projetos refatorados

**Projeto 1** (porta padrão 5000; no macOS, se o AirPlay estiver usando a 5000, troque com `PORT`):

```bash
cd code-smells-project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PORT=5001 python app.py
```

**Projeto 2:**

```bash
cd ecommerce-api-legacy
npm install
ADMIN_TOKEN=um-token-qualquer npm start      # http://localhost:3000
```

Se o npm 11 avisar que não rodou o script de instalação do `sqlite3` e a aplicação reclamar de `bindings`, aprove e recompile:

```bash
npm install-scripts approve sqlite3 && npm rebuild sqlite3
```

**Projeto 3:**

```bash
cd task-manager-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
PORT=5002 python app.py
```

As variáveis de cada projeto estão no `.env.example` dele. Nenhuma é obrigatória para rodar localmente; sem `SECRET_KEY`, a aplicação gera uma chave aleatória a cada boot e avisa no log.

### Como validar

1. **Subir e chamar.** Os comandos acima, mais os exemplos do `api.http` (projeto 2) ou do README de cada projeto. As chamadas que usei estão nos arquivos `docs/evidencias/projeto-N-rodando.txt`.
2. **Repetir o gate.** O `smoke.py` compara a aplicação com o baseline gravado antes da refatoração. Ele precisa do `plan.json` e do `baseline.json` que a skill deixa na pasta de trabalho (`$TMPDIR/refactor-arch/<projeto>`):

   ```bash
   python3 .claude/skills/refactor-arch/scripts/smoke.py compare \
     --plan "$TMPDIR/refactor-arch/<projeto>/plan.json" \
     --project . --work "$TMPDIR/refactor-arch/<projeto>"
   ```

   Exit 0 é verde. Exit 2 lista cada requisição que mudou sem estar declarada.
3. **Comparar os sinais.** `python3 .claude/skills/refactor-arch/scripts/scan_signals.py .` no projeto refatorado e no original mostra quantos sinais de anti-pattern sobraram.
