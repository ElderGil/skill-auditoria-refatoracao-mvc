# Stack: Node.js + Express

Leia junto com `mvc-guidelines.md`. Vale para Express 4 e 5, CommonJS ou ESM (siga o que o
projeto usa; não converta de um para o outro).

## Árvore alvo

```
<projeto>/
├── package.json                # "main" e "scripts.start" continuam apontando para o mesmo arquivo
├── .env.example
└── src/
    ├── app.js                  # entry point: carrega config, cria app (createApp) e chama listen
    ├── createApp.js            # composition root: db, repositórios, controllers, rotas, middlewares
    ├── config/index.js         # lê process.env
    ├── database/
    │   ├── connection.js       # abre o banco e expõe helpers com Promise (run/get/all/transaction)
    │   └── seed.js             # schema + dados iniciais (se o original fazia seed no boot)
    ├── models/                 # um por entidade: user.model.js, course.model.js ...
    ├── controllers/            # um por recurso: checkout.controller.js ...
    ├── routes/                 # um router por recurso (as "views" da API)
    ├── services/               # integrações externas: payment.service.js, notification ...
    ├── middlewares/
    │   ├── errorHandler.js     # AppError + middleware (err, req, res, next)
    │   ├── asyncHandler.js     # repassa rejeição de handler async para o errorHandler (Express 4)
    │   └── requireAdmin.js     # X-Admin-Token, se houver rota administrativa
    └── utils/
        ├── validators.js
        └── password.js         # scrypt + timingSafeEqual
```

Se o `package.json` aponta `"main": "src/app.js"`, o entry point continua sendo `src/app.js`.

## Padrões

**Promisificar o sqlite3** (fim do callback hell e base para transação):
```js
// src/database/connection.js
const sqlite3 = require('sqlite3');

function openDatabase(filename) {
  const db = new sqlite3.Database(filename);
  const run = (sql, params = []) => new Promise((resolve, reject) =>
    db.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); }));
  const get = (sql, params = []) => new Promise((resolve, reject) =>
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));
  const all = (sql, params = []) => new Promise((resolve, reject) =>
    db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));
  // Em memória e com uma conexão só, serialize as transações para não intercalar.
  let queue = Promise.resolve();
  const transaction = (work) => {
    const result = queue.then(async () => {
      await run('BEGIN');
      try { const value = await work(); await run('COMMIT'); return value; }
      catch (err) { await run('ROLLBACK'); throw err; }
    });
    queue = result.catch(() => {});
    return result;
  };
  return { raw: db, run, get, all, transaction };
}

module.exports = { openDatabase };
```

**Erro de handler async não derruba o processo:**
```js
// src/middlewares/asyncHandler.js (necessário no Express 4; no 5 a rejeição já vai para o errorHandler)
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```
```js
// src/middlewares/errorHandler.js
class AppError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}

function errorHandler(err, req, res, next) {
  if (err.type === 'entity.parse.failed') return res.status(400).send('Bad Request');
  if (err instanceof AppError) return res.status(err.status).send(err.message);
  console.error('[error]', err.message);
  return res.status(500).send('Erro interno');
}

module.exports = { AppError, errorHandler };
```
Se o contrato original responde texto puro (`res.send("Bad Request")`), o handler responde texto;
se responde JSON, responde JSON. O registro do `errorHandler` vai depois de todas as rotas.

**Config:**
```js
// src/config/index.js
module.exports = {
  port: Number(process.env.PORT) || 3000,
  dbFile: process.env.DB_FILE || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  adminToken: process.env.ADMIN_TOKEN || '',
};
```

**Senha:**
```js
// src/utils/password.js
const crypto = require('crypto');
function hashPassword(plain) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `${salt}:${crypto.scryptSync(plain, salt, 64).toString('hex')}`;
}
function verifyPassword(plain, stored) {
  const [salt, hash] = stored.split(':');
  const candidate = crypto.scryptSync(plain, salt, 64);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
module.exports = { hashPassword, verifyPassword };
```

**Produção:** `app.disable('x-powered-by')`; nunca logar cartão, chave ou senha. O handler de erro
próprio evita a página HTML com stack trace do handler padrão.

## Comandos de validação

- Dependências fora do projeto: `"link": {"node_modules": "{work}/deps/node_modules"}`.
- Plano antes: `"start": "node src/app.js"`, com `"port": {"before": 3000, "after": null}` se a
  porta original for fixa no código.
- Plano depois: `"start": "node src/app.js"` (a config lê `PORT`).
- Antes do smoke: `node --check` em cada arquivo alterado pega erro de sintaxe rápido.
