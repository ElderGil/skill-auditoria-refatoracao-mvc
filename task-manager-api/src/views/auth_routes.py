from flask import Blueprint, jsonify, request

from src.controllers import auth_controller

bp = Blueprint('auth', __name__)


@bp.post('/login')
def login():
    return jsonify(auth_controller.login(request.get_json())), 200
