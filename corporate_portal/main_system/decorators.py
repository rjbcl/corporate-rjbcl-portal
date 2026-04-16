from django.shortcuts import redirect #type: ignore
from django.contrib import messages #type: ignore
from functools import wraps


def company_required(view_func):
    """Decorator to restrict access to company users only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.get_user_type() != 'company':
            messages.error(request, 'Access denied. Company account required.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def individual_required(view_func):
    """Decorator to restrict access to individual users only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.get_user_type() != 'individual':
            messages.error(request, 'Access denied. Individual account required.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper