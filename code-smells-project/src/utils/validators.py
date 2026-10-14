"""Validação de entrada reutilizada pelos controllers. Erros viram 400 no error handler."""
import math

from src.errors import ValidationError


def exigir_objeto(dados, mensagem="Dados inválidos"):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError(mensagem)
    return dados


def numero(valor, mensagem):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValidationError(mensagem)
    return valor


def inteiro(valor, mensagem):
    if isinstance(valor, bool):
        raise ValidationError(mensagem)
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    raise ValidationError(mensagem)


def identificador(valor, mensagem):
    """Inteiro positivo; aceita também texto só com dígitos ("2"), como a API original aceitava."""
    if isinstance(valor, str) and valor.strip().isdigit():
        valor = int(valor.strip())
    valor = inteiro(valor, mensagem)
    if valor < 1:
        raise ValidationError(mensagem)
    return valor


def texto(valor, mensagem, max_len=None, mensagem_tamanho=None):
    if not isinstance(valor, str) or not valor.strip():
        raise ValidationError(mensagem)
    valor = valor.strip()
    if max_len is not None and len(valor) > max_len:
        raise ValidationError(mensagem_tamanho or mensagem)
    return valor


def numero_de_query(valor, campo):
    """Parâmetro de query opcional convertido para float; vazio vira None."""
    if valor is None or valor == "":
        return None
    try:
        convertido = float(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"{campo} deve ser numérico") from None
    if not math.isfinite(convertido):
        raise ValidationError(f"{campo} deve ser numérico")
    return convertido
