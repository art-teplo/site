from pathlib import Path

from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import Lead

PHONE_MESSAGE = 'Номер в формате +375 29 123-45-67'
CONSENT_MESSAGE = 'Нужно согласие, иначе мы не сможем перезвонить'
BELARUS_CODE = 375


class LeadCreateSerializer(serializers.ModelSerializer):
    """Заявка из формы сайта (multipart: поля + необязательный файл).

    Проверки файла — валидаторы поля модели (models.py).
    """

    phone = PhoneNumberField(
        region='BY',
        error_messages={
            'invalid': PHONE_MESSAGE,
        },
    )
    consent = serializers.BooleanField()

    class Meta:
        model = Lead
        fields = [
            'name',
            'phone',
            'contact_method',
            'comment',
            'company',
            'city',
            'file',
            'source',
            'page',
            'context',
            'consent',
            'consent_version',
        ]
        extra_kwargs = {
            'comment': {
                'max_length': 2000,
            },
            'context': {
                'max_length': 1000,
            },
            'file': {
                'allow_empty_file': False,
            },
        }

    def validate_phone(self, value):
        # Шоурум в Минске, доставка по Беларуси: только номера РБ
        if value.country_code != BELARUS_CODE:
            raise serializers.ValidationError(PHONE_MESSAGE)
        return value

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(CONSENT_MESSAGE)
        return value

    def create(self, validated_data):
        validated_data.pop('consent')
        file = validated_data.get('file')
        if file:
            validated_data['file_name'] = Path(file.name).name[:255]
        return super().create(validated_data)
