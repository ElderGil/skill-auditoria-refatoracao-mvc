# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas como hash). `flask --app app run` também funciona.

### Variáveis de ambiente

Todas são opcionais; veja `.env.example`.

| Variável | Padrão | Uso |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Endereço do servidor (`python app.py`) |
| `FLASK_DEBUG` | `0` | `1` liga o modo debug (só em máquina local) |
| `SECRET_KEY` | aleatória por boot | Chave de assinatura do Flask |
| `ADMIN_TOKEN` | vazio | Token exigido em `X-Admin-Token` por `POST /admin/reset-db`; vazio desabilita a rota |
| `DATABASE_PATH` | `loja.db` | Arquivo do SQLite |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula |
| `APP_ENV` | `producao` | Rótulo devolvido em `/health` |

## Estrutura

```
app.py                  # entry point: create_app() + app.run
src/
├── app.py              # composition root (config, banco, CORS, blueprints, error handlers)
├── config/settings.py  # configuração lida do ambiente
├── database.py         # conexão SQLite por requisição + transacao()
├── errors.py           # erros de aplicação (400/401/403/404/409)
├── seed.py             # dados de exemplo
├── models/             # acesso a dados por entidade (produto, usuario, pedido)
├── controllers/        # validação e regra de negócio por recurso
├── views/              # blueprints HTTP (rotas finas)
├── services/           # notificação de pedidos
├── middlewares/        # error handler central, autenticação admin
└── utils/validators.py
```

## Endpoints

`GET/POST /produtos`, `GET /produtos/busca`, `GET/PUT/DELETE /produtos/<id>`, `GET/POST /usuarios`, `GET /usuarios/<id>`, `POST /login`, `GET/POST /pedidos`, `GET /pedidos/usuario/<id>`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `GET /health`, `GET /`, `POST /admin/reset-db` (exige `X-Admin-Token`).

Regras de negócio relevantes:
- Status do pedido segue as transições `pendente → aprovado | cancelado`, `aprovado → enviado | cancelado`, `enviado → entregue`. Cancelar devolve o estoque.
- O relatório de vendas não conta pedidos cancelados no faturamento.
- Entrada inválida responde 400; e-mail já cadastrado, 409; recurso inexistente, 404. Erros seguem o formato `{"erro": "...", "sucesso": false}`.
