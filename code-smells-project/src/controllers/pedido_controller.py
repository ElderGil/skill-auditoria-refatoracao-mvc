import logging
from collections import Counter

from src.database import transacao
from src.errors import NotFoundError, ValidationError
from src.models import pedido_model, produto_model, usuario_model
from src.services.notificacao_service import Notificador
from src.utils import validators

logger = logging.getLogger(__name__)


def _validar_itens(itens):
    if not isinstance(itens, list) or not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    validados = []
    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Item do pedido inválido")
        produto_id = validators.identificador(item.get("produto_id"), "produto_id inválido")
        quantidade = validators.inteiro(item.get("quantidade"), "Quantidade deve ser um número inteiro")
        if quantidade < 1:
            raise ValidationError("Quantidade deve ser maior que zero")
        validados.append((produto_id, quantidade))
    return validados


def criar(dados, notificador=None):
    validators.exigir_objeto(dados)
    if not dados.get("usuario_id"):
        raise ValidationError("Usuario ID é obrigatório")
    usuario_id = validators.identificador(dados.get("usuario_id"), "Usuario ID inválido")
    itens = _validar_itens(dados.get("itens", []))

    if usuario_model.buscar_por_id(usuario_id) is None:
        raise ValidationError("Usuário não encontrado")

    # Estoque conferido pela soma de cada produto, não item a item.
    quantidades = Counter()
    for produto_id, quantidade in itens:
        quantidades[produto_id] += quantidade
    produtos = produto_model.buscar_por_ids(quantidades)
    for produto_id, quantidade in quantidades.items():
        produto = produtos.get(produto_id)
        if produto is None:
            raise ValidationError("Produto " + str(produto_id) + " não encontrado")
        if produto["estoque"] < quantidade:
            raise ValidationError("Estoque insuficiente para " + produto["nome"])

    total = 0
    linhas = []
    for produto_id, quantidade in itens:
        preco = produtos[produto_id]["preco"]
        total = total + preco * quantidade
        linhas.append((produto_id, quantidade, preco))

    with transacao():
        for produto_id, quantidade in quantidades.items():
            if not produto_model.baixar_estoque(produto_id, quantidade):
                raise ValidationError("Estoque insuficiente para " + produtos[produto_id]["nome"])
        pedido_id = pedido_model.inserir(usuario_id, total, linhas)

    logger.info("pedido criado id=%s usuario_id=%s", pedido_id, usuario_id)
    (notificador or Notificador()).pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}


def listar_todos():
    return pedido_model.listar_todos()


def listar_por_usuario(usuario_id):
    return pedido_model.listar_por_usuario(usuario_id)


def alterar_status(pedido_id, dados, notificador=None):
    validators.exigir_objeto(dados)
    novo_status = dados.get("status", "")
    if novo_status not in pedido_model.STATUS_VALIDOS:
        raise ValidationError("Status inválido")

    with transacao():
        pedido = pedido_model.buscar_por_id(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido não encontrado")
        if not pedido_model.transicao_permitida(pedido["status"], novo_status):
            raise ValidationError(f"Transição de status inválida: {pedido['status']} -> {novo_status}")
        pedido_model.atualizar_status(pedido_id, novo_status)
        if novo_status == pedido_model.STATUS_CANCELADO:
            for produto_id, quantidade in pedido_model.itens_do_pedido(pedido_id):
                produto_model.devolver_estoque(produto_id, quantidade)

    logger.info("pedido %s: %s -> %s", pedido_id, pedido["status"], novo_status)
    (notificador or Notificador()).status_alterado(pedido_id, novo_status)
