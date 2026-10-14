from flask import Blueprint, jsonify

from src.controllers import report_controller

bp = Blueprint('reports', __name__)


@bp.get('/reports/summary')
def summary_report():
    return jsonify(report_controller.summary_report()), 200


@bp.get('/reports/user/<int:user_id>')
def user_report(user_id):
    return jsonify(report_controller.user_report(user_id)), 200
