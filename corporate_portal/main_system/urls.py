from django.urls import path #type: ignore
from . import views
from .admin import refresh_groups_cache_view

urlpatterns = [
    # Authentication
    path('', views.user_login, name='login'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Main dashboard (redirect based on user type)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Company routes
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('company/policies/', views.company_policies, name='company_policies'),
    
    # Company Reports
    path('company/reports/maturity/', views.maturity_report, name='maturity_report'),
    path('company/reports/premium/', views.premium_report, name='premium_report'),
    path('company/reports/summary/', views.policy_summary, name='policy_summary'),
    
    # Individual routes
    path('individual/dashboard/', views.individual_dashboard, name='individual_dashboard'),
    
    # Admin routes
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),
]