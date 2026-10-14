import logging

from src.database import transacao
from src.models import pedido_model, produto_model, usuario_model

logger = logging.getLogger(__name__)


def resetar_banco():
    """Apaga todos os dados numa única transação."""
    with transacao():
        pedido_model.apagar_todos()
        produto_model.apagar_todos()
        usuario_model.apagar_todos()
    logger.warning("banco de dados resetado por requisição administrativa")
