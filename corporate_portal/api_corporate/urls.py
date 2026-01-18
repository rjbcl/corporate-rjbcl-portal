from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import GroupInformationViewSet

router = DefaultRouter()
router.register(r'groups', GroupInformationViewSet, basename='group')

urlpatterns = [
    path('', include(router.urls)),
]