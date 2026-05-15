# views.py
from django.shortcuts import render, redirect #type: ignore
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout #type: ignore
from django.contrib.auth.decorators import login_required #type: ignore
from django.contrib import messages #type: ignore
from main_system.models import Group
from .decorators import company_required
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash
from .forms import ChangePasswordForm
from main_system.models import AuditLog  # adjust import path if needed
from .utils import validate_password_strength
 
def user_login(request):
    """Single login view for all user types"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Please contact support.')
                return render(request, 'login.html')
            
            # Check if company account is inactive
            user_type = user.get_user_type()
            if user_type == 'company':
                if not user.company_id.isactive:
                    messages.error(request, 'Your company account is inactive. Please contact support.')
                    return render(request, 'login.html')
            
            # Check if individual's group is valid
            elif user_type == 'individual':
                individual = user.individual_profile
                group = individual.group_id
                
                if not group.isactive or group.isdeleted:
                    messages.error(request, 'Your group is inactive. Please contact your company administrator.')
                    return render(request, 'login.html')
                
                # Check if the company is inactive
                if not group.company_id.isactive:
                    messages.error(request, 'Your company account is inactive. Please contact support.')
                    return render(request, 'login.html')
            
            # Login successful
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')
 
 
@login_required
def dashboard(request):
    """Route users to appropriate dashboard based on their role"""
    user = request.user
    user_type = user.get_user_type()
    
    if user_type == 'staff':
        # Staff/admin goes to Django admin
        return redirect('/admin/')
    elif user_type == 'admin':
        # Staff/admin goes to Django admin
        return redirect('/admin/')
    elif user_type == 'company':
        # Company users go to company dashboard
        return redirect('company_dashboard')
    elif user_type == 'individual':
        # Individual users go to individual dashboard
        return redirect('individual_dashboard')
    else:
        messages.error(request, 'Account type not recognized.')
        logout(request)
        return redirect('login')
 
# ================================
# COMPANY VIEWS
# ================================
 
@login_required
@company_required
def company_dashboard(request):
    """Dashboard for company users"""
    company = request.user.company_id
    
    # Get total groups count
    total_groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).count()
    
    context = {
        'company': company,
        'total_groups': total_groups,
    }
    return render(request, 'Dashboard/Company/dashboard.html', context)
 
 
@login_required
def company_groups(request):
    """Policies page for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    context = {
        'company': company,
    }
    return render(request, 'Dashboard/Company/groups.html', context)
 
 
# ================================
# COMPANY REPORTS VIEWS
# ================================
@login_required
def maturity_forecasting_report(request):
    """Maturity forecasting report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/maturity_forecasting_report.html', context)
 
@login_required
def transfer_report(request):
    """Group transfer report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/Transfer_report.html', context)
 
@login_required
def claim_report(request):
    """
    Claim report for company users (Maturity, Surrender, Death claims).
    """
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/claim_report.html', context)
 
@login_required
def business_detail_report(request):
    """
    Business detail report for company users (New Business, Renewal Business).
    """
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
 
    company = request.user.company_id
 
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
 
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/Business_detail_report.html', context)
 
@login_required
def loan_repayment_report(request):
    """Loan repayment report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/group_loan_report.html', context)
 
 
@login_required
def policy_summary(request):
    """Policy summary report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
 
    company = request.user.company_id
    
    context = {
        'company': company,
    }
    return render(request, 'Dashboard/Company/policy_summary_report.html', context)
 
@login_required
def surrender_calculator(request):
    """Surrender calculator for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_id
    
    context = {
        'company': company,
    }
    return render(request, 'Dashboard/Company/surrender_calculator.html', context)
 
 
 
@login_required
def individual_dashboard(request):
    """Dashboard for individual users"""
    if request.user.get_user_type() != 'individual':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    individual = request.user.individual_profile
    context = {
        'user_name': individual.user_full_name or request.user.username,
        'individual': individual,
    }
    return render(request, 'individual_dashboard.html', context)
 
 
@login_required
@require_POST
def change_password(request):
    form = ChangePasswordForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    user = request.user

    if not user.check_password(form.cleaned_data['current_password']):
        return JsonResponse({
            'success': False,
            'errors': {'current_password': ['Incorrect current password.']}
        }, status=400)

    new_password = form.cleaned_data['new_password']
    strength_errors = validate_password_strength(new_password)
    if strength_errors:
        return JsonResponse({
            'success': False,
            'errors': {'new_password': [f"Password must contain: {', '.join(strength_errors)}."]}
        }, status=400)

    user.set_password(new_password)
    user.modified_by = user.username
    user.save()

    update_session_auth_hash(request, user)

    AuditLog.create_log(
        action='password_reset',
        target_username=user.username,
        target_type=user.get_user_type(),
        performed_by=user.username,
        details='User changed their own password.',
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return JsonResponse({'success': True, 'message': 'Password changed successfully.'})
 
def user_logout(request):
    """Logout view for all users"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')