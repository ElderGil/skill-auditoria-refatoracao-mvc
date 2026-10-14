"""Token de acesso assinado com a SECRET_KEY e com validade (TOKEN_MAX_AGE, em segundos)."""
from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

_SALT = 'auth-token'


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SALT)


def issue_token(user_id):
    return _serializer().dumps({'uid': user_id})


def read_token(token):
    """Devolve o id do usuário, ou None se o token for inválido ou estiver expirado."""
    try:
        payload = _serializer().loads(token, max_age=current_app.config['TOKEN_MAX_AGE'])
    except BadSignature:
        return None
    user_id = payload.get('uid') if isinstance(payload, dict) else None
    return user_id if isinstance(user_id, int) else None
