from flask import Blueprint, jsonify, request

from src.controllers import user_controller
from src.middlewares.auth import current_user, require_admin, require_auth

bp = Blueprint('users', __name__)


@bp.get('/users')
def list_users():
    return jsonify(user_controller.list_users()), 200


@bp.get('/users/<int:user_id>')
def get_user(user_id):
    return jsonify(user_controller.get_user(user_id)), 200


@bp.post('/users')
def create_user():
    return jsonify(user_controller.create_user(request.get_json(), current_user())), 201


@bp.put('/users/<int:user_id>')
@require_auth
def update_user(user_id):
    return jsonify(user_controller.update_user(user_id, request.get_json(), current_user())), 200


@bp.delete('/users/<int:user_id>')
@require_admin
def delete_user(user_id):
    return jsonify(user_controller.delete_user(user_id)), 200


@bp.get('/users/<int:user_id>/tasks')
def list_user_tasks(user_id):
    return jsonify(user_controller.list_user_tasks(user_id)), 200
