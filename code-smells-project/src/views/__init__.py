from src.views import (admin_routes, pedido_routes, produto_routes, relatorio_routes, sistema_routes,
                       usuario_routes)

BLUEPRINTS = [
    produto_routes.bp,
    usuario_routes.bp,
    pedido_routes.bp,
    relatorio_routes.bp,
    sistema_routes.bp,
    admin_routes.bp,
]
