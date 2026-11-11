from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()


# BUILD_MODE=1 — сборка образа (collectstatic): секреты и БД ещё не нужны
BUILD_MODE = env.bool('BUILD_MODE', default=False)

env.prefix = 'BACKEND__'

DEBUG = env.bool('DEBUG', default=False)

SECRET_KEY = env.str(
    'SECRET_KEY',
    default='dummy-secret-key' if BUILD_MODE else env.NOTSET,
)

VERSION = env.str('VERSION', default='0.0.0')

ALLOWED_HOSTS = [
    *env.list('ALLOWED_HOSTS', default=[]),  # pyright: ignore[reportArgumentType]
    'localhost',
    '127.0.0.1',
    'backend',
]

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])  # pyright: ignore[reportArgumentType]

# Пока фронт на Vercel, браузер ходит в API с другого домена
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])  # pyright: ignore[reportArgumentType]

# Нестандартный путь админки, без слешей; на nginx тот же путь
ADMIN_PATH = env.str('ADMIN_PATH', default='admin').strip('/')

SERVER_HOST = env.str('HOST', default='0.0.0.0')

SERVER_PORT = env.int('PORT', default=8000)

SERVER_WORKERS = env.int('WORKERS', default=2)

DEFAULT_DATABASE = env.db_url(
    'DATABASE_URL',
    default='sqlite:///:memory:' if BUILD_MODE else env.NOTSET,  # pyright: ignore[reportArgumentType]
)

DEFAULT_CACHE = env.cache_url(
    'CACHE_URL',
    default='dummycache://' if BUILD_MODE else env.NOTSET,  # pyright: ignore[reportArgumentType]
)

CELERY_BROKER_URL = env.str(
    'CELERY_BROKER_URL',
    default='memory://' if BUILD_MODE else env.NOTSET,
)

TIME_ZONE = env.str('TIME_ZONE', default='Europe/Minsk')

# Адрес сайта со схемой, без слеша в конце — для ссылок на админку из Telegram
PUBLIC_URL = env.str('PUBLIC_URL', default='').rstrip('/')

# Адрес фронта — для ссылок на страницы сайта (товар) в Telegram и админке.
# Пока фронт на Vercel, он отличается от PUBLIC_URL; пусто — как PUBLIC_URL
SITE_URL = env.str('SITE_URL', default='').rstrip('/') or PUBLIC_URL

# Бот пишет заявки в одну закрытую группу; пусто — уведомления выключены
TELEGRAM__BOT_TOKEN = env.str('TELEGRAM__BOT_TOKEN', default='')
TELEGRAM__CHAT_ID = env.int('TELEGRAM__CHAT_ID', default=None)  # pyright: ignore[reportArgumentType]

# Срок хранения заявок и файлов (Закон РБ № 99-З: не дольше, чем нужно)
LEADS__RETENTION_DAYS = env.int('LEADS__RETENTION_DAYS', default=365)

# Куда стучаться после правки контента, чтобы фронт обновил страницы
# (POST /api/revalidate на Next). Пусто — не стучимся: фронт обновится
# сам по истечении кэша
FRONTEND__REVALIDATE_URL = env.str('FRONTEND__REVALIDATE_URL', default='')
FRONTEND__REVALIDATE_SECRET = env.str(
    'FRONTEND__REVALIDATE_SECRET', default=''
)

S3__ENABLED = env.bool('S3__ENABLED', default=False)
s3_options = (
    {
        'region_name': env.str('S3__REGION_NAME', default=None),  # pyright: ignore[reportArgumentType]
        'endpoint_url': env.str('S3__ENDPOINT_URL'),
        'access_key': env.str('S3__ACCESS_KEY_ID'),
        'secret_key': env.str('S3__SECRET_ACCESS_KEY'),
        'bucket_name': env.str('S3__BUCKET_NAME'),
        'custom_domain': env.str('S3__CUSTOM_DOMAIN', default=None),  # pyright: ignore[reportArgumentType]
        'location': env.str('S3__LOCATION', default=''),
        'default_acl': None,
        'querystring_auth': False,
        'file_overwrite': False,
    }
    if S3__ENABLED
    else {}
)

# --- django ---

INSTALLED_APPS = [
    # admin
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    # base
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    # modules
    'corsheaders',
    'rest_framework',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'storages',
    'phonenumber_field',
    'solo',
    'axes',
    # apps
    'apps.core',
    'apps.leads',
    'apps.content',
    'apps.catalog',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'settings.asgi:app'

DATABASES = {
    'default': DEFAULT_DATABASE,
}
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    # мб в будущем явно задать pool_size, max_overflow, timeout, recycle и пр.
    DATABASES['default']['CONN_MAX_AGE'] = 0
    DATABASES['default'].setdefault('OPTIONS', {})['pool'] = True

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'static'
STATIC_ROOT.mkdir(exist_ok=True)

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_ROOT.mkdir(exist_ok=True)

# Файлы заявок (планы, спецификации): вне MEDIA_ROOT, который ASGI отдаёт
# открыто, пока S3 выключен. Скачать — только из админки
PRIVATE_MEDIA_ROOT = BASE_DIR / 'private'
PRIVATE_MEDIA_ROOT.mkdir(exist_ok=True)

# Большие загрузки пишутся во временный файл; /tmp в образе может не быть
FILE_UPLOAD_TEMP_DIR = PRIVATE_MEDIA_ROOT / 'tmp'
FILE_UPLOAD_TEMP_DIR.mkdir(exist_ok=True)

CACHES = {
    'default': DEFAULT_CACHE,
}

STORAGES = {
    'default': (
        {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': s3_options,
        }
        if S3__ENABLED
        else {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        }
    ),
    'private': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {'location': PRIVATE_MEDIA_ROOT},
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
        ),
    },
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# --- логи: всё в stdout, собирает docker ---

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '{asctime} {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'plain',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

# --- axes: лимит попыток входа в админку ---


AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_DISABLE_ACCESS_LOG = True
AXES_CLIENT_IP_CALLABLE = 'apps.core.utils.client_ip'

# --- drf_spectacular ---

SPECTACULAR_SETTINGS = {
    'TITLE': 'АртТепло API',
    'VERSION': VERSION,
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'COMPONENT_SPLIT_REQUEST': True,
    'SERVE_PERMISSIONS': [
        'rest_framework.permissions.AllowAny'
        if DEBUG
        else 'rest_framework.permissions.IsAdminUser',
    ],
}

# --- rest_framework ---

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        *(['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 24,
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttling.ProxiedAnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'leads_burst': '3/min',
        'leads_day': '20/day',
    },
    # Перед бэком ровно один прокси (nginx): IP клиента — последний в X-Forwarded-For
    'NUM_PROXIES': 1,
}

# --- unfold ---

UNFOLD = {
    'SITE_TITLE': 'АртТепло',
    'SITE_HEADER': 'АртТепло',
    'ENVIRONMENT': 'settings.settings.environment_callback',
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': True,
        'navigation': [
            {
                'items': [
                    {
                        'title': 'Главная',
                        'icon': 'home',
                        'link': reverse_lazy('admin:index'),
                    },
                    {
                        'title': 'Заявки',
                        'icon': 'inbox',
                        'link': reverse_lazy('admin:leads_lead_changelist'),
                    },
                ],
            },
            {
                'title': 'Сайт',
                'items': [
                    {
                        'title': 'Настройки сайта',
                        'icon': 'settings',
                        'link': reverse_lazy(
                            'admin:content_sitesettings_change',
                        ),
                    },
                    {
                        'title': 'Вопрос-ответ',
                        'icon': 'help',
                        'link': reverse_lazy('admin:content_faq_changelist'),
                    },
                    {
                        'title': 'Проекты',
                        'icon': 'photo_library',
                        'link': reverse_lazy(
                            'admin:content_project_changelist',
                        ),
                    },
                    {
                        'title': 'Блог',
                        'icon': 'article',
                        'link': reverse_lazy('admin:content_post_changelist'),
                    },
                    {
                        'title': 'Акции',
                        'icon': 'sell',
                        'link': reverse_lazy('admin:content_promo_changelist'),
                    },
                    {
                        'title': 'Шоурум',
                        'icon': 'storefront',
                        'link': reverse_lazy(
                            'admin:content_showroomphoto_changelist',
                        ),
                    },
                ],
            },
            {
                'title': 'Каталог',
                'items': [
                    {
                        'title': 'Категории',
                        'icon': 'category',
                        'link': reverse_lazy(
                            'admin:catalog_category_changelist',
                        ),
                    },
                    {
                        'title': 'Бренды',
                        'icon': 'factory',
                        'link': reverse_lazy('admin:catalog_brand_changelist'),
                    },
                    {
                        'title': 'Сроки изготовления',
                        'icon': 'schedule',
                        'link': reverse_lazy(
                            'admin:catalog_leadtime_changelist',
                        ),
                    },
                    {
                        'title': 'Серии',
                        'icon': 'view_list',
                        'link': reverse_lazy(
                            'admin:catalog_series_changelist'
                        ),
                    },
                    {
                        'title': 'Варианты',
                        'icon': 'table_rows',
                        'link': reverse_lazy(
                            'admin:catalog_variant_changelist',
                        ),
                    },
                    {
                        'title': 'Цвета',
                        'icon': 'palette',
                        'link': reverse_lazy('admin:catalog_color_changelist'),
                    },
                    {
                        'title': 'Курсы валют',
                        'icon': 'currency_exchange',
                        'link': reverse_lazy(
                            'admin:catalog_currencyrate_changelist',
                        ),
                    },
                ],
            },
        ],
    },
}


def environment_callback(request):  # noqa: ARG001
    return ['Разработка', 'info'] if DEBUG else ['Прод', 'danger']


# --- celery ---

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_TASK_TIME_LIMIT = 600

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# DatabaseScheduler сам заносит эти задачи в БД при старте beat
CELERY_BEAT_SCHEDULE = {
    'purge-old-leads': {
        'task': 'apps.leads.tasks.purge_old_leads',
        'schedule': crontab(hour=3, minute=30),
    },
    'update-currency-rates': {
        'task': 'apps.catalog.tasks.update_rates',
        'schedule': crontab(hour=1, minute=10),
    },
}

# --- phonenumber_field ---

# Номер без кода страны считаем белорусским; хранится в E.164
PHONENUMBER_DEFAULT_REGION = 'BY'

# --- corsheaders ---

CORS_ALLOW_CREDENTIALS = False
CORS_URLS_REGEX = r'^/api/.*$'
