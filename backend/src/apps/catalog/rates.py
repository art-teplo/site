import json
from datetime import date
from decimal import Decimal
from urllib.request import urlopen

NBRB_URL = 'https://api.nbrb.by/exrates/rates/{code}?parammode=2'
TIMEOUT = 10
BAD_RATE = 'Нацбанк вернул некорректный курс'


def fetch_rate(code: str) -> tuple[date, Decimal]:
    """Официальный курс Нацбанка РБ: BYN за одну единицу валюты."""
    url = NBRB_URL.format(code=code)
    with urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310
        data = json.loads(response.read(), parse_float=Decimal)
    scale = Decimal(data['Cur_Scale'])
    official = Decimal(data['Cur_OfficialRate'])
    if not scale.is_finite() or scale <= 0:
        raise ValueError(BAD_RATE)
    rate = official / scale
    if not rate.is_finite() or rate <= 0:
        raise ValueError(BAD_RATE)
    return date.fromisoformat(data['Date'][:10]), rate
