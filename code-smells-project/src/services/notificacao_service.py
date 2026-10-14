"""Ponto único de notificação de pedidos.

Ainda não há canal real (e-mail, SMS, push): esta implementação só registra o evento no log.
Para integrar um canal, troque o corpo destes métodos ou injete outra classe com a mesma interface.
"""
import logging

logger = logging.getLogger(__name__)


class Notificador:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("evento pedido_criado pedido_id=%s usuario_id=%s", pedido_id, usuario_id)

    def status_alterado(self, pedido_id, status):
        logger.info("evento pedido_status pedido_id=%s status=%s", pedido_id, status)
