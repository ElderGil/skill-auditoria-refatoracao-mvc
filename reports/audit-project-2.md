================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v24.13.1) + Express ^4.18.2 (lock: 4.22.1), sqlite3 ^5.1.6 (lock: 5.1.7)
Files:   3 analyzed | ~140 lines of code (180 total)
Grade:   A (monólito: classe-deus AppManager com banco, seed, rotas, SQL e regra)

## Summary
CRITICAL: 6 | HIGH: 9 | MEDIUM: 2 | LOW: 4 | Total: 21

## Findings

### [CRITICAL] #1 Classe-deus AppManager mistura todas as camadas (AP21)
File: src/AppManager.js:4-139, src/app.js:8-10
Description: Uma única classe abre a conexão (7), cria o schema e faz o seed (10-23), registra as três rotas (25-137), executa o SQL, decide se o pagamento é aprovado e monta a resposta HTTP.
Impact: nenhuma regra (aprovação de pagamento, matrícula, relatório) pode ser testada sem subir HTTP e banco. Qualquer mudança mexe no mesmo arquivo de 141 linhas.
Evidence: confirmado por leitura.
Recommendation: separar em config, conexão, models (repositórios SQL), services (checkout, relatório, usuários, gateway), controllers e rotas, com uma factory `createApp` (playbook T4).

### [CRITICAL] #2 Credenciais e chave de produção no código (AP03)
File: src/utils.js:2-5 (`config.dbUser`, `config.dbPass`, `config.paymentGatewayKey` com prefixo de chave live, `config.smtpUser`)
Description: usuário e senha de banco e a chave do gateway de pagamento estão literais no módulo de configuração versionado.
Impact: quem lê o repositório tem as credenciais. Uma chave live do gateway permite cobrança em nome da empresa.
Evidence: scan_signals `hardcoded-secret` (utils.js:3, 4) e `live-key` (utils.js:4); confirmado por leitura. Valores omitidos.
Recommendation: remover os literais; ler de variável de ambiente (`PAYMENT_GATEWAY_KEY`) com `.env.example` sem valores; apagar `dbUser`/`dbPass`/`smtpUser`, que não são usados. Recomenda-se revogar a chave exposta fora do código (playbook T2).

### [CRITICAL] #3 Número do cartão e chave do gateway escritos no log (AP07)
File: src/AppManager.js:45
Description: cada checkout faz `console.log` do número completo do cartão (`cc`) e de `config.paymentGatewayKey`.
Impact: o PAN completo e a chave vão para qualquer destino de log (violação de PCI-DSS e LGPD).
Evidence: o log do baseline (`$WORK/app-baseline.log`) tem 8 linhas "Processando cartão … na chave …" com o número inteiro (valores não reproduzidos aqui).
Recommendation: não registrar cartão nem chave; logar só o id da matrícula e os 4 últimos dígitos, por um logger com nível (playbook T14).

### [CRITICAL] #4 Senha armazenada de forma reversível, seed em texto puro e senha padrão (AP05)
File: src/utils.js:17-23 (`badCrypto`), src/AppManager.js:18, 68
Description: `badCrypto` só repete os 2 primeiros caracteres do base64 da senha e corta em 10 caracteres (não é hash: colide e se reverte). O seed grava a senha do usuário 1 em texto puro. Checkout sem `pwd` cria a conta com uma senha padrão fixa.
Impact: um vazamento do banco entrega as senhas. Toda conta criada sem `pwd` tem a mesma senha conhecida.
Evidence: sonda `sonda-sem-senha`: 200, conta criada (enrollment_id 5) sem senha informada; scan_signals `base64-password` (utils.js:20).
Recommendation: hash com `crypto.scrypt` + salt aleatório e comparação com `timingSafeEqual`; seed com hash; `pwd` obrigatório para criar conta (playbook T3).

### [CRITICAL] #5 Relatório financeiro e exclusão de usuários sem autenticação (AP06)
File: src/AppManager.js:80, 131
Description: `GET /api/admin/financial-report` (nomes de alunos e receita) e `DELETE /api/users/:id` não fazem nenhuma checagem de identidade.
Impact: qualquer pessoa com a URL lê dados financeiros e pessoais e apaga usuários.
Evidence: sondas `sonda-relatorio-sem-token` 200 (relatório completo) e `sonda-delete-sem-token` 200.
Recommendation: middleware `requireAdmin` que compara `Authorization: Bearer <token>` com `ADMIN_TOKEN` do ambiente (comparação em tempo constante); sem token configurado, nega tudo (playbook T13).

### [CRITICAL] #6 Cartão enviado como número derruba o processo inteiro (AP08)
File: src/AppManager.js:46 (dentro dos callbacks 37-77); mesmo padrão em 92-93 (`enrollments.length` com `err` ignorado)
Description: `cc.startsWith("4")` roda num callback do sqlite3. Com `card` numérico, o `TypeError` não é capturado e encerra o Node. A conta do usuário já foi criada (69) antes da queda.
Impact: uma requisição anônima derruba a API para todos os clientes (DoS) e deixa um usuário criado sem matrícula.
Evidence: sonda `sonda-cartao-numero`: sem resposta, PROCESSO CAIU (`TypeError: cc.startsWith is not a function` em AppManager.js:46).
Recommendation: validar o tipo antes de qualquer acesso ao banco; usar async/await com promessas para que toda exceção chegue ao error handler do Express (playbook T7, T8, T9).

### [HIGH] #7 Checkout age em nome de outra pessoa só com o e-mail dela (AP06)
File: src/AppManager.js:40-41, 66-75
Description: se o e-mail já existe, o checkout usa a conta encontrada e ignora `pwd`. Não confere a senha do dono.
Impact: qualquer pessoa cria matrículas e pagamentos na conta de outra pessoa sabendo só o e-mail dela.
Evidence: sonda `sonda-email-alheio`: 200, matrícula 3 criada na conta de gui@… com senha errada.
Recommendation: com e-mail existente, exigir `pwd` e conferir com o hash; senão 401 (playbook T13).

### [HIGH] #8 Checkout em várias etapas sem transação e sem idempotência (AP23)
File: src/AppManager.js:50-63 (enrollments → payments → audit_logs), 66-72 (usuário criado antes do pagamento)
Description: matrícula, pagamento e auditoria são três `INSERT` independentes. Uma falha no meio deixa matrícula sem pagamento. O usuário é gravado antes da decisão do pagamento, e o mesmo checkout repetido gera nova matrícula e nova cobrança.
Impact: banco pela metade em caso de erro e cobrança duplicada em retry ou duplo clique.
Evidence: sonda `sonda-checkout-duplicado`: 200, segunda matrícula (enrollment_id 4) no mesmo curso para o mesmo usuário; na queda do #6 o usuário ficou criado sem matrícula.
Recommendation: `BEGIN/COMMIT/ROLLBACK` cobrindo usuário + matrícula + pagamento + auditoria; recusar com 409 matrícula já existente para (user, course) e índice `UNIQUE(user_id, course_id)` (playbook T6).

### [HIGH] #9 Integridade: exclusão deixa órfãos, sucesso falso, sem FK nem UNIQUE (AP24)
File: src/AppManager.js:12-16 (schema sem FK nem UNIQUE em email), 131-136
Description: `DELETE /api/users/:id` apaga só o usuário: matrículas e pagamentos ficam órfãos (a própria resposta diz isso), e o erro é ignorado. Também responde sucesso para id inexistente. `users.email` não é único.
Impact: o relatório passa a mostrar aluno "Unknown" com valor pago, o cliente recebe sucesso para uma exclusão que não ocorreu, e há duplicação possível de conta por e-mail.
Evidence: `sonda-delete-inexistente`: 200 para /api/users/999; `sonda-relatorio-pos-exclusao`: `{"student":"Unknown","paid":997}`.
Recommendation: exclusão em transação removendo pagamentos → matrículas → usuário, com 404 quando `changes = 0`; FKs, `UNIQUE(email)` e `PRAGMA foreign_keys = ON` (playbook T6, T7).

### [HIGH] #10 Entrada sem validação de tipo e formato (AP11)
File: src/AppManager.js:29-35, 46
Description: a validação checa só presença. O cartão é aprovado se começar com "4", sem conferir que são dígitos; e-mail sem formato; `c_id` de qualquer tipo; nomes sem limite.
Impact: pagamento "aprovado" e matrícula criada com cartão `"4abc"`; contas com e-mail inválido; tipo errado vira 404 enganoso ou queda (#6).
Evidence: `sonda-cartao-invalido` 200 (matrícula 6), `sonda-email-invalido` 200 (matrícula 7), `sonda-cid-objeto` 404 "Curso não encontrado" para `c_id` objeto.
Recommendation: validador do checkout: `usr` texto 1-120, `eml` formato de e-mail, `pwd` texto 1-128, `c_id` inteiro positivo (número ou texto numérico, como hoje), `card` 13-19 dígitos; 400 em caso contrário (playbook T7).

### [HIGH] #11 Callback hell e contadores manuais (AP15)
File: src/AppManager.js:37-77 (checkout com 6 níveis), 83-128 (relatório com `coursesPending--`/`enrPending--`)
Description: o fluxo de negócio inteiro está aninhado em callbacks, e o relatório espera as consultas com contadores manuais.
Impact: erros se perdem (#6, #16), transação é inviável (#8) e a ordem do relatório depende de qual callback termina primeiro.
Evidence: o baseline devolveu o relatório em ordens diferentes (`relatorio-financeiro` começa por "Docker"; `sonda-relatorio-sem-token`, por "Clean Architecture"); scan_signals `callback-nesting` (8 ocorrências).
Recommendation: camada de acesso com promessas (`run/get/all`) e async/await, com ordem determinística `ORDER BY id` (playbook T9).

### [HIGH] #12 Regra de negócio dentro da rota (AP22)
File: src/AppManager.js:43-64 (aprovação do pagamento e matrícula), 89-123 (agregação de receita)
Description: o handler decide a aprovação (`cc.startsWith("4")`), cria a conta, matricula, calcula receita e formata o relatório.
Impact: a regra de aprovação e o cálculo de receita não têm lugar próprio para teste ou troca (gateway real).
Evidence: confirmado por leitura.
Recommendation: `CheckoutService`, `PaymentGateway` (simulado, mesma regra) e `ReportService`; o controller só traduz HTTP (playbook T5).

### [HIGH] #13 Consulta N+1 aninhada no relatório (AP17)
File: src/AppManager.js:92 (1 query por curso), 104 e 106 (2 queries por matrícula)
Description: o relatório faz 1 + C + 2·M consultas, com laço dentro de laço.
Impact: o tempo do relatório cresce linearmente com matrículas; com milhares de alunos, segundos por chamada.
Evidence: scan_signals `query-in-loop` (3 ocorrências); confirmado por leitura.
Recommendation: uma consulta com `LEFT JOIN` courses → enrollments → users → payments, agregada em memória (playbook T10).

### [HIGH] #14 Estado global mutável sem uso (AP09)
File: src/utils.js:9-15, 25; src/AppManager.js:59
Description: `globalCache` é um objeto de módulo que recebe uma chave por checkout e nunca é lido nem limpo. `totalRevenue` é exportado e nunca atualizado.
Impact: vazamento de memória que cresce a cada checkout e acoplamento invisível entre módulos.
Evidence: scan_signals `global-state-js` (utils.js:9, 10); `grep` mostra que `globalCache` não tem leitura.
Recommendation: remover o cache e o contador; o "último checkout" já fica em `audit_logs` (playbook T11).

### [HIGH] #15 Dependências com vulnerabilidades conhecidas (AP27)
File: package.json:8-11, package-lock.json
Description: o `npm audit --omit=dev` aponta 14 vulnerabilidades (2 critical, 8 high, 1 moderate, 3 low). Em runtime, via express 4.22.1: proxy-addr 2.0.7 (critical, GHSA-jqcg-44mw-7w3h), path-to-regexp 0.1.12 (high, ReDoS, GHSA-37ch-88jc-xwx2), qs 6.14.2 (moderate, 3 avisos), body-parser 1.20.4 (low). Na cadeia de build do sqlite3 5.1.7: tar, node-gyp, cacache, make-fetch-happen (critical/high).
Impact: as falhas de runtime são corrigíveis na mesma major (`npm audit fix`). As da cadeia do sqlite3 afetam a instalação, não as requisições, e só fecham com sqlite3 6 (major).
Evidence: saída do `npm audit --omit=dev` em `$WORK/deps`.
Recommendation: na Fase 3, `npm audit fix` sem `--force` (express 4.x e transitivas na mesma major) e atualização do lockfile. sqlite3 6 fica em melhorias propostas.

### [MEDIUM] #16 Erros engolidos e stack trace em HTML (AP08)
File: src/AppManager.js:57, 92, 104, 106, 133 (`err` ignorado); src/app.js:5-10 (sem error handler)
Description: erros do banco na auditoria, no relatório e na exclusão são ignorados, e a exclusão responde sucesso mesmo com erro. JSON malformado cai no handler padrão do Express, que devolve HTML com stack trace.
Impact: falha silenciosa, e a página de erro expõe caminhos internos e versões a quem manda corpo inválido.
Evidence: `sonda-json-malformado`: 400 com `<!DOCTYPE html>… SyntaxError …` e o stack de body-parser.
Recommendation: error handler central com resposta curta sem detalhe interno e log do erro no servidor (playbook T8).

### [MEDIUM] #17 Configuração inline, porta fixa e bootstrap acoplado (AP14)
File: src/utils.js:1-7, src/app.js:5-14, src/AppManager.js:7
Description: porta 3000 fixa (não lê `PORT`), configuração e utilitários no mesmo módulo, conexão aberta no construtor e app montada no topo do módulo de entrada.
Impact: não dá para subir em outra porta, com outro banco ou em teste sem editar código.
Evidence: o baseline precisou de porta fixa 3000 (`plan.json: port.before`).
Recommendation: `config/` lendo o ambiente com padrões (`PORT=3000`), `createApp(deps)` como composition root, e `app.js` só faz listen (playbook T4).

### [LOW] #18 console.log como log (AP13)
File: src/app.js:13, src/utils.js:13, src/AppManager.js:45
Description: os logs são `console.log` sem nível nem formato. O de utils.js:13 registra só a chave do cache (id do usuário), sem dado sensível; o sensível está no #3.
Impact: não há como filtrar por nível nem desligar o log em teste.
Evidence: scan_signals `print-logging` (3).
Recommendation: logger mínimo com nível (`LOG_LEVEL`) sobre `console` (playbook T14).

### [LOW] #19 Código morto (AP18)
File: src/AppManager.js:2 (`totalRevenue` importado e não usado), src/AppManager.js:104 (`email` selecionado e não usado), src/utils.js:2, 3, 5 (`dbUser`, `dbPass`, `smtpUser` sem uso)
Description: há imports, campos e configuração sem nenhum consumidor.
Impact: ruído que esconde o que importa e segredo mantido sem necessidade.
Evidence: `grep` pelos nomes no projeto.
Recommendation: remover.

### [LOW] #20 Literais com significado de negócio (AP20)
File: src/AppManager.js:46, 48, 108 ("4", "PAID", "DENIED"); src/utils.js:19 (10000)
Description: a regra de aprovação e os status de pagamento estão escritos inline.
Impact: mudar a regra ou um status exige caçar strings.
Evidence: confirmado por leitura.
Recommendation: constantes `PAYMENT_STATUS` e regra no `PaymentGateway`.

### [LOW] #21 Nomes que não dizem nada (AP26)
File: src/AppManager.js:29-33 (`u`, `e`, `p`, `cid`, `cc`), src/utils.js:17 (`badCrypto`), `AppManager`, `utils.js` com regra
Description: as variáveis do fluxo principal têm uma letra, e os nomes de função e módulo não descrevem o que fazem.
Impact: leitura lenta e propensa a erro.
Evidence: confirmado por leitura.
Recommendation: renomear internamente. Os campos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) são preservados.

## Deprecated APIs
Nenhum uso de API deprecated encontrado no código. Conferido contra a tabela AP16 e a documentação via Context7 (Express 4.21 `/expressjs/express/4_21_2`: `req.param`, `app.del` e `res.send(status)` não são usados; node-sqlite3 `/tryghost/node-sqlite3`: `verbose()`, `serialize()`, `run/get/all` são API atual). Versões vulneráveis de dependência estão no #15.

## Dependencies
`npm audit --omit=dev`: 14 vulnerabilidades (critical 2, high 8, moderate 1, low 3).
- Runtime (express 4.22.1): proxy-addr (critical), path-to-regexp (high), qs (moderate), body-parser (low). Correção disponível na mesma major (`npm audit fix`).
- Instalação (sqlite3 5.1.7 → node-gyp/tar/cacache/make-fetch-happen/@tootallnate/once): critical/high. A correção exige sqlite3 6.0.1 (major).

## Baseline (estado atual dos endpoints)
18 requisições | 1 5xx/sem resposta | 1 derrubou o processo
- `sonda-relatorio-sem-token` 200 e `sonda-delete-sem-token` 200: rotas administrativas abertas (#5)
- `sonda-delete-inexistente` 200: sucesso falso para id 999 (#9)
- `sonda-relatorio-pos-exclusao` 200: aluno "Unknown" com 997 pagos depois de apagar o usuário 1 (#9)
- `sonda-email-alheio` 200: matrícula na conta de outra pessoa com senha errada (#7)
- `sonda-checkout-duplicado` 200: segunda matrícula e segunda cobrança no mesmo curso (#8)
- `sonda-sem-senha` 200: conta criada com senha padrão (#4)
- `sonda-cartao-invalido` 200 e `sonda-email-invalido` 200: dado inválido aceito (#10)
- `sonda-json-malformado` 400 em HTML com stack trace (#16)
- `sonda-cid-objeto` 404 "Curso não encontrado" para tipo errado (#10)
- `sonda-cartao-numero`: sem resposta, o processo caiu (#6)

## Proposed improvements (not defects)
- Envelope de erro em JSON (`{"error": "..."}`): hoje os erros são texto puro e clientes podem depender disso; mudar quebra o contrato.
- Autenticação real de clientes (login/sessão/JWT) no checkout em vez de senha no corpo; exige novo fluxo.
- Exclusão lógica ou anonimização do usuário, preservando o histórico financeiro; a Fase 3 apaga matrículas e pagamentos em cascata para não deixar órfãos, o que remove a receita do relatório.
- sqlite3 6.x (fecha as vulnerabilidades da cadeia de instalação; major) e Express 5.
- Integração com gateway de pagamento real (tokenização; o servidor não deveria receber o PAN).
- Banco persistente e migrações (hoje é em memória e zera a cada boot).
- Testes automatizados de services e rotas; rate limiting no checkout.

## Phase 3 plan
- Target structure:
  src/
    app.js                      (entrada: createApp + listen; `npm start` igual)
    createApp.js                (composition root)
    config/index.js             (PORT, ADMIN_TOKEN, PAYMENT_GATEWAY_KEY, LOG_LEVEL)
    database/connection.js      (sqlite3 com promessas + transaction)
    database/schema.js          (schema com FK/UNIQUE + seed)
    models/                     (user, course, enrollment, payment, auditLog)
    services/                   (checkout, report, user, paymentGateway, password)
    controllers/                (checkout, report, user)
    routes/index.js             (rotas → controllers)
    middlewares/                (requireAdmin, errorHandler)
    validators/checkout.validator.js
    utils/                      (logger, httpError)
- Intentional behavior changes:
  - Relatório e exclusão exigem `Authorization: Bearer $ADMIN_TOKEN`; sem ele, 401 (#5)
  - Checkout com e-mail existente e senha errada: 401 (#7)
  - Matrícula repetida no mesmo curso: 409 (#8)
  - `pwd` obrigatório para conta nova: 400 (#4)
  - Cartão, e-mail e `c_id` validados: 400 (#6, #10)
  - DELETE de id inexistente: 404; exclusão em cascata sem órfãos e mensagem verdadeira (#9)
  - Usuário de checkout recusado não fica gravado (#8)
  - Relatório em ordem de id do curso (#11)
  - JSON malformado: 400 em texto curto, sem stack trace (#16)
  - Porta lida de `PORT` (padrão 3000) (#17)
- Out of scope: itens de "Proposed improvements"; troca de major de dependências.

================================
Total: 21 findings
================================
