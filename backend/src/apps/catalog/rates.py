import json
from datetime import date
from decimal import Decimal
from urllib.request import urlopen

NBRB_URL = 'https://api.nbrb.by/exrates/rates/{code}?parammode=2'
TIMEOUT = 10


def fetch_rate(code: str) -> tuple[date, Decimal]:
    """Официальный курс Нацбанка РБ: BYN за одну единицу валюты."""
    url = NBRB_URL.format(code=code)
    with urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310
        data = json.loads(response.read(), parse_float=Decimal)
    rate = Decimal(data['Cur_OfficialRate']) / Decimal(data['Cur_Scale'])
    return date.fromisoformat(data['Date'][:10]), rate
