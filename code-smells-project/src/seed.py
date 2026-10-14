"""Dados de exemplo carregados no primeiro boot (banco sem produtos)."""
from src.models import produto_model, usuario_model

PRODUTOS_EXEMPLO = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Contas de demonstração (documentadas no README). As senhas são gravadas como hash.
USUARIOS_EXEMPLO = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


def popular_se_vazio():
    """Sem commit: quem chama abre a transação."""
    if produto_model.contar() > 0:
        return False
    for produto in PRODUTOS_EXEMPLO:
        produto_model.inserir(*produto)
    for nome, email, senha, tipo in USUARIOS_EXEMPLO:
        if not usuario_model.email_cadastrado(email):
            usuario_model.inserir(nome, email, senha, tipo)
    return True
