from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Lead
from .tasks import notify_lead, sync_lead_message

TG_SENT = 'Отправлена в группу'
TG_FILE_PENDING = 'Отправлена, файл — ещё нет'
TG_NOT_SENT = 'Не отправлена'


def without_context(fields):
    return [field for field in fields if field != 'context']


class AssignedFilter(admin.SimpleListFilter):
    title = 'ответственный'
    parameter_name = 'assigned'

    def lookups(self, request, model_admin):  # noqa: ARG002
        return [('yes', 'Взята'), ('no', 'Свободна')]

    def queryset(self, request, queryset):  # noqa: ARG002
        if self.value() == 'yes':
            return queryset.exclude(assignee_name='')
        if self.value() == 'no':
            return queryset.filter(assignee_name='')
        return queryset


@admin.register(Lead)
class LeadAdmin(ModelAdmin):
    list_display = [
        '__str__',
        'created_at',
        'name',
        'phone',
        'source_display',
        'assignee_name',
        'notified',
    ]
    list_filter = [AssignedFilter, 'contact_method', 'created_at']
    search_fields = ['name', 'phone', 'comment', 'company']
    actions = ['resend']
    fieldsets = [
        (
            'Клиент',
            {
                'fields': [
                    'name',
                    'phone',
                    'contact_method',
                    'company',
                    'city',
                    'comment',
                    'file_link',
                ],
            },
        ),
        (
            'Откуда',
            {
                'fields': [
                    'source_display',
                    'page_link',
                    'context',
                    'created_at',
                ],
            },
        ),
        ('Ответственный', {'fields': ['assignee_name', 'assigned_at']}),
        (
            'Согласие (Закон № 99-З)',
            {'fields': ['consent_at', 'consent_ip', 'consent_version']},
        ),
        ('Telegram', {'fields': ['tg_status']}),
    ]
    readonly_fields = [
        'name',
        'phone',
        'contact_method',
        'company',
        'city',
        'comment',
        'file_link',
        'source_display',
        'page_link',
        'context',
        'created_at',
        'assigned_at',
        'consent_at',
        'consent_ip',
        'consent_version',
        'tg_status',
    ]

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.context:
            return fieldsets
        # Контекст есть только у квиза и товара — у остальных пустая строка
        return [
            (title, {**options, 'fields': without_context(options['fields'])})
            for title, options in fieldsets
        ]

    @admin.display(
        description='источник',
        ordering='source',
    )
    def source_display(self, obj):
        return obj.source_label

    @admin.display(description='страница')
    def page_link(self, obj):
        if not obj.page_url:
            return obj.page or '—'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            obj.page_url,
            obj.page_url,
        )

    @admin.display(description='статус')
    def tg_status(self, obj):
        if obj.tg_message_id is None:
            return TG_NOT_SENT
        if obj.file and not obj.tg_file_sent:
            return TG_FILE_PENDING
        return TG_SENT

    @admin.display(
        description='в Telegram',
        boolean=True,
    )
    def notified(self, obj):
        return obj.tg_message_id is not None

    @admin.display(description='файл')
    def file_link(self, obj):
        if not obj.file:
            return '—'
        url = reverse('admin:leads_lead_file', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.file_name)

    def get_urls(self):
        return [
            path(
                '<int:pk>/file/',
                self.admin_site.admin_view(self.download),
                name='leads_lead_file',
            ),
            *super().get_urls(),
        ]

    def download(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        if not self.has_view_permission(request, lead):
            raise PermissionDenied
        if not lead.file:
            raise Http404
        return FileResponse(
            lead.file.open('rb'),
            as_attachment=True,
            filename=lead.file_name or None,
        )

    def save_model(self, request, obj, form, change):
        if 'assignee_name' in form.changed_data:
            obj.assignee_tg_id = None
            obj.assigned_at = timezone.now() if obj.assignee_name else None
        super().save_model(request, obj, form, change)
        if 'assignee_name' in form.changed_data and obj.tg_message_id:
            transaction.on_commit(lambda: sync_lead_message.delay(obj.pk))

    @admin.action(description='Отправить в Telegram ещё раз')
    def resend(self, request, queryset):
        pending = [
            lead.pk
            for lead in queryset
            if not lead.tg_message_id or (lead.file and not lead.tg_file_sent)
        ]
        for lead_id in pending:
            transaction.on_commit(
                lambda lead_id=lead_id: notify_lead.delay(lead_id)
            )
        self.message_user(
            request,
            f'Поставлено в отправку: {len(pending)}',
            messages.SUCCESS,
        )
