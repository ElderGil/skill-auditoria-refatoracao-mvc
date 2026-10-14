"""Validação de entrada reutilizada por criar e atualizar. Toda falha vira ValidationError (400)."""
from datetime import datetime

from src.errors import ValidationError

INVALID_DATA = 'Dados inválidos'


def require_object(data, allow_empty=False):
    if not isinstance(data, dict) or (not data and not allow_empty):
        raise ValidationError(INVALID_DATA)
    return data


def text(value, *, required_message, invalid_message=None, min_len=1, max_len=None,
         too_short_message=None, too_long_message=None):
    """Texto obrigatório, sem espaços nas pontas, dentro dos limites."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(required_message)
    if not isinstance(value, str):
        raise ValidationError(invalid_message or required_message)
    value = value.strip()
    if len(value) < min_len:
        raise ValidationError(too_short_message or required_message)
    if max_len is not None and len(value) > max_len:
        raise ValidationError(too_long_message or required_message)
    return value


def optional_text(value, *, message, max_len=None):
    if value is None:
        return None
    if not isinstance(value, str) or (max_len is not None and len(value) > max_len):
        raise ValidationError(message)
    return value


def integer(value, *, message, minimum=None, maximum=None):
    """Inteiro de verdade: rejeita bool, texto e fração (2.0 é aceito como 2)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(message)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValidationError(message)
        value = int(value)
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValidationError(message)
    return value


def optional_id(value, *, message):
    if value is None:
        return None
    return integer(value, message=message)


def boolean(value, *, message):
    if not isinstance(value, bool):
        raise ValidationError(message)
    return value


def choice(value, options, *, message):
    if not isinstance(value, str) or value not in options:
        raise ValidationError(message)
    return value


def date(value, fmt, *, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, fmt)
    except ValueError:
        raise ValidationError(message) from None


def pattern(value, regex, *, message):
    if not isinstance(value, str) or not regex.match(value):
        raise ValidationError(message)
    return value


def string_list_or_text(value, *, message):
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ValidationError(message)
        return value
    if value is None or isinstance(value, str):
        return value
    raise ValidationError(message)


def query_int(value, *, message):
    """Parâmetro de query string opcional que precisa ser inteiro."""
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(message) from None
