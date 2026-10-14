"""Acesso a dados de produtos. Escritas não fazem commit: o controller abre a transação."""
from src.database import get_db

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]

_COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def criar_tabela():
    get_db().execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT,
            preco REAL,
            estoque INTEGER,
            categoria TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def listar():
    rows = get_db().execute("SELECT id, nome, descricao, preco, estoque, categoria, ativo, criado_em FROM produtos ORDER BY id").fetchall()
    return [to_dict(row) for row in rows]


def buscar_por_id(produto_id):
    row = get_db().execute("SELECT id, nome, descricao, preco, estoque, categoria, ativo, criado_em FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return to_dict(row) if row else None


def buscar_por_ids(produto_ids):
    """Dicionário {id: produto} numa única consulta."""
    ids = list(produto_ids)
    if not ids:
        return {}
    marcadores = ", ".join("?" for _ in ids)
    rows = get_db().execute(f"SELECT {_COLUNAS} FROM produtos WHERE id IN ({marcadores})", ids).fetchall()
    return {row["id"]: to_dict(row) for row in rows}


def pesquisar(termo=None, categoria=None, preco_min=None, preco_max=None):
    clausulas, params = [], []
    if termo:
        clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        clausulas.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        clausulas.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        clausulas.append("preco <= ?")
        params.append(preco_max)
    where = " AND ".join(clausulas) or "1=1"
    rows = get_db().execute(f"SELECT {_COLUNAS} FROM produtos WHERE {where} ORDER BY id", params).fetchall()
    return [to_dict(row) for row in rows]


def inserir(nome, descricao, preco, estoque, categoria):
    cursor = get_db().execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    cursor = get_db().execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    return cursor.rowcount > 0


def remover(produto_id):
    cursor = get_db().execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    return cursor.rowcount > 0


def baixar_estoque(produto_id, quantidade):
    """Baixa condicional: falha (False) se o estoque não cobre a quantidade, inclusive sob concorrência."""
    cursor = get_db().execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
        (quantidade, produto_id, quantidade),
    )
    return cursor.rowcount > 0


def devolver_estoque(produto_id, quantidade):
    get_db().execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))


def contar():
    return get_db().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]


def apagar_todos():
    get_db().execute("DELETE FROM produtos")
