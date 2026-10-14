from src.models import pedido_model

# (faturamento mínimo exclusivo, percentual de desconto), da maior faixa para a menor
FAIXAS_DESCONTO = [
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
]


def desconto_aplicavel(faturamento):
    for minimo, percentual in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * percentual
    return 0


def vendas():
    resumo = pedido_model.resumo_por_status()
    total_pedidos = sum(quantidade for quantidade, _ in resumo.values())
    cancelados, _ = resumo.get(pedido_model.STATUS_CANCELADO, (0, 0))

    # Pedidos cancelados não contam como faturamento.
    faturamento = sum(soma for status, (_, soma) in resumo.items()
                      if status != pedido_model.STATUS_CANCELADO)
    pedidos_faturados = total_pedidos - cancelados
    desconto = desconto_aplicavel(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": resumo.get(pedido_model.STATUS_PENDENTE, (0, 0))[0],
        "pedidos_aprovados": resumo.get(pedido_model.STATUS_APROVADO, (0, 0))[0],
        "pedidos_cancelados": cancelados,
        "ticket_medio": round(faturamento / pedidos_faturados, 2) if pedidos_faturados > 0 else 0,
    }
