import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog import pricing
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    LeadTime,
    Series,
    SeriesImage,
    Showcase,
    Variant,
)
from apps.content.models import (
    Faq,
    Post,
    Project,
    ProjectPhoto,
    Promo,
    ShowroomPhoto,
    SiteSettings,
)

APPS = Path(__file__).resolve().parents[3]
DEMO = APPS / 'content' / 'demo' / 'demo.json'
CATALOG_DEMO = APPS / 'catalog' / 'demo' / 'demo.json'
# web/public/images, смонтированная в dev-compose только для чтения
IMAGES = Path('/demo-images')


class Command(BaseCommand):
    help = (
        'Заливает в базу демо-контент и каталог (бренды, категории, сроки) '
        'с фронта (web/src/data) и их фото. '
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
        catalog = json.loads(CATALOG_DEMO.read_text())
        with transaction.atomic():
            self.load_site(demo['site'])
            self.load_faq(demo['faq'])
            self.load_projects(demo['projects'])
            self.load_posts(demo['posts'])
            self.load_promos(demo['promos'])
            self.load_showroom(demo['showroom'])
            self.load_categories(catalog['categories'])
            self.load_brands(catalog['brands'])
            self.load_lead_times(catalog['lead_times'])
            self.load_series(catalog['series'])
        self.stdout.write(self.style.SUCCESS('Демо-контент загружен'))

    def attach(self, obj, image):
        """Фото — только если его ещё нет: повторный запуск не плодит файлы."""
        obj.image_alt = image['alt']
        if obj.image:
            return
        self.save_file(obj.image, image['src'])

    def save_file(self, field, src):
        path = self.images / src.removeprefix('/images/')
        with path.open('rb') as file:
            field.save(path.name, File(file), save=False)

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

    def load_promos(self, items):
        for position, item in enumerate(items):
            image = item.pop('image')
            promo = Promo.objects.filter(title=item['title']).first()
            promo = promo or Promo()
            for field, value in item.items():
                setattr(promo, field, value)
            promo.position = position
            self.attach(promo, image)
            promo.save()

    def load_showroom(self, items):
        for position, image in enumerate(items):
            photo = ShowroomPhoto.objects.filter(
                image_alt=image['alt'],
            ).first()
            photo = photo or ShowroomPhoto()
            photo.position = position
            self.attach(photo, image)
            photo.save()

    def load_categories(self, items):
        for position, item in enumerate(items):
            image = item.pop('image')
            category = Category.objects.filter(slug=item['slug']).first()
            category = category or Category(slug=item['slug'])
            for field, value in item.items():
                setattr(category, field, value)
            category.position = position
            self.attach(category, image)
            category.save()

    def load_brands(self, items):
        for position, item in enumerate(items):
            logo = item.pop('logo')
            brand = Brand.objects.filter(slug=item['slug']).first()
            brand = brand or Brand(slug=item['slug'])
            for field, value in item.items():
                setattr(brand, field, value)
            brand.position = position
            if logo and not brand.logo:
                self.save_file(brand.logo, logo)
            brand.save()

    def load_lead_times(self, items):
        brands = {brand.slug: brand for brand in Brand.objects.all()}
        for position, item in enumerate(items):
            LeadTime.objects.update_or_create(
                series=item['series'],
                defaults={
                    'brand': brands[item['brand']],
                    'days': item['days'],
                    'position': position,
                },
            )

    def load_series(self, items):
        """Демо-серии: по slug, варианты — по (бренд, артикул), фото — по
        описанию. На базе с полным импортом прайса серии и варианты с теми
        же slug и артикулами обновляются, дублей нет."""
        variants = []
        for position, item in enumerate(items):
            series = Series.objects.filter(slug=item['slug']).first()
            series = series or Series(slug=item['slug'])
            series.brand = Brand.objects.get(slug=item['brand'])
            series.category = Category.objects.get(slug=item['category'])
            for field in (
                'name',
                'description',
                'material',
                'heating',
                'pressure_bar',
            ):
                setattr(series, field, item[field])
            series.position = position
            series.is_published = True
            series.save()
            self.load_color_groups(series, item['color_groups'])
            variants += self.load_variants(series, item['variants'])
            self.load_series_images(series, item['images'])
            self.load_showcases(series, item['showcases'])
        pricing.recalculate(Variant.objects.filter(pk__in=variants))

    def load_color_groups(self, series, groups):
        for position, group in enumerate(groups):
            colors = [
                Color.objects.update_or_create(
                    code=color['code'],
                    defaults=color,
                )[0]
                for color in group['colors']
            ]
            obj, _ = ColorGroup.objects.update_or_create(
                series=series,
                name=group['name'],
                defaults={
                    'percent': group['percent'],
                    'is_base': group['is_base'],
                    'any_ral': group['any_ral'],
                    'position': position,
                },
            )
            obj.colors.set(colors)

    def load_variants(self, series, rows):
        ids = []
        for row in rows:
            variant, _ = Variant.objects.update_or_create(
                brand=series.brand,
                article=row['article'],
                defaults={**row, 'series': series},
            )
            ids.append(variant.pk)
        return ids

    def load_series_images(self, series, images):
        for position, image in enumerate(images):
            obj = series.images.filter(image_alt=image['alt']).first()
            obj = obj or SeriesImage(series=series)
            obj.position = position
            self.attach(obj, image)
            obj.save()

    def load_showcases(self, series, items):
        for position, item in enumerate(items):
            showcase = series.showcases.filter(label=item['label']).first()
            showcase = showcase or Showcase(series=series)
            showcase.label = item['label']
            showcase.variant = series.variants.get(article=item['variant'])
            showcase.position = position
            showcase.save()
