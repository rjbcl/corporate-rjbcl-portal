from django.contrib import admin #type: ignore
from django.urls import path, include #type: ignore
from main_system.admin import refresh_groups_cache_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),
    path('admin/', admin.site.urls),
    path('', include('main_system.urls')),
    path('api/corporate/', include('api_corporate.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)