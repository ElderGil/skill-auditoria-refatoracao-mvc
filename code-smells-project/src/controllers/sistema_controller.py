import logging
import sqlite3

from src.models import pedido_model, produto_model, usuario_model

logger = logging.getLogger(__name__)


def indice(versao):
    return {
        "mensagem": "Bem-vindo à API da Loja",
        "versao": versao,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    }


def health(config):
    """(corpo, saudável?). Nunca devolve segredo."""
    try:
        counts = {
            "produtos": produto_model.contar(),
            "usuarios": usuario_model.contar(),
            "pedidos": pedido_model.contar(),
        }
    except sqlite3.Error:
        logger.exception("health: banco indisponível")
        return {"status": "erro", "detalhes": "Banco de dados indisponível"}, False
    return {
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": config["VERSAO_API"],
        "ambiente": config["AMBIENTE"],
        "db_path": config["DATABASE_PATH"],
        "debug": config["DEBUG"],
    }, True
