from flask import Blueprint, jsonify

from src.controllers import admin_controller
from src.middlewares.auth import require_admin

bp = Blueprint("admin", __name__)


@bp.post("/admin/reset-db")
@require_admin
def reset_database():
    admin_controller.resetar_banco()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
