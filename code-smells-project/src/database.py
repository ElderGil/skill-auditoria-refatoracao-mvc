import sqlite3
from contextlib import contextmanager

from flask import current_app, g


def get_db():
    """Conexão da requisição atual; aberta sob demanda e fechada no teardown."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transacao():
    """Commit ao final do bloco, rollback se houver exceção."""
    db = get_db()
    with db:
        yield db


def init_app(app):
    app.teardown_appcontext(close_db)
