"""Identidade da requisição: `Authorization: Bearer <token emitido pelo /login>`."""
from functools import wraps

from flask import g, request

from src.errors import ForbiddenError, UnauthorizedError
from src.models import User
from src.services.token_service import read_token

_NO_USER = object()


def current_user():
    """Usuário ativo dono do token, ou None (sem cabeçalho, token inválido/expirado, usuário inativo)."""
    cached = g.get('current_user', _NO_USER)
    if cached is not _NO_USER:
        return cached
    user = None
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme.lower() == 'bearer' and token:
        user_id = read_token(token.strip())
        if user_id is not None:
            candidate = User.get(user_id)
            if candidate is not None and candidate.active:
                user = candidate
    g.current_user = user
    return user


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            raise UnauthorizedError('Autenticação necessária')
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            raise UnauthorizedError('Autenticação necessária')
        if not user.is_admin():
            raise ForbiddenError('Acesso restrito a administradores')
        return view(*args, **kwargs)
    return wrapper
