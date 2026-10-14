import logging

from src.database import db
from src.errors import ForbiddenError, UnauthorizedError, ValidationError
from src.models import User
from src.services.token_service import issue_token
from src.utils import validators as v

logger = logging.getLogger(__name__)


def login(data):
    v.require_object(data)
    email = data.get('email')
    password = data.get('password')
    if not (isinstance(email, str) and email and isinstance(password, str) and password):
        raise ValidationError('Email e senha são obrigatórios')

    user = User.get_by_email(email)
    if user is None or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    if user.has_legacy_password_hash():
        user.set_password(password)
        db.session.commit()
        logger.info('hash de senha migrado user_id=%s', user.id)

    logger.info('login ok user_id=%s', user.id)
    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user.id),
    }
