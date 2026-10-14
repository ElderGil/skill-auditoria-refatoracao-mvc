from datetime import datetime

from flask import Blueprint

bp = Blueprint('health', __name__)


@bp.get('/health')
def health():
    return {'status': 'ok', 'timestamp': str(datetime.now())}


@bp.get('/')
def index():
    return {'message': 'Task Manager API', 'version': '1.0'}
