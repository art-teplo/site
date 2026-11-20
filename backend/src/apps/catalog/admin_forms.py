"""Рабочие поля подключения; происхождение остаётся в служебном блоке."""

from django import forms

from .models import ConnectionOption, Variant


class ConnectionOptionForm(forms.ModelForm):
    configuration_surcharge_rub = forms.DecimalField(
        label='Доплата за конфигурацию, RUB',
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text='Пусто — цена подключения по запросу. Подтверждённая установочная часть включена в сумму.',
    )
    allowed_sections = forms.TypedMultipleChoiceField(
        label='Доступные секции',
        coerce=int,
        widget=forms.CheckboxSelectMultiple,
        help_text='Точное множество секций, а не только чётность или границы диапазона.',
    )

    class Meta:
        model = ConnectionOption
        fields = [
            'series',
            'label',
            'tubes',
            'connection',
            'mount',
            'thermovalve',
            'allowed_sections',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['series'].disabled = True
        series = (
            self.data.get('series')
            if self.is_bound and not self.instance.pk
            else self.instance.series_id
        )
        tubes = (
            self.data.get('tubes') if self.is_bound else self.instance.tubes
        )
        try:
            query = Variant.objects.filter(
                series_id=int(series), tubes=int(tubes)
            )
        except TypeError, ValueError:
            query = Variant.objects.none()
        numbers = (
            query.exclude(sections__isnull=True)
            .order_by('sections')
            .values_list('sections', flat=True)
            .distinct()
        )
        self.fields['allowed_sections'].choices = [
            (n, str(n)) for n in numbers
        ]
        if self.instance.pk and self.instance.surcharge_rub is not None:
            self.initial['configuration_surcharge_rub'] = (
                self.instance.surcharge_rub + self.instance.base_adjustment_rub
            )

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get('configuration_surcharge_rub')
        install = self.instance.base_adjustment_rub
        if total is not None and total < install:
            self.add_error(
                'configuration_surcharge_rub',
                f'Сумма не может быть меньше подтверждённой установочной части {install} RUB',
            )
        else:
            self.instance.surcharge_rub = (
                None if total is None else total - install
            )
        return cleaned


class ConnectionPreviewForm(forms.Form):
    article = forms.CharField(label='Базовый артикул', max_length=100)
