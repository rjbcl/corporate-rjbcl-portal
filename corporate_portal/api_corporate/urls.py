from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GroupInformationViewSet

router = DefaultRouter()
router.register(r'groups', GroupInformationViewSet, basename='group')

urlpatterns = [
    path('', include(router.urls)),
]