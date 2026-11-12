import pytest

from apps.leads.sources import is_product, source_label


@pytest.mark.parametrize(
    ('source', 'label', 'product'),
    [
        ('series/guardo-pilon', 'Карточка товара', True),
        ('product/guardo-retta', 'Карточка товара', True),
        ('catalog/radiatory', 'Каталог', False),
        ('catalog', 'Каталог', False),
        ('blog:kak-vybrat-radiator', 'Статья блога', False),
        ('blog', 'Блог', False),
        ('home:paths', 'Главная, «С чего начнём?»', False),
        ('quiz', 'Квиз', False),
        ('new-form', 'new-form', False),
    ],
)
def test_source_label(source, label, product):
    # Те же source, что шлёт LeadForm на фронте
    assert source_label(source) == label
    assert is_product(source) is product
