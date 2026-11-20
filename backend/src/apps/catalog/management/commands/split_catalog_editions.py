import json
from dataclasses import asdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.catalog_editions import (
    apply_catalog_editions,
    plan_catalog_editions,
)


class Command(BaseCommand):
    help = 'Проверить/перенести подтверждённые Guardo/Velar исполнения. По умолчанию без записи.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=Path, required=True)
        parser.add_argument('--series', action='append', required=True)
        parser.add_argument('--report', type=Path, required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        try:
            plan = plan_catalog_editions(
                source=options['source'], series_slugs=options['series']
            )
            options['report'].write_text(
                json.dumps(
                    asdict(plan), ensure_ascii=False, indent=2, default=str
                )
                + '\n'
            )
            result = (
                apply_catalog_editions(plan)
                if options['apply']
                else {
                    'dry_run': True,
                    'moves': len(plan.moves),
                    'conflicts': len(plan.conflicts),
                }
            )
            self.stdout.write(json.dumps(result, ensure_ascii=False))
        except (ValueError, OSError) as error:
            raise CommandError(str(error)) from error
