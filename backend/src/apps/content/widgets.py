from django import forms
from django.contrib import messages
from django.utils.html import format_html


class FocusWidget(forms.TextInput):
    """Точка фокуса фото: превью с меткой, клик ставит «x y» в процентах,
    рядом — как фото обрежется в рамках 4:5 и 16:9 (focus.js).

    Адрес сохранённого фото кладёт в data-src ImageModelForm, новое
    выбранное focus.js берёт из соседнего поля «фото» той же формы."""

    class Media:
        js = ['content/focus.js']
        css = {'all': ['content/focus.css']}

    def __init__(self, attrs=None):
        super().__init__(
            {
                'class': 'focus-input',
                'size': 7,
                'inputmode': 'numeric',
                **(attrs or {}),
            },
        )

    def render(self, name, value, attrs=None, renderer=None):
        field = super().render(name, value, attrs, renderer)
        return format_html(
            '<div class="focus-picker" data-focus-for="{}">'
            '<div class="focus-picker__stage" hidden>'
            '<div class="focus-picker__frame">'
            '<img class="focus-picker__img" alt="">'
            '<span class="focus-picker__dot"></span>'
            '</div>'
            '<div class="focus-picker__crops">'
            '<span class="focus-picker__crop focus-picker__crop--v"></span>'
            '<span class="focus-picker__crop focus-picker__crop--h"></span>'
            '</div>'
            '</div>'
            '<p class="focus-picker__empty">'
            'Загрузите фото — здесь появится превью'
            '</p>'
            '{}'
            '</div>',
            name,
            field,
        )


class ImageModelForm(forms.ModelForm):
    """Форма модели с фото (WithImage): виджет фокуса знает адрес фото,
    подсказка к полю «фото» — из IMAGE_HINT модели."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hint, _ = getattr(self._meta.model, 'IMAGE_HINT', ('', 0))
        if hint and 'image' in self.fields:
            self.fields['image'].help_text = hint
        if 'image_focus' in self.fields:
            widget = FocusWidget()
            if self.instance.pk and self.instance.image:
                widget.attrs['data-src'] = self.instance.image.url
            self.fields['image_focus'].widget = widget


def warn_small_image(request, obj):
    """После сохранения: фото уже рамки на сайте — будет мыльным и
    «зазумленным». Не ошибка, а предупреждение: менеджер решает сам."""
    hint, min_width = getattr(obj, 'IMAGE_HINT', ('', 0))
    width = getattr(obj, 'image_width', None)
    # в инлайнах серии есть строки без фото (группы цветов, файлы)
    image = getattr(obj, 'image', None)
    if image and width and min_width and width < min_width:
        messages.warning(
            request,
            f'«{obj}»: фото {width} px в ширину, для этой рамки нужно от '
            f'{min_width} px — на сайте оно будет нечётким. {hint}.',
        )


class InlineImagesAdminMixin:
    """ModelAdmin, у которого фото в инлайнах (серия, проект): предупреждение
    о маленьком фото для каждой сохранённой строки."""

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        for item in formset.new_objects + [
            o for o, _ in formset.changed_objects
        ]:
            warn_small_image(request, item)


class ImageAdminMixin(InlineImagesAdminMixin):
    """ModelAdmin записи с фото: форма с фокусом и предупреждение о
    маленьком фото."""

    form = ImageModelForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        warn_small_image(request, obj)
