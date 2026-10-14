import hmac
from functools import wraps

from flask import current_app, request

from src.errors import ForbiddenError, UnauthorizedError


def require_admin(view):
    """Exige X-Admin-Token igual a ADMIN_TOKEN. Sem ADMIN_TOKEN configurado, a rota fica fechada."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        esperado = current_app.config.get("ADMIN_TOKEN")
        if not esperado:
            raise ForbiddenError("Rotas administrativas desabilitadas")
        recebido = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(recebido.encode(), esperado.encode()):
            raise UnauthorizedError("Acesso negado")
        return view(*args, **kwargs)
    return wrapper
