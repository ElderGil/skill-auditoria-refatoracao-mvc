# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`,
já refatorada para MVC.

## Como rodar

```bash
npm install
ADMIN_TOKEN=troque-este-token npm start
```

A aplicação sobe em `http://localhost:3000` (ou na porta de `PORT`). O banco SQLite é em memória e
carrega os seeds automaticamente no boot. As variáveis aceitas estão em `.env.example`:

| Variável | Uso | Padrão |
|---|---|---|
| `PORT` | porta HTTP | `3000` |
| `DB_FILE` | arquivo do SQLite | `:memory:` |
| `ADMIN_TOKEN` | token das rotas administrativas | vazio (rotas fechadas, 403) |
| `PAYMENT_GATEWAY_KEY` | chave do gateway (simulado) | vazio |
| `LOG_LEVEL` | `error`, `warn`, `info`, `debug` | `info` |

Exemplos de requisições estão em `api.http`.

## Endpoints

| Método | Caminho | Autenticação |
|---|---|---|
| POST | `/api/checkout` | nenhuma; e-mail já cadastrado exige a senha (`pwd`) do dono |
| GET | `/api/admin/financial-report` | `Authorization: Bearer $ADMIN_TOKEN` |
| DELETE | `/api/users/:id` | `Authorization: Bearer $ADMIN_TOKEN` |

Regras do checkout: `usr`, `eml`, `pwd`, `c_id` e `card` são obrigatórios; `card` tem 13 a 19
dígitos; a mesma pessoa não se matricula duas vezes no mesmo curso (409). Excluir um usuário
remove também as matrículas e os pagamentos dele.

## Estrutura

```
src/
├── app.js              # entry point: inicializa o banco e sobe o servidor
├── createApp.js        # composition root (models, services, controllers, rotas)
├── config/             # leitura do ambiente
├── database/           # conexão sqlite3 com Promise/transação, schema e seed
├── models/             # SQL por entidade (user, course, enrollment, payment, auditLog)
├── controllers/        # fluxo de checkout, relatório e exclusão de usuário
├── routes/             # mapeamento HTTP → controller
├── services/           # gateway de pagamento (simulado)
├── middlewares/        # erro centralizado, async, autenticação de admin
└── utils/              # validação, hash de senha (scrypt), logger
```
