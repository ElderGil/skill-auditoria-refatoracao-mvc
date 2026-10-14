# Catálogo de anti-patterns (Fase 2)

Cada entrada traz: severidade padrão e quando ela muda, **sinais** (os ids que o
`scan_signals.py` emite e o que procurar lendo o código), por que importa e o padrão de correção
no `refactoring-playbook.md`. Sinal é pista: confirme lendo o trecho antes de virar achado.

Escala (do enunciado): **CRITICAL** quebra o funcionamento, expõe dado sensível ou destrói a
separação de camadas · **HIGH** viola MVC/SOLID e trava manutenção e teste · **MEDIUM**
padronização, duplicação, performance moderada, validação ausente · **LOW** legibilidade, nomes,
magic numbers.

## Índice

| ID | Anti-pattern | Severidade padrão | Correção |
|---|---|---|---|
| AP01 | [SQL montado com entrada do usuário](#ap01) | CRITICAL | T1 |
| AP02 | [Execução de SQL/código vindo do cliente](#ap02) | CRITICAL | T13 |
| AP03 | [Credencial ou chave no código](#ap03) | CRITICAL | T2 |
| AP04 | [Debug ligado / servidor exposto](#ap04) | HIGH | T2 |
| AP05 | [Senha guardada ou devolvida de forma insegura](#ap05) | CRITICAL | T3 |
| AP06 | [Autenticação ausente, falsa ou sem autorização](#ap06) | CRITICAL / HIGH | T13 |
| AP07 | [Dado sensível em log](#ap07) | CRITICAL / LOW | T14 |
| AP08 | [Tratamento de erro que vaza, engole ou derruba](#ap08) | MEDIUM | T8 |
| AP09 | [Estado global mutável](#ap09) | HIGH | T11 |
| AP10 | [CORS aberto](#ap10) | MEDIUM | T2 |
| AP11 | [Entrada sem validação de tipo e limite](#ap11) | HIGH / MEDIUM | T7 |
| AP12 | [Efeito colateral acoplado ou fingido](#ap12) | MEDIUM | T5 |
| AP13 | [print/console.log como log](#ap13) | LOW | T14 |
| AP14 | [Configuração e bootstrap no import](#ap14) | MEDIUM | T4 |
| AP15 | [Callbacks aninhados (callback hell)](#ap15) | HIGH | T9 |
| AP16 | [API deprecated ou legada](#ap16) | MEDIUM | T12 |
| AP17 | [Consulta N+1](#ap17) | MEDIUM | T10 |
| AP18 | [Código morto e import sem uso](#ap18) | LOW | — |
| AP19 | [Lógica duplicada](#ap19) | MEDIUM | T5 |
| AP20 | [Literais e magic numbers repetidos](#ap20) | LOW | — |
| AP21 | [God class / god file, camadas misturadas](#ap21) | CRITICAL | T4 |
| AP22 | [Regra de negócio no controller ou na rota](#ap22) | HIGH | T5 |
| AP23 | [Operação de várias etapas sem transação](#ap23) | HIGH | T6 |
| AP24 | [Integridade de dados não garantida](#ap24) | HIGH / MEDIUM | T6, T7 |
| AP25 | [Estado de entidade sem máquina de estados](#ap25) | HIGH | T15 |
| AP26 | [Nomes que não dizem nada](#ap26) | LOW | — |
| AP27 | [Dependência vulnerável ou desatualizada](#ap27) | HIGH / MEDIUM | — |

Regras de classificação:
- Use a severidade padrão e mude só com motivo escrito no achado ("sobe para CRITICAL porque a
  rota é anônima e apaga o banco").
- **Um achado por problema, não por linha.** Agrupe as ocorrências (`models.py:28, 48, 58...`) e
  dê o intervalo ou a lista de linhas.
- Achado confirmado por requisição real (sonda do baseline) vale mais que leitura: cite a evidência.

---

## AP01 — SQL montado com entrada do usuário <a id="ap01"></a>
**Severidade:** CRITICAL.
**Sinais:** `sql-concat`, `sql-fstring`, `sql-template`, `sql-format`; `execute-variable` quando a
variável foi montada por concatenação. Leia: o valor concatenado vem de request, parâmetro de rota
ou argumento de função pública?
**Por que importa:** o banco executa o que o cliente mandar. Login sem senha (`' OR '1'='1`),
leitura de outras tabelas, exclusão de dados. Entrada legítima com apóstrofo (`O'Brien`) quebra.
**Não é achado:** ORM com parâmetros (`Model.title.like(f"%{q}%")` vira parâmetro), placeholders
`?`/`%s`/`$1` com valores separados.

## AP02 — Execução de SQL ou código vindo do cliente <a id="ap02"></a>
**Severidade:** CRITICAL.
**Sinais:** `sql-from-request`, `admin-route`; `eval(`, `exec(`, `child_process` com entrada.
**Por que importa:** é acesso total ao banco ou ao servidor entregue por HTTP.
**Correção:** remover o endpoint (não existe versão segura de "execute este SQL").

## AP03 — Credencial ou chave no código <a id="ap03"></a>
**Severidade:** CRITICAL.
**Sinais:** `hardcoded-secret`, `live-key`; também segredo devolvido em resposta (`/health` com
`secret_key`).
**Por que importa:** quem lê o repositório (ou a resposta) tem a credencial. Chave de sessão
conhecida permite forjar sessão; chave de gateway `live` permite cobrança.
**No relatório:** cite `arquivo:linha` e o nome da variável. **Nunca copie o valor.**

## AP04 — Debug ligado ou servidor exposto <a id="ap04"></a>
**Severidade:** HIGH (CRITICAL se combinado com segredo exposto ou rota perigosa).
**Sinais:** `debug-on`, `bind-all`.
**Por que importa:** o debugger interativo do Werkzeug executa código no servidor (protegido só
por PIN); stack traces vazam estrutura interna. `0.0.0.0` publica isso na rede.

## AP05 — Senha guardada ou devolvida de forma insegura <a id="ap05"></a>
**Severidade:** CRITICAL.
**Sinais:** `weak-hash` (MD5/SHA1), `base64-password`, `password-serialized`,
`password-compare-plain`; seed com senha literal gravada direto; função chamada "crypto"/"hash"
que só codifica.
**Por que importa:** vazamento do banco ou da API entrega senhas prontas. MD5 sem salt cai com
tabela pronta; base64 se reverte.

## AP06 — Autenticação ausente, falsa ou sem autorização <a id="ap06"></a>
**Severidade:** CRITICAL quando a rota aberta é destrutiva, administrativa ou dá privilégio
(apagar tudo, virar admin); HIGH quando expõe ou altera dados de outros usuários.
**Sinais:** `fake-auth`, `admin-route`, `destructive-route`; login que não emite credencial; campo
`role`/`is_admin`/`tipo` aceito do corpo da requisição (atribuição em massa); `is_admin()` definido
e nunca chamado.
**Por que importa:** qualquer pessoa com a URL age como administrador.

## AP07 — Dado sensível em log <a id="ap07"></a>
**Severidade:** CRITICAL para cartão, chave, senha ou token; LOW para e-mail e outros dados
pessoais.
**Sinais:** `sensitive-log`.
**Por que importa:** log circula por ferramentas e pessoas que não deveriam ver esses dados (PCI,
LGPD).

## AP08 — Tratamento de erro que vaza, engole ou derruba <a id="ap08"></a>
**Severidade:** MEDIUM. Sobe para CRITICAL quando uma entrada derruba o processo inteiro (Node:
exceção em callback assíncrono). Desce para LOW quando é só log genérico.
**Sinais:** `bare-except`, `broad-except`, `error-leak`, `ignored-callback-error`; resposta HTML de
erro do framework numa API JSON; sonda que derrubou o processo no baseline.
**Por que importa:** `str(e)` entrega detalhe interno ao cliente; `except:` esconde a causa; erro
não tratado em Node encerra o servidor para todos.

## AP09 — Estado global mutável <a id="ap09"></a>
**Severidade:** HIGH (exemplo do enunciado).
**Sinais:** `global-state-py`, `global-state-js`, `shared-connection`; singletons de módulo
alterados por várias funções; objeto exportado e mutado de fora.
**Por que importa:** acoplamento invisível, condição de corrida entre requisições, impossível
isolar em teste, vazamento de memória quando só cresce.

## AP10 — CORS aberto <a id="ap10"></a>
**Severidade:** MEDIUM.
**Sinais:** `cors-open`.
**Por que importa:** qualquer site chama a API pelo navegador do usuário. Origem permitida deve vir
de configuração.

## AP11 — Entrada sem validação de tipo e limite <a id="ap11"></a>
**Severidade:** HIGH quando dado inválido é gravado e corrompe regra de negócio (estoque negativo,
total negativo, valor fracionado em quantidade); MEDIUM quando só vira erro 500.
**Sinais:** `unguarded-cast`, `unvalidated-compare`, `string-method-on-input`; validação que checa
presença mas não tipo; validação diferente entre criar e atualizar. Aplique `hostile-inputs.md`.
**Por que importa:** o cliente recebe 500 sem saber o que corrigir, ou pior, o dado errado entra.

## AP12 — Efeito colateral acoplado ou fingido <a id="ap12"></a>
**Severidade:** MEDIUM.
**Sinais:** `fake-side-effect`; envio de e-mail/SMS dentro do handler HTTP; serviço de notificação
que existe e não é chamado.
**Por que importa:** o fluxo HTTP depende do canal externo (ou finge que envia), e não há como
trocar ou testar a notificação.

## AP13 — print/console.log como log <a id="ap13"></a>
**Severidade:** LOW.
**Sinais:** `print-logging`.
**Por que importa:** sem nível, sem destino configurável, sem formato; mistura com dado sensível.

## AP14 — Configuração e bootstrap no import <a id="ap14"></a>
**Severidade:** MEDIUM.
**Sinais:** `create-all-import`; config escrita inline no arquivo da app; porta fixa; conexão aberta
no import; ausência de factory/composition root.
**Por que importa:** não há como subir a app com outra configuração (teste, outra porta, outro
banco) sem editar código.

## AP15 — Callbacks aninhados <a id="ap15"></a>
**Severidade:** HIGH quando o fluxo de negócio inteiro está aninhado (checkout com 4+ níveis).
**Sinais:** `callback-nesting`, `ignored-callback-error`; contadores manuais para esperar callbacks
(`pending--; if (pending === 0)`).
**Por que importa:** erro em qualquer nível se perde, ordem de execução fica implícita, transação
fica impossível.

## AP16 — API deprecated ou legada <a id="ap16"></a>
**Severidade:** MEDIUM (HIGH se já foi removida na versão em uso).
**Sinais:** `dep-utcnow`, `dep-utcfromtimestamp`, `dep-query-get`, `dep-model-query`, `dep-flask`,
`dep-python`, `dep-node`. Se o MCP Context7 estiver disponível, confirme na documentação da versão
declarada; senão, use a tabela abaixo e o aviso do interpretador (`python -W error::DeprecationWarning`).

| Uso antigo | Status | Equivalente moderno |
|---|---|---|
| `datetime.utcnow()` / `utcfromtimestamp()` | Deprecated no Python 3.12 | `datetime.now(timezone.utc)` / `datetime.fromtimestamp(ts, timezone.utc)` |
| `Model.query.get(id)` | Legado no SQLAlchemy 2.0 (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `Model.query.filter_by(...).all()` e demais `Model.query` | Interface legada (Flask-SQLAlchemy 3.x) | `db.session.execute(db.select(Model).filter_by(...)).scalars().all()` |
| `Model.query.get_or_404(id)` | Legado | `db.get_or_404(Model, id)` |
| `@app.before_first_request` | Removido no Flask 2.3 | Inicializar na factory (`create_app`) |
| `from flask import escape, Markup` | Removido no Flask 3.0 | `from markupsafe import escape, Markup` |
| `flask.json.JSONEncoder` / `app.json_encoder` | Removido no Flask 2.3 | `app.json = CustomJSONProvider(app)` |
| `pkg_resources` | Deprecated (setuptools) | `importlib.metadata` / `importlib.resources` |
| `asyncio.get_event_loop()` sem loop rodando | Deprecated no 3.10+ | `asyncio.run()` / `asyncio.get_running_loop()` |
| `new Buffer(x)` | Deprecated (DEP0005) | `Buffer.from(x)` / `Buffer.alloc(n)` |
| `url.parse()` | Legado | `new URL(input, base)` |
| `fs.exists()` | Deprecated | `fs.existsSync()` / `fs.promises.access()` |
| `util.isDate()`, `util.isBoolean()` e afins / `util.isArray()` | Removidos no Node 23 / `isArray` ainda existe, deprecated | `instanceof Date`, `typeof x === "boolean"` / `Array.isArray()` |
| `crypto.createCipher()` | Removido no Node 22 | `crypto.createCipheriv()` |
| `req.param()`, `app.del()`, `res.send(status)`, `res.json(obj, status)` | Removidos no Express 5 | `req.params/query/body`, `app.delete()`, `res.sendStatus()`, `res.status(s).json(obj)` |
| `String.prototype.substr()` | Legado (Annex B) | `slice()` / `substring()` |

Se não houver uso de API deprecated no código, diga isso no relatório (a checagem foi feita) e
registre versões antigas de dependência em AP27.

## AP17 — Consulta N+1 <a id="ap17"></a>
**Severidade:** MEDIUM (exemplo do enunciado). HIGH se o laço é aninhado (query por item de cada
pedido).
**Sinais:** `query-in-loop`; acesso lazy a relacionamento dentro de laço (`len(u.tasks)`).
**Por que importa:** o número de queries cresce com os dados; a listagem fica lenta com o tempo.

## AP18 — Código morto e import sem uso <a id="ap18"></a>
**Severidade:** LOW (MEDIUM se for uma camada inteira sem uso, como um serviço nunca chamado).
**Sinais:** `unused-import`; função ou módulo sem chamador (`grep` pelo nome); dependência
declarada e nunca importada.

## AP19 — Lógica duplicada <a id="ap19"></a>
**Severidade:** MEDIUM.
**Sinais:** `duplicate-block`; mesma regra em vários handlers (cálculo de "atrasado", serialização
manual igual em vários lugares); função utilitária que existe e não é usada enquanto a lógica é
repetida.
**Por que importa:** a regra muda em um lugar e não no outro; as cópias já divergem.

## AP20 — Literais e magic numbers repetidos <a id="ap20"></a>
**Severidade:** LOW.
**Sinais:** `repeated-literal`; números soltos com significado de negócio (`10000`, `0.1`, `5000`)
e listas de status/categorias escritas inline.

## AP21 — God class / god file, camadas misturadas <a id="ap21"></a>
**Severidade:** CRITICAL (exemplo do enunciado).
**Sinais (leitura):** um arquivo ou classe com rotas + SQL + regra + formatação de resposta; mais de
~250 linhas cobrindo vários domínios; classe que cria o banco, faz seed e registra rotas.
**Por que importa:** não há como testar uma regra isolada nem mudar uma parte sem mexer nas outras.

## AP22 — Regra de negócio no controller ou na rota <a id="ap22"></a>
**Severidade:** HIGH (exemplo do enunciado).
**Sinais (leitura):** handler que valida, calcula, decide, consulta e monta resposta; model sem
comportamento enquanto a regra está nas rotas; método de domínio existente e ignorado.

## AP23 — Operação de várias etapas sem transação <a id="ap23"></a>
**Severidade:** HIGH.
**Sinais (leitura):** pedido → itens → baixa de estoque, ou matrícula → pagamento → auditoria, em
comandos separados sem `BEGIN/COMMIT` ou sessão única; ausência de idempotência em operação
repetível (mesmo checkout duas vezes).
**Por que importa:** falha no meio deixa o banco pela metade; repetição duplica cobrança.

## AP24 — Integridade de dados não garantida <a id="ap24"></a>
**Severidade:** HIGH quando gera dado órfão ou duplicado que afeta regra (pedido de usuário
inexistente, matrícula órfã); MEDIUM para unicidade e exclusão física que apaga histórico.
**Sinais (leitura):** FK não validada antes de inserir; `DELETE` sem tratar dependentes; e-mail sem
`UNIQUE`; checagem de estoque item a item (o mesmo item repetido fura o total); exclusão que
responde sucesso para registro inexistente.

## AP25 — Estado de entidade sem máquina de estados <a id="ap25"></a>
**Severidade:** HIGH.
**Sinais (leitura):** status atualizado para qualquer valor válido sem olhar o atual (cancelado →
aprovado); efeito de transição que não acontece (cancelar não devolve estoque); agregação que conta
estados que não deveria (cancelado no faturamento).

## AP26 — Nomes que não dizem nada <a id="ap26"></a>
**Severidade:** LOW.
**Sinais (leitura):** variáveis de uma letra no fluxo principal (`u`, `e`, `p`, `cc`), nome que
sombreia builtin (`id`), nome que mente (`badCrypto` que não é crypto, `utils` com regra de negócio).
Nomes de campos do **contrato** da API são preservados mesmo se ruins; o achado fica registrado.

## AP27 — Dependência vulnerável ou desatualizada <a id="ap27"></a>
**Severidade:** HIGH se a auditoria (`pip-audit`, `npm audit`) apontar CVE crítica/alta em
dependência usada em runtime; MEDIUM para versão sem suporte ou dependência descontinuada; LOW para
"há versão mais nova".
**Sinais:** saída da auditoria de dependências; versão não fixada no manifesto.
**Correção na Fase 3:** atualizar dentro da mesma major quando resolve a CVE sem mudar API; troca
de major (ex.: Express 4 → 5) fica como melhoria proposta, salvo se a correção exigir.
