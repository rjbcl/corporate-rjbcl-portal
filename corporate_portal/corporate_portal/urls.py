from django.contrib import admin #type: ignore
from django.urls import path, include #type: ignore
from main_system.admin import refresh_groups_cache_view

urlpatterns = [
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),
    path('admin/', admin.site.urls),
    path('', include('main_system.urls')),
    path('api/corporate/', include('api_corporate.urls')),
]
