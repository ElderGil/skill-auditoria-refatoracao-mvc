from flask import Blueprint, jsonify, request

from src.controllers import category_controller
from src.middlewares.auth import require_admin

bp = Blueprint('categories', __name__)


@bp.get('/categories')
def list_categories():
    return jsonify(category_controller.list_categories()), 200


@bp.post('/categories')
def create_category():
    return jsonify(category_controller.create_category(request.get_json())), 201


@bp.put('/categories/<int:category_id>')
def update_category(category_id):
    return jsonify(category_controller.update_category(category_id, request.get_json())), 200


@bp.delete('/categories/<int:category_id>')
@require_admin
def delete_category(category_id):
    return jsonify(category_controller.delete_category(category_id)), 200
