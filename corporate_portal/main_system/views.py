# views.py
from django.shortcuts import render, redirect #type: ignore
from django.contrib.auth import authenticate, login, logout #type: ignore
from django.contrib.auth.decorators import login_required #type: ignore
from django.contrib import messages #type: ignore
from main_system.models import Group
from .decorators import company_required, individual_required

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
                if not user.company_profile.isactive:
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
    company = request.user.company_profile
    
    # Get total groups count
    total_groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).count()
    
    context = {
        'company': company,
        'total_groups': total_groups,
    }
    # return render(request, 'Dashboard/Company/company_dashboard.html', context)
    return render(request, 'Dashboard/Company/dashboard.html', context)


@login_required
def company_policies(request):
    """Policies page for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_profile
    
    context = {
        'company': company,
    }
    return render(request, 'Dashboard/Company/policies.html', context)


# ================================
# COMPANY REPORTS VIEWS
# ================================

@login_required
def maturity_report(request):
    """Maturity forecasting report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_profile
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/maturity_report.html', context)


@login_required
def premium_report(request):
    """Premium report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_profile
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/premium_report.html', context)


@login_required
def policy_summary(request):
    """Policy summary report for company users"""
    if request.user.get_user_type() != 'company':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    company = request.user.company_profile
    
    # Get groups for dropdown
    groups = Group.objects.filter(
        company_id=company,
        isdeleted=False
    ).values('group_id', 'group_name')
    
    context = {
        'company': company,
        'groups': groups,
    }
    return render(request, 'Dashboard/Company/reports/policy_summary.html', context)



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


def user_logout(request):
    """Logout view for all users"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')