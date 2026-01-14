from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_system.urls')),
    path('api/corporate/', include('api_corporate.urls')),
]
