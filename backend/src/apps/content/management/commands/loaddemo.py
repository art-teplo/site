import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import (
    Faq,
    Post,
    Project,
    ProjectPhoto,
    ShowroomPhoto,
    SiteSettings,
)

DEMO = Path(__file__).resolve().parents[2] / 'demo' / 'demo.json'
# web/public/images, смонтированная в dev-compose только для чтения
IMAGES = Path('/demo-images')


class Command(BaseCommand):
    help = (
        'Заливает в базу демо-контент с фронта (web/src/data) и его фото. '
        'Повторный запуск обновляет записи, фото не дублирует.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--images',
            type=Path,
            default=IMAGES,
            help='папка web/public/images',
        )

    def handle(self, *args, **options):  # noqa: ARG002
        self.images = options['images']
        if not self.images.is_dir():
            msg = f'Нет папки с фото: {self.images}'
            raise CommandError(msg)
        demo = json.loads(DEMO.read_text())
        with transaction.atomic():
            self.load_site(demo['site'])
            self.load_faq(demo['faq'])
            self.load_projects(demo['projects'])
            self.load_posts(demo['posts'])
            self.load_showroom(demo['showroom'])
        self.stdout.write(self.style.SUCCESS('Демо-контент загружен'))

    def attach(self, obj, image):
        """Фото — только если его ещё нет: повторный запуск не плодит файлы."""
        obj.image_alt = image['alt']
        if obj.image:
            return
        path = self.images / image['src'].removeprefix('/images/')
        with path.open('rb') as file:
            obj.image.save(path.name, File(file), save=False)

    def load_site(self, data):
        hours = data.pop('hours')
        site = SiteSettings.get_solo()
        for field, value in data.items():
            setattr(site, field, value)
        site.save()
        site.hours.all().delete()
        for position, row in enumerate(hours):
            site.hours.create(position=position, **row)

    def load_faq(self, items):
        for position, item in enumerate(items):
            Faq.objects.update_or_create(
                question=item['question'],
                defaults={**item, 'position': position},
            )

    def load_projects(self, items):
        for position, item in enumerate(items):
            image = item.pop('image')
            photos = item.pop('photos')
            project = Project.objects.filter(slug=item['slug']).first()
            project = project or Project(slug=item['slug'])
            for field, value in item.items():
                setattr(project, field, value)
            project.position = position
            self.attach(project, image)
            project.save()
            for photo_position, photo_image in enumerate(photos):
                photo = project.photos.filter(
                    image_alt=photo_image['alt'],
                ).first()
                photo = photo or ProjectPhoto(project=project)
                photo.position = photo_position
                self.attach(photo, photo_image)
                photo.save()

    def load_posts(self, items):
        for item in items:
            image = item.pop('image')
            post = Post.objects.filter(slug=item['slug']).first()
            post = post or Post(slug=item['slug'])
            for field, value in item.items():
                setattr(post, field, value)
            self.attach(post, image)
            post.save()

    def load_showroom(self, items):
        for position, image in enumerate(items):
            photo = ShowroomPhoto.objects.filter(
                image_alt=image['alt'],
            ).first()
            photo = photo or ShowroomPhoto()
            photo.position = position
            self.attach(photo, image)
            photo.save()
