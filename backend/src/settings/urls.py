from django.conf import settings
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
    path('schema/', include(schema_urls)),
]

urlpatterns = [
    path(f'{settings.ADMIN_PATH}/', admin.site.urls),
    path('api/', include(api_urls)),
]
