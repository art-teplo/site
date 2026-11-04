"""Чистка HTML из редактора статей (Trix в Unfold).

Остаются только теги, которые фронт умеет оформить; стили, классы,
скрипты и картинки уходят. Заголовок статьи на странице — h1, поэтому
h1 из редактора становится h2.
"""

import re

import nh3

ALLOWED_TAGS = {
    'h2',
    'h3',
    'h4',
    'p',
    'br',
    'strong',
    'b',
    'em',
    'i',
    'u',
    's',
    'del',
    'a',
    'ul',
    'ol',
    'li',
    'blockquote',
}
ALLOWED_ATTRIBUTES = {
    'a': {'href'},
}
URL_SCHEMES = {'http', 'https', 'mailto', 'tel'}

WORDS_PER_MINUTE = 180

H1 = re.compile(r'<(/?)h1\b', re.IGNORECASE)
# Trix пишет абзацы как <div>…</div>; пустые абзацы — <div><br></div>
DIV = re.compile(r'<(/?)div\b', re.IGNORECASE)
EMPTY_P = re.compile(r'<p>(\s|<br>)*</p>')


def clean_html(html: str) -> str:
    html = H1.sub(r'<\1h2', html)
    html = DIV.sub(r'<\1p', html)
    html = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        link_rel='noopener noreferrer',
    )
    return EMPTY_P.sub('', html).strip()


def read_minutes(html: str) -> int:
    words = len(nh3.clean(html, tags=set()).split())
    return max(1, round(words / WORDS_PER_MINUTE))
