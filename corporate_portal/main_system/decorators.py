from django.shortcuts import redirect  # type: ignore
from django.contrib import messages  # type: ignore
from functools import wraps


def company_required(view_func):
    """Restricts access to company users only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.get_user_type() != 'company':
            messages.error(request, 'Access denied. Company account required.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def primary_company_required(view_func):
    """
    Restricts access to the primary company account user only.
    Checks:
      1. User is authenticated
      2. User type is 'company'
      3. Account is approved (is_approved=True)
      4. Account is the primary contact (is_primary=True)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.get_user_type() != 'company':
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