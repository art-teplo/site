from django.urls import path

from . import views

urlpatterns = [
    path(
        'categories/',
        views.CategoryListView.as_view(),
        name='category-list',
    ),
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path(
        'lead-times/',
        views.LeadTimeListView.as_view(),
        name='lead-time-list',
    ),
]
