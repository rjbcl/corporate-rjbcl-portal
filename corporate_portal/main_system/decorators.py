from django.shortcuts import redirect  # type: ignore
from django.contrib import messages  # type: ignore
from functools import wraps


def company_required(view_func):
    """Restricts access to company users or staff/admin acting on a company."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        user_type = request.user.get_user_type()
        
        # Staff and Admin bypass if they have a selected company in session
        if user_type in ('staff', 'admin'):
            if not request.session.get('selected_company_id'):
                messages.info(request, 'Please select a company to access the dashboard.')
                return redirect('select_company')
            return view_func(request, *args, **kwargs)
            
        if user_type != 'company':
            messages.error(request, 'Access denied. Company account required.')
            return redirect('dashboard')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def primary_company_required(view_func):
    """
    Restricts access to the primary company account user, or staff/admin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        user_type = request.user.get_user_type()

        # Staff and Admin bypass primary checks if they have a selected company
        if user_type in ('staff', 'admin'):
            if not request.session.get('selected_company_id'):
                messages.info(request, 'Please select a company to access the dashboard.')
                return redirect('select_company')
            return view_func(request, *args, **kwargs)

        if user_type != 'company':
            messages.error(request, 'Access denied. Company account required.')
            return redirect('dashboard')

        try:
            profile = request.user.company_profile
        except Exception:
            messages.error(request, 'Access denied. No company profile found.')
            return redirect('dashboard')

        if not profile.is_approved:
            messages.error(request, 'Your account is pending approval.')
            return redirect('dashboard')

        if not profile.is_primary:
            messages.error(request, 'Access denied. Primary account required.')
            return redirect('company_dashboard')

        return view_func(request, *args, **kwargs)
    return wrapper