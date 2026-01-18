from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import GroupEndowmentViewSet, GroupInformationViewSet

router = DefaultRouter()
router.register(r'groups', GroupInformationViewSet, basename='group')
router.register(r'endowments', GroupEndowmentViewSet, basename='endowment')

urlpatterns = [
    path('', include(router.urls)),
]