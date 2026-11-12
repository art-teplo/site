from django.urls import path

from . import views

urlpatterns = [
    path(
        'categories/',
        views.CategoryListView.as_view(),
        name='category-list',
    ),
    path('search/', views.SearchView.as_view(), name='search'),
    path(
        'series/',
        views.SeriesListView.as_view(),
        name='series-list',
    ),
    path(
        'series/<slug:slug>/',
        views.SeriesDetailView.as_view(),
        name='series-detail',
    ),
    path(
        'series/<slug:slug>/variants/',
        views.SeriesVariantsView.as_view(),
        name='series-variants',
    ),
    path(
        'variants/<str:article>/',
        views.VariantDetailView.as_view(),
        name='variant-detail',
    ),
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path(
        'lead-times/',
        views.LeadTimeListView.as_view(),
        name='lead-time-list',
    ),
]
