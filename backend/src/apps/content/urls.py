from django.urls import path

from . import views

urlpatterns = [
    path('site/', views.SiteView.as_view(), name='site'),
    path('faq/', views.FaqListView.as_view(), name='faq-list'),
    path('projects/', views.ProjectListView.as_view(), name='project-list'),
    path('posts/', views.PostListView.as_view(), name='post-list'),
    path(
        'posts/<slug:slug>/',
        views.PostDetailView.as_view(),
        name='post-detail',
    ),
    path('promos/', views.PromoListView.as_view(), name='promo-list'),
    path('showroom/', views.ShowroomView.as_view(), name='showroom'),
]
