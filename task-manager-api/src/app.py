"""Composition root: config, banco, CORS, blueprints e tratamento de erro."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Config
from src.database import db
from src.middlewares.error_handler import register_error_handlers
from src.views import auth_routes, category_routes, health_routes, report_routes, task_routes, user_routes

BLUEPRINTS = (health_routes.bp, task_routes.bp, user_routes.bp, auth_routes.bp,
              category_routes.bp, report_routes.bp)


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    logging.basicConfig(level=app.config['LOG_LEVEL'],
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    if not app.config['SECRET_KEY_FROM_ENV']:
        app.logger.warning('SECRET_KEY não definida: chave aleatória gerada; tokens expiram a cada restart')

    db.init_app(app)
    if app.config['CORS_ORIGINS']:
        CORS(app, origins=app.config['CORS_ORIGINS'])

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()  # sem ferramenta de migração no projeto; cria só tabelas ausentes

    return app
