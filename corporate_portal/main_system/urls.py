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

    #Change Password
    path('change_password/', views.change_password, name='change_password'),
    
    # Company Reports
    path('company/reports/maturity/', views.maturity_forecasting_report, name='maturity_forecasting_report'),
    path('company/reports/loan/', views.loan_repayment_report, name='loan_repayment_report'),
    path('company/reports/transfer/', views.transfer_report, name='transfer_report'),
    path('company/reports/claims/', views.claim_report, name='claim_report'), 
    path('company/reports/summary/', views.policy_summary, name='policy_summary'),
    path('company/reports/surrender-calculator/', views.surrender_calculator, name='surrender_calculator'),
    path('company/reports/business-detail/', views.business_detail_report, name='business_detail_report'),
    
    # Admin routes
    path('admin/refresh-groups-cache/', refresh_groups_cache_view, name='refresh_groups_cache'),

    # 2FA and OTP verification routes
    path('verify-2fa/', views.verify_2fa, name='verify_2fa'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),


    # Primary company user routes
    path('company/info/', views.company_info, name='company_info'),
    path('company/accounts/', views.manage_accounts, name='manage_accounts'),
    path('company/accounts/<int:account_id>/reset-password/', views.reset_account_password, name='reset_account_password'),

]

# 