"""Ручной отбор повторяющихся кадров; импорт не восстанавливает повторы."""

import json
from functools import cache
from pathlib import Path


@cache
def gallery_rules():
    source = Path(__file__).parent / 'data/gallery_curation.json'
    return json.loads(source.read_text())['series']


def hidden_factory_photo(slug, source_url):
    rule = gallery_rules().get(slug, {})
    return source_url in rule.get('hidden_source_urls', [])
