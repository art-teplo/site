"""Разбор поискового запроса: слова, раскладка клавиатуры, синонимы.

Каждое слово должно найтись хоть в одном поле серии (название, бренд, тип,
категория) или совпасть с артикулом: «guardo retta» находит Retta бренда
Guardo, хотя целиком строки нет ни в одном поле. Запрос пробуем как есть,
в другой раскладке («udfhlj» → «гуардо»), с синонимами («гуардо» → «guardo»,
«батарея» → «радиатор») и латиницей («ретта» → «retta») — для каждого слова
отдельно.
"""

from django.db.models import Q

from .models import Variant

MIN_WORD = 2
# Больше слов в запросе по каталогу не нужно, а каждое — до 9 форм с
# подзапросом: без потолка длинный запрос из коротких слов грузил базу
MAX_WORDS = 5

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
_RU = 'йцукенгшщзхъфывапролджэячсмитьбюё'
TO_RU = str.maketrans(_EN, _RU)
TO_EN = str.maketrans(_RU, _EN)
# Кириллица → латиница для названий моделей (Retta, Siluet, Pilon, Torre)
TRANSLIT = dict(
    zip(
        'абвгдезийклмнопрстуфхцы',
        [
            'a',
            'b',
            'v',
            'g',
            'd',
            'e',
            'z',
            'i',
            'i',
            'k',
            'l',
            'm',
            'n',
            'o',
            'p',
            'r',
            's',
            't',
            'u',
            'f',
            'h',
            'c',
            'y',
        ],
        strict=True,
    ),
)
TRANSLIT.update(
    {
        'ж': 'zh',
        'ч': 'ch',
        'ш': 'sh',
        'щ': 'sch',
        'ю': 'yu',
        'я': 'ya',
        'э': 'e',
        'ь': '',
        'ъ': '',
    }
)

# Начало слова → как оно записано в базе. Ключ — основа: «батареи»,
# «батарею» тоже. Бренды — русской транслитерацией, как их называют по телефону
SYNONYMS = {
    'гуардо': 'guardo',
    'гвардо': 'guardo',
    'нова': 'nova',
    'новa': 'nova',
    'kzto': 'кзто',
    'radimax': 'радимакс',
    'роял': 'royal',
    'ройял': 'royal',
    'термо': 'thermo',
    'кариса': 'carisa',
    'карис': 'carisa',
    'рубинетери': 'rubinetterie',
    'батаре': 'радиатор',
    'полотенчик': 'полотенцесушител',
    'сушилк': 'полотенцесушител',
    'полотенцесуш': 'полотенцесушител',
    'конвектор': 'конвектор',
    'чугун': 'чугунн',
    'алюмин': 'алюминиев',
    'трубчат': 'трубчат',
    'вентил': 'вентил',
    'кран': 'вентил',
    'термоголовк': 'автоматик',
}


def _synonym(word: str) -> str:
    for stem, target in SYNONYMS.items():
        if word.startswith(stem):
            return target
    return word


def _translit(word: str) -> str:
    return ''.join(TRANSLIT.get(ch, ch) for ch in word)


def forms(word: str) -> list[str]:
    """Как ещё могли иметь в виду слово: другая раскладка, синоним,
    латиница («ретта» → «retta», «силует» → «siluet»)."""
    result = []
    for variant in (word, word.translate(TO_RU), word.translate(TO_EN)):
        for candidate in (variant, _synonym(variant), _translit(variant)):
            if candidate not in result:
                result.append(candidate)
    return result


def words(query: str) -> list[str]:
    """Слова запроса без повторов, не больше MAX_WORDS; короче двух букв
    отбрасываются (кроме цифр артикула)."""
    text = query.lower().replace('ё', 'е')
    found = [w for w in text.split() if len(w) >= MIN_WORD or w.isdigit()]
    return list(dict.fromkeys(found))[:MAX_WORDS]


def _text(word: str) -> Q:
    return (
        Q(name__icontains=word)
        | Q(brand__name__icontains=word)
        | Q(subcategory__name__icontains=word)
        | Q(category__name__icontains=word)
    )


def _articles(candidates: list[str]) -> Q:
    # Артикул — подзапросом, не соединением: join с вариантами (десятки
    # тысяч строк) размножал серии, и план Postgres уходил в минуты.
    # Один подзапрос на слово, все его формы — внутри
    match = Q()
    for candidate in candidates:
        match |= Q(article__iexact=candidate)
    return Q(pk__in=Variant.objects.filter(match).values('series_id'))


def series_filter(query: str) -> Q | None:
    """Q для Series: каждое слово запроса — в любой своей форме. Формы
    подбираются для каждого слова отдельно, поэтому «udfhlj ретта»
    (раскладка + кириллица) тоже находит Guardo Retta. None — искать нечего."""
    found = words(query)
    if not found:
        return None
    every = Q()
    for word in found:
        candidates = forms(word)
        any_form = _articles(candidates)
        for form in candidates:
            any_form |= _text(form)
        every &= any_form
    return every
