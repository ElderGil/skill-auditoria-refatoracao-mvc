import logging
import os

from src.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    logging.getLogger(__name__).info("servidor iniciando em http://%s:%s", host, port)
    app.run(host=host, port=port, debug=app.config["DEBUG"])
