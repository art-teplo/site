from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

schema_urls = [
    path('', SpectacularAPIView.as_view(), name='schema'),
    path(
        'swagger/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='api-docs',
    ),
]

api_urls = [
    path('', include('apps.core.urls')),
    path('', include('apps.leads.urls')),
    path('', include('apps.content.urls')),
    path('schema/', include(schema_urls)),
]

urlpatterns = [
    path(f'{settings.ADMIN_PATH}/', admin.site.urls),
    path('api/', include(api_urls)),
]

# runserver в разработке не отдаёт /media/ сам (в образе это делает ASGI).
# static() работает только при DEBUG
if not settings.S3__ENABLED:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
