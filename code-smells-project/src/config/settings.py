import os
import secrets


def _lista(valor):
    return [item.strip() for item in valor.split(",") if item.strip()]


class Config:
    """Configuração lida do ambiente. Nenhum segredo tem valor literal no código."""

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    SECRET_KEY_FROM_ENV = bool(os.environ.get("SECRET_KEY"))
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = _lista(os.environ.get("CORS_ORIGINS", "*"))
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or None
    AMBIENTE = os.environ.get("APP_ENV", "producao")
    VERSAO_API = "1.0.0"
