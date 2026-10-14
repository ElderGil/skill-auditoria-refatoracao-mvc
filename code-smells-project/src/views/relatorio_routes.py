from flask import Blueprint, jsonify

from src.controllers import relatorio_controller

bp = Blueprint("relatorios", __name__)


@bp.get("/relatorios/vendas")
def relatorio_vendas():
    return jsonify({"dados": relatorio_controller.vendas(), "sucesso": True}), 200
