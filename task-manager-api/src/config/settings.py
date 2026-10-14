import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _csv(name):
    return [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]


class Config:
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', '5000'))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Sem SECRET_KEY no ambiente, cada processo gera a sua: tokens não sobrevivem a um restart.
    SECRET_KEY_FROM_ENV = bool(os.environ.get('SECRET_KEY'))
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '28800'))

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Vazio = CORS desligado (só a mesma origem).
    CORS_ORIGINS = _csv('CORS_ORIGINS')

    SMTP_HOST = os.environ.get('SMTP_HOST', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
