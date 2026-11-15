"""Страница серии на kztoradiator.ru: описание, параметры, документы, фото.

Сайт собран из шаблона MODX, поэтому блоки узнаём по классам: описание —
`.catalog-text .content-style`, примечание под ним — `.catalog-bottom-text`,
параметры — таблица в `.catalog4-params`, документы — ссылки
`.documentation-pdf__name` под заголовками разделов `.job-lvl*-link`,
фото — `.catalog-gall__item img.des`.
"""

import re
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

VOID = frozenset(
    {
        'area',
        'base',
        'br',
        'col',
        'embed',
        'hr',
        'img',
        'input',
        'link',
        'meta',
        'param',
        'source',
        'track',
        'wbr',
    },
)
SPACES = re.compile(r'\s+')
# Отсылки к ссылкам и вкладкам их сайта — у нас их нет
FOREIGN_NOTE = re.compile(
    r'закладке|по ссылке|ознакомьтесь',
    re.IGNORECASE,
)
# Строка примечания «- …» — пункт списка ограничений
LIST_ITEM = re.compile(r'^[-–—•]\s*')
PARAMS_TITLE = 'Характеристики'


@dataclass
class Document:
    section: str
    title: str
    url: str


@dataclass
class Page:
    # (тег, текст): 'p' — абзац, 'li' — пункт списка
    description: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    params: list[tuple[str, str]] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    gallery: list[str] = field(default_factory=list)

    def param(self, name: str) -> str:
        return next((v for n, v in self.params if n == name), '')

    def html(self) -> str:
        """Описание для серии: текст завода, параметры списком и
        примечания: комплектация, ограничения исполнений."""
        parts = _blocks(self.description)
        if self.params:
            parts.append(f'<h3>{PARAMS_TITLE}</h3>')
            parts.append(
                _list(f'{name}: {value}' for name, value in self.params),
            )
        notes = []
        for note in self.notes:
            if FOREIGN_NOTE.search(note):
                continue
            if LIST_ITEM.match(note):
                notes.append(('li', LIST_ITEM.sub('', note)))
            else:
                notes.append(('p', note))
        parts += _blocks(notes)
        return '\n'.join(parts)


def _blocks(lines) -> list[str]:
    """Абзацы как есть, подряд идущие пункты — одним списком."""
    parts, items = [], []
    for tag, text in lines:
        if tag == 'li':
            items.append(text)
            continue
        if items:
            parts.append(_list(items))
            items = []
        parts.append(f'<p>{escape(text)}</p>')
    if items:
        parts.append(_list(items))
    return parts


def _list(items) -> str:
    rows = ''.join(f'<li>{escape(item)}</li>' for item in items)
    return f'<ul>{rows}</ul>'


def _clean(text: str) -> str:
    return SPACES.sub(' ', text).strip()


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.page = Page()
        self.stack: list[tuple[str, frozenset]] = []
        self.buffer: list[str] | None = None
        self.capture = ''
        self.row: list[str] = []
        self.href = ''
        self.section = ''

    def inside(self, name: str) -> bool:
        return any(name in classes for _, classes in self.stack)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = frozenset((attributes.get('class') or '').split())
        if tag == 'img':
            if 'des' in classes and self.inside('catalog-gall__item'):
                self.page.gallery.append(attributes.get('src') or '')
            return
        if tag not in VOID:
            self.stack.append((tag, classes))
        if self.buffer is None:
            self.begin(tag, classes, attributes)

    def begin(self, tag: str, classes: frozenset, attributes: dict):
        """Начинает собирать текст, если тег — начало нужного блока."""
        if tag in ('p', 'li') and self.inside('content-style'):
            if self.inside('catalog-text'):
                self.start(tag)
            elif self.inside('catalog-bottom-text'):
                self.start('note')
        elif tag == 'td' and self.inside('catalog4-params'):
            self.start('td')
        elif tag == 'a' and 'documentation-pdf__name' in classes:
            self.href = attributes.get('href') or ''
            self.start('doc')
        elif tag == 'a' and any(c.startswith('job-lvl') for c in classes):
            self.start('section')

    def start(self, capture: str):
        self.capture = capture
        self.buffer = []

    def handle_data(self, data):
        if self.buffer is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.buffer is not None and self.ends_capture(tag):
            self.finish(_clean(''.join(self.buffer)))
            self.buffer = None
        if tag == 'tr' and self.row:
            if len(self.row) >= 2 and self.row[0]:
                name = self.row[0].removesuffix(':').strip()
                self.page.params.append((name, self.row[1]))
            self.row = []
        # Разметка бывает с незакрытыми тегами: снимаем до своего
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def ends_capture(self, tag: str) -> bool:
        expected = {'note': 'p', 'doc': 'a', 'section': 'a'}
        return tag == expected.get(self.capture, self.capture) or (
            self.capture == 'note' and tag == 'li'
        )

    def finish(self, text: str):
        page = self.page
        if self.capture in ('p', 'li'):
            if text:
                page.description.append((self.capture, text))
        elif self.capture == 'note':
            if text:
                page.notes.append(text)
        elif self.capture == 'td':
            self.row.append(text)
        elif self.capture == 'doc':
            page.documents.append(Document(self.section, text, self.href))
        elif self.capture == 'section':
            self.section = text


def _unique(items: list) -> list:
    # Описание на странице дважды — для компьютера и телефона
    return list(dict.fromkeys(items))


def parse_page(html: str) -> Page:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    page = parser.page
    page.description = _unique(page.description)
    page.notes = _unique(page.notes)
    page.params = _unique(page.params)
    page.gallery = _unique(page.gallery)
    seen, documents = set(), []
    for document in page.documents:
        if document.url not in seen:
            seen.add(document.url)
            documents.append(document)
    page.documents = documents
    return page
