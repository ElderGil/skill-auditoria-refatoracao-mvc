import logging

from src.database import transacao
from src.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from src.models import usuario_model
from src.utils import validators

logger = logging.getLogger(__name__)

NOME_MAX = 200
EMAIL_MAX = 254


def listar():
    return usuario_model.listar()


def buscar(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados):
    validators.exigir_objeto(dados)
    nome, email, senha = dados.get("nome"), dados.get("email"), dados.get("senha")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(valor, str) for valor in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")

    nome = validators.texto(nome, "Nome, email e senha são obrigatórios", NOME_MAX, "Nome muito longo")
    email = validators.texto(email, "Nome, email e senha são obrigatórios", EMAIL_MAX, "Email muito longo")
    if "@" not in email:
        raise ValidationError("Email inválido")
    if usuario_model.email_cadastrado(email):
        raise ConflictError("Email já cadastrado")

    # O tipo nunca vem do corpo: cadastro público sempre cria cliente.
    with transacao():
        usuario_id = usuario_model.inserir(nome, email, senha)
    logger.info("usuario criado id=%s", usuario_id)
    return usuario_id


def login(dados):
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email"), dados.get("senha")
    if not isinstance(email, str) or not isinstance(senha, str) or not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.autenticar(email.strip(), senha)
    if usuario is None:
        logger.info("login recusado")
        raise UnauthorizedError("Email ou senha inválidos")
    logger.info("login ok usuario_id=%s", usuario["id"])
    return usuario
