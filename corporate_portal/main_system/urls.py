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
    path('company/groups/', views.company_groups, name='company_groups'),
    
    # Company Reports
    path('company/reports/maturity/', views.maturity_forecasting_report, name='maturity_forecasting_report'),
    path('company/reports/loan/', views.loan_repayment_report, name='loan_repayment_report'),
    path('company/reports/transfer/', views.transfer_report, name='transfer_report'),
    path('company/reports/claims/', views.claim_report, name='claim_report'), 
    path('company/reports/premium/', views.premium_report, name='premium_report'),
    path('company/reports/summary/', views.policy_summary, name='policy_summary'),
    path('company/reports/surrender-calculator/', views.surrender_calculator, name='surrender_calculator'),
    path('company/reports/business-detail/', views.business_detail_report, name='business_detail_report'),
    # Individual routes
    path('individual/dashboard/', views.individual_dashboard, name='individual_dashboard'),
    
    # Admin routes
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),
]

# 