# Stack: Python + Flask

Leia junto com `mvc-guidelines.md`. Vale para Flask 2.x/3.x, com SQL à mão (`sqlite3`) ou
Flask-SQLAlchemy.

## Árvore alvo

```
<projeto>/
├── app.py                      # entry point fino: from src.app import create_app; app = create_app(); app.run(...)
├── seed.py                     # se já existia: continua funcionando, agora via create_app()
├── requirements.txt
├── .env.example                # todas as variáveis lidas pela config, sem valor sensível
└── src/
    ├── __init__.py
    ├── app.py                  # create_app(): config, banco, blueprints, error handlers (composition root)
    ├── config/settings.py      # classe Config lendo os.environ
    ├── database.py             # conexão por requisição (sqlite3) ou instância db = SQLAlchemy()
    ├── models/                 # uma entidade por arquivo: <entidade>_model.py
    ├── controllers/            # um por recurso: <recurso>_controller.py
    ├── views/                  # blueprints: <recurso>_routes.py
    ├── services/               # integrações externas (notificação, pagamento), se houver
    ├── middlewares/
    │   ├── error_handler.py    # AppError + register_error_handlers(app)
    │   └── auth.py             # require_admin (X-Admin-Token), se houver rota administrativa
    └── utils/validators.py     # validação de entrada reutilizada por criar/atualizar
```

Para projeto grau B que já tem `models/`, `routes/` etc. na raiz, pode manter as pastas na raiz em
vez de `src/` se a mudança de import for grande; o que importa são as responsabilidades.

## Padrões

**Entry point preservado** (`python app.py` continua funcionando):
```python
# app.py
import os
from src.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
            debug=app.config["DEBUG"])
```
`flask --app app run` também continua funcionando, porque o módulo expõe `app`.

**Config:**
```python
# src/config/settings.py
import os, secrets

class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)  # sem segredo fixo
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")  # sem valor = rotas admin fechadas
```
Se `SECRET_KEY` não vier do ambiente, gere uma aleatória e avise no log; nunca deixe literal.

**Conexão sqlite3 por requisição** (substitui o singleton global):
```python
# src/database.py
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
```

**Flask-SQLAlchemy 3.x / SQLAlchemy 2.0:** troque `Model.query.get(id)` por
`db.session.get(Model, id)` e `Model.query.filter_by(...).all()` por
`db.session.execute(db.select(Model).filter_by(...)).scalars().all()`. Inicialize com
`db.init_app(app)` dentro de `create_app` e chame `db.create_all()` lá dentro, com
`app.app_context()`, não no import.

**Error handler central:**
```python
# src/middlewares/error_handler.py
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

class AppError(Exception):
    status = 400
    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        if status:
            self.status = status

def register_error_handlers(app, error_key="erro"):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message}), err.status

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({error_key: err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logging.getLogger(__name__).exception("erro não tratado")
        return jsonify({error_key: "Erro interno"}), 500
```
Use a chave de erro que o projeto já usa (`"erro"` ou `"error"`) para preservar o contrato.

**Corpo JSON ausente:** use `request.get_json(silent=True)` na view e trate `None` como 400.

**Senha:** `from werkzeug.security import generate_password_hash, check_password_hash` (já vem
com Flask). Nada de dependência nova.

**Token assinado** (quando o projeto já tem login com token falso):
`from itsdangerous import URLSafeTimedSerializer` (já vem com Flask).

**Debug:** nunca `debug=True` fixo; `FLASK_DEBUG=1` só no ambiente local. Host padrão `127.0.0.1`.

## Comandos de validação

- Plano antes: `"start": "{work}/venv/bin/flask --app app run -p {port}"` (funciona com porta fixa
  no código, porque o `flask run` ignora o `app.run`).
- Plano depois: `"start": "{work}/venv/bin/python app.py"` (prova que o entry point documentado
  funciona e lê `PORT`).
- Seed: `"setup": ["{work}/venv/bin/python seed.py"]` quando o projeto depende dele.
- Antes do smoke: `{work}/venv/bin/python -c "import app"` pega erro de import rápido.
