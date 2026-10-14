from datetime import datetime, timezone


def now_utc():
    """Agora em UTC, sem tzinfo: compatível com as colunas DateTime e com o formato do JSON."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_today():
    return now_utc().date()
