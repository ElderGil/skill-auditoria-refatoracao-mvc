from flask import Blueprint, current_app, jsonify

from src.controllers import sistema_controller

bp = Blueprint("sistema", __name__)


@bp.get("/")
def index():
    return jsonify(sistema_controller.indice(current_app.config["VERSAO_API"]))


@bp.get("/health")
def health_check():
    corpo, saudavel = sistema_controller.health(current_app.config)
    return jsonify(corpo), 200 if saudavel else 500
