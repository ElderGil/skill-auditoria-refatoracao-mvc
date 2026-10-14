"""Composition root: cria a app, carrega a config, inicializa o banco e registra rotas e handlers."""
import logging

from flask import Flask
from flask_cors import CORS

from src import database, seed
from src.config import Config
from src.middlewares.error_handler import register_error_handlers
from src.models import pedido_model, produto_model, usuario_model
from src.views import BLUEPRINTS

logger = logging.getLogger(__name__)


def _inicializar_banco():
    with database.transacao():
        produto_model.criar_tabela()
        usuario_model.criar_tabela()
        pedido_model.criar_tabelas()
        if seed.popular_se_vazio():
            logger.info("banco vazio: dados de exemplo carregados")
        migradas = usuario_model.migrar_senhas_legadas()
    if migradas:
        logger.info("%s senha(s) em texto puro convertida(s) para hash", migradas)


def create_app(config=Config):
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(config)
    if not app.config.get("SECRET_KEY_FROM_ENV"):
        logger.warning("SECRET_KEY não definida no ambiente; usando chave aleatória gerada neste boot")

    CORS(app, origins=app.config["CORS_ORIGINS"])
    database.init_app(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    register_error_handlers(app)

    with app.app_context():
        _inicializar_banco()
    return app
