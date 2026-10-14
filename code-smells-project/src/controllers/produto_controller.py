import logging

from src.database import transacao
from src.errors import NotFoundError, ValidationError
from src.models import produto_model
from src.utils import validators

logger = logging.getLogger(__name__)

NOME_MIN = 2
NOME_MAX = 200
DESCRICAO_MAX = 2000
CATEGORIA_PADRAO = "geral"


def _validar(dados):
    """Mesma validação para criar e atualizar."""
    validators.exigir_objeto(dados)
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = validators.texto(dados["nome"], "Nome é obrigatório")
    preco = validators.numero(dados["preco"], "Preço deve ser numérico")
    estoque = validators.inteiro(dados["estoque"], "Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")

    descricao = dados.get("descricao") or ""
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if len(descricao) > DESCRICAO_MAX:
        raise ValidationError("Descrição muito longa")

    categoria = dados.get("categoria", CATEGORIA_PADRAO)
    if categoria not in produto_model.CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(produto_model.CATEGORIAS_VALIDAS))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def listar():
    return produto_model.listar()


def buscar(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if produto is None:
        raise NotFoundError("Produto não encontrado")
    return produto


def pesquisar(filtros):
    termo = filtros.get("q", "")
    categoria = filtros.get("categoria") or None
    preco_min = validators.numero_de_query(filtros.get("preco_min"), "preco_min")
    preco_max = validators.numero_de_query(filtros.get("preco_max"), "preco_max")
    return produto_model.pesquisar(termo, categoria, preco_min, preco_max)


def criar(dados):
    produto = _validar(dados)
    with transacao():
        produto_id = produto_model.inserir(**produto)
    logger.info("produto criado id=%s", produto_id)
    return produto_id


def atualizar(produto_id, dados):
    if produto_model.buscar_por_id(produto_id) is None:
        raise NotFoundError("Produto não encontrado")
    produto = _validar(dados)
    with transacao():
        produto_model.atualizar(produto_id, **produto)
    logger.info("produto atualizado id=%s", produto_id)


def remover(produto_id):
    with transacao():
        if not produto_model.remover(produto_id):
            raise NotFoundError("Produto não encontrado")
    logger.info("produto removido id=%s", produto_id)
