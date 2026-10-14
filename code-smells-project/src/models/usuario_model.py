"""Acesso a dados de usuários. A senha é guardada só como hash e nunca sai deste módulo."""
import logging
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from src.database import get_db
from src.errors import ConflictError

logger = logging.getLogger(__name__)

TIPO_PADRAO = "cliente"
_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def criar_tabela():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            senha TEXT,
            tipo TEXT DEFAULT 'cliente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email)")
    except sqlite3.IntegrityError:
        logger.warning("e-mails duplicados no banco; índice único não criado (cadastro novo continua conferindo)")


def to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def listar():
    rows = get_db().execute("SELECT id, nome, email, tipo, criado_em FROM usuarios ORDER BY id").fetchall()
    return [to_dict(row) for row in rows]


def buscar_por_id(usuario_id):
    row = get_db().execute("SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return to_dict(row) if row else None


def email_cadastrado(email):
    return get_db().execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone() is not None


def inserir(nome, email, senha, tipo=TIPO_PADRAO):
    try:
        cursor = get_db().execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    except sqlite3.IntegrityError as exc:
        raise ConflictError("Email já cadastrado") from exc
    return cursor.lastrowid


def autenticar(email, senha):
    """Dados públicos do usuário se a senha confere; None caso contrário."""
    row = get_db().execute(
        "SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ? ORDER BY id", (email,)
    ).fetchone()
    if row is None or not row["senha"] or not check_password_hash(row["senha"], senha):
        return None
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}


def migrar_senhas_legadas():
    """Converte para hash as senhas gravadas em texto puro pela versão anterior."""
    db = get_db()
    rows = db.execute("SELECT id, senha FROM usuarios WHERE senha IS NOT NULL").fetchall()
    legadas = [(generate_password_hash(row["senha"]), row["id"])
               for row in rows if not row["senha"].startswith(_PREFIXOS_HASH)]
    db.executemany("UPDATE usuarios SET senha = ? WHERE id = ?", legadas)
    return len(legadas)


def contar():
    return get_db().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]


def apagar_todos():
    get_db().execute("DELETE FROM usuarios")
