import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.errors import AppError

logger = logging.getLogger(__name__)


def _erro(mensagem, status):
    return jsonify({"erro": mensagem, "sucesso": False}), status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return _erro(err.mensagem, err.status)

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return _erro(err.description, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(_err):
        logger.exception("erro não tratado")
        return _erro("Erro interno", 500)
