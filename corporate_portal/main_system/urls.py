from django.urls import path #type: ignore
from . import views
from .admin import refresh_groups_cache_view

urlpatterns = [
    path('', views.user_login, name='login'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('individual/dashboard/', views.individual_dashboard, name='individual_dashboard'),
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),
]