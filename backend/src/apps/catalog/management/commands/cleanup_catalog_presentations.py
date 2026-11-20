"""Report and back up before deleting proven redundant catalogue parents."""

import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from apps.catalog.catalog_cleanup import (
    apply_cleanup,
    build_cleanup_report,
    lock_cleanup_rows,
)
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


class Command(BaseCommand):
    help = 'Очистить доказанно лишних родителей и витрину Nova. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--report', type=Path, required=True)
        parser.add_argument('--series', action='append', dest='slugs')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        path = Path(options['report'])
        with muted_revalidation(), transaction.atomic():
            if options['apply']:
                lock_cleanup_rows(options['slugs'])
            try:
                report = build_cleanup_report(options['slugs'])
            except ValueError as error:
                raise CommandError(str(error)) from error
            report['database'] = {
                key: settings.DATABASES['default'].get(key)
                for key in ('ENGINE', 'HOST', 'PORT', 'NAME')
            }
            report['applied'] = options['apply']
            try:
                # Never replace an earlier backup, even for a repeated no-op.
                descriptor = os.open(
                    path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, 'w') as output:
                    json.dump(
                        report,
                        output,
                        cls=DjangoJSONEncoder,
                        ensure_ascii=False,
                        indent=2,
                    )
                    output.write('\n')
                    output.flush()
                    os.fsync(output.fileno())
            except OSError as error:
                message = f'Не записана новая копия: {path}'
                raise CommandError(message) from error
            if options['apply']:
                apply_cleanup(report)
                if report['changes']:
                    transaction.on_commit(
                        lambda: revalidate_frontend.delay(Tag.CATALOG)
                    )
        self.stdout.write(
            json.dumps(
                {
                    'eligible_parents': sum(
                        p['status'] == 'eligible' for p in report['parents']
                    ),
                    'retained_parents': sum(
                        p['status'] == 'retained' for p in report['parents']
                    ),
                    'changes': report['changes'],
                    'applied': options['apply'],
                    'report': str(path),
                },
                ensure_ascii=False,
            )
        )
