"""Acesso a dados de pedidos e itens, com as transições de status permitidas."""
from src.database import get_db

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"

STATUS_VALIDOS = [STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO]

TRANSICOES = {
    STATUS_PENDENTE: {STATUS_APROVADO, STATUS_CANCELADO},
    STATUS_APROVADO: {STATUS_ENVIADO, STATUS_CANCELADO},
    STATUS_ENVIADO: {STATUS_ENTREGUE},
    STATUS_ENTREGUE: set(),
    STATUS_CANCELADO: set(),
}


def transicao_permitida(atual, novo):
    return novo in TRANSICOES.get(atual, set())


def criar_tabelas():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            status TEXT DEFAULT 'pendente',
            total REAL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER,
            preco_unitario REAL
        )
    """)


def inserir(usuario_id, total, itens):
    """itens: lista de (produto_id, quantidade, preco_unitario). Sem commit."""
    db = get_db()
    pedido_id = db.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
        (usuario_id, STATUS_PENDENTE, total),
    ).lastrowid
    db.executemany(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
        [(pedido_id, produto_id, quantidade, preco) for produto_id, quantidade, preco in itens],
    )
    return pedido_id


def buscar_por_id(pedido_id):
    row = get_db().execute(
        "SELECT id, usuario_id, status, total, criado_em FROM pedidos WHERE id = ?", (pedido_id,)
    ).fetchone()
    return dict(row) if row else None


def _com_itens(pedidos_rows, filtro_sql, params):
    """Anexa os itens a cada pedido com uma única consulta (sem N+1)."""
    pedidos = []
    por_id = {}
    for row in pedidos_rows:
        pedido = {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        }
        pedidos.append(pedido)
        por_id[pedido["id"]] = pedido
    if not pedidos:
        return pedidos
    itens = get_db().execute(f"""
        SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario,
               COALESCE(p.nome, 'Desconhecido') AS produto_nome
        FROM itens_pedido i
        LEFT JOIN produtos p ON p.id = i.produto_id
        WHERE i.pedido_id IN (SELECT id FROM pedidos {filtro_sql})
        ORDER BY i.id
    """, params).fetchall()
    for item in itens:
        pedido = por_id.get(item["pedido_id"])
        if pedido is not None:
            pedido["itens"].append({
                "produto_id": item["produto_id"],
                "produto_nome": item["produto_nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            })
    return pedidos


def listar_todos():
    rows = get_db().execute(
        "SELECT id, usuario_id, status, total, criado_em FROM pedidos ORDER BY id"
    ).fetchall()
    return _com_itens(rows, "", ())


def listar_por_usuario(usuario_id):
    rows = get_db().execute(
        "SELECT id, usuario_id, status, total, criado_em FROM pedidos WHERE usuario_id = ? ORDER BY id",
        (usuario_id,),
    ).fetchall()
    return _com_itens(rows, "WHERE usuario_id = ?", (usuario_id,))


def itens_do_pedido(pedido_id):
    rows = get_db().execute(
        "SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?", (pedido_id,)
    ).fetchall()
    return [(row["produto_id"], row["quantidade"]) for row in rows]


def atualizar_status(pedido_id, status):
    get_db().execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))


def resumo_por_status():
    """{status: (quantidade, soma_total)} numa única consulta."""
    rows = get_db().execute(
        "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS soma FROM pedidos GROUP BY status"
    ).fetchall()
    return {row["status"]: (row["quantidade"], row["soma"]) for row in rows}


def contar():
    return get_db().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]


def apagar_todos():
    db = get_db()
    db.execute("DELETE FROM itens_pedido")
    db.execute("DELETE FROM pedidos")
