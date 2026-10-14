# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Refatorada para MVC: rotas finas em `src/views/`, fluxo em `src/controllers/`, dados e regra em `src/models/`, com configuração por variáveis de ambiente e tratamento de erro central.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env      # opcional; ajuste SECRET_KEY, CORS_ORIGINS etc.
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (veja `HOST`/`PORT`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias. `flask --app app run` também funciona.

## Configuração

Todas as variáveis estão em `.env.example`. As principais:

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória a cada boot | Assina os tokens do `/login`. Defina em qualquer ambiente real. |
| `TOKEN_MAX_AGE` | `28800` | Validade do token, em segundos. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Endereço do `python app.py`. |
| `FLASK_DEBUG` | `0` | `1` só em desenvolvimento local. |
| `DATABASE_URL` | `sqlite:///tasks.db` | Banco do SQLAlchemy. |
| `CORS_ORIGINS` | vazio (CORS desligado) | Origens liberadas, separadas por vírgula. |
| `SMTP_*` | vazio | Credenciais do `NotificationService`. |
| `SEED_PASSWORD` | senhas de desenvolvimento do seed | Senha única para os usuários de exemplo. |

## Autenticação

`POST /login` devolve `token`. Envie-o como `Authorization: Bearer <token>` nas rotas protegidas:

- `PUT /users/<id>`: o próprio usuário ou um admin; `role` e `active` só admin.
- `POST /users` com `role` diferente de `user`: só admin.
- `DELETE /users/<id>` e `DELETE /categories/<id>`: só admin.

Sem token válido a resposta é `401`; com token sem permissão, `403`. As demais rotas continuam abertas.

## Estrutura

```
app.py                 # entry point: create_app() + app.run()
seed.py
src/
  app.py               # composition root (config, banco, CORS, blueprints, erros)
  config/settings.py   # leitura do ambiente
  database.py
  errors.py            # erros de aplicação → JSON {"error": ...}
  models/              # Task, User, Category: consultas, regra e serialização
  controllers/         # tasks, users, auth, categories, reports
  views/               # blueprints HTTP
  services/            # token assinado, notificação por e-mail
  middlewares/         # error handler, autenticação
  utils/               # validadores, datas, percentuais
```

Senhas são gravadas com hash do Werkzeug; hashes MD5 de bancos antigos ainda permitem login e são convertidos no primeiro login.
