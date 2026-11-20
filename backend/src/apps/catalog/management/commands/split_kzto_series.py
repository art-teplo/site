import json
from dataclasses import asdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.kzto import FEED_URL, FeedError
from apps.catalog.kzto_split import apply_kzto_split, plan_kzto_split


class Command(BaseCommand):
    help = 'Разделить объединённые серии КЗТО с сохранением вариантов. По умолчанию — только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--feed', default=FEED_URL)
        parser.add_argument('--series', action='append')
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--report')

    def handle(self, *args, **options):  # noqa: ARG002
        try:
            plan = plan_kzto_split(
                feed_source=options['feed'], legacy_slugs=options['series']
            )
            if options['report']:
                Path(options['report']).write_text(
                    json.dumps(
                        asdict(plan), ensure_ascii=False, indent=2, default=str
                    )
                )
            result = (
                apply_kzto_split(plan)
                if options['apply'] and not options['dry_run']
                else {
                    'dry_run': True,
                    'variants': len(plan.moves),
                    'parents': len(plan.parents),
                }
            )
            self.stdout.write(json.dumps(result, ensure_ascii=False))
        except FeedError as error:
            raise CommandError(str(error)) from error
