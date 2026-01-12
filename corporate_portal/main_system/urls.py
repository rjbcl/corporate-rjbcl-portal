from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('individual/dashboard/', views.individual_dashboard, name='individual_dashboard'),
]