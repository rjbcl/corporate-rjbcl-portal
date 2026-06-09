import base64
import io
import qrcode
 
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
 
from main_system.models import Group, AuditLog, UserVerification, CompanyAccount, CompanyDocument
from .decorators import company_required, primary_company_required
from .forms import ChangePasswordForm
from .utils import validate_password_strength
from .services import (
    generate_otp,
    verify_otp as verify_otp_service,
    get_totp_qr_uri,
    verify_totp,
    setup_totp,
    CompanyAccountService,
    CompanyService,
)
 
 
# ============================================================
# HELPERS
# ============================================================
 
def _get_pending_user(request):
    """
    Retrieves the pending 2FA user from session.
    Returns (user, error_message).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
 
    username = request.session.get('pending_2fa_user')
    expiry = request.session.get('pending_2fa_expiry')
 
    if not username or not expiry:
        return None, "Session expired. Please login again."
 
    if timezone.now().timestamp() > expiry:
        request.session.pop('pending_2fa_user', None)
        request.session.pop('pending_2fa_expiry', None)
        return None, "Session expired. Please login again."
 
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return None, "User not found. Please login again."
 
    return user, None
 
 
def _set_pending_user(request, user):
    """Stores pending 2FA user in session with expiry."""
    expiry_seconds = getattr(settings, 'TWO_FA_SESSION_EXPIRY', 300)
    request.session['pending_2fa_user'] = user.username
    request.session['pending_2fa_expiry'] = timezone.now().timestamp() + expiry_seconds
 
 
def _generate_qr_base64(uri: str) -> str:
    """Generates a QR code from URI and returns base64 encoded PNG."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
 
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
 
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
 
 
# ============================================================
# AUTH VIEWS
# ============================================================
 
def user_login(request):
    """Single login view for all user types: admin, staff, company."""
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
 
            user_type = user.get_user_type()
 
            if user_type == 'company':
                # Check approval first — before any other company check
                if not user.company_profile.is_approved:
                    messages.error(
                        request,
                        'Your account is pending approval. '
                        'Please contact your administrator.'
                    )
                    AuditLog.create_log(
                        action='login_failed',
                        target_username=user.username,
                        target_type='company',
                        performed_by=user.username,
                        details='Login blocked — account pending approval.',
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                    return render(request, 'login.html')
 
                # Check company is active
                if not user.company_profile.company.isactive:
                    messages.error(request, 'Your company account is inactive. Please contact support.')
                    return render(request, 'login.html')
 
                # Verify 2FA record exists
                try:
                    verification = user.user_verification
                except UserVerification.DoesNotExist:
                    messages.error(request, 'No verification setup found. Please contact your administrator.')
                    return render(request, 'login.html')
 
                _set_pending_user(request, user)
 
                AuditLog.create_log(
                    action='login',
                    target_username=user.username,
                    target_type='company',
                    performed_by=user.username,
                    details='Credentials verified. Redirected to 2FA.',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
 
                return redirect('verify_2fa')
 
            # Admin and staff bypass 2FA
            login(request, user)
 
            AuditLog.create_log(
                action='login',
                target_username=user.username,
                target_type=user_type or 'unknown',
                performed_by=user.username,
                details='Login successful.',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
 
            return redirect('dashboard')
 
        else:
            AuditLog.create_log(
                action='login_failed',
                target_username=username or 'unknown',
                target_type='unknown',
                performed_by=username or 'unknown',
                details='Invalid credentials.',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.error(request, 'Invalid username or password.')
 
    return render(request, 'login.html')
 
 
def verify_2fa(request):
    """
    Handles TOTP verification.
    - is_totp_enabled=False: shows QR code for first-time setup.
    - is_totp_enabled=True:  shows TOTP input for normal verification.
    """
    user, error = _get_pending_user(request)
    if not user:
        messages.error(request, error)
        return redirect('login')
 
    verification = user.user_verification
    has_mobile = bool(user.company_profile.mobile)
 
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
 
        if not verification.is_totp_enabled:
            success, message = setup_totp(user, code)
        else:
            success, message = verify_totp(user, code)
 
        if success:
            request.session.pop('pending_2fa_user', None)
            request.session.pop('pending_2fa_expiry', None)
 
            login(request, user)
 
            action_detail = (
                'First-time TOTP setup and login.'
                if not verification.is_totp_enabled
                else 'TOTP verified. Login successful.'
            )
            AuditLog.create_log(
                action='login',
                target_username=user.username,
                target_type='company',
                performed_by=user.username,
                details=action_detail,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
 
            return redirect('dashboard')
 
        else:
            verification.refresh_from_db()
            if verification.timeout_until and timezone.now() < verification.timeout_until:
                AuditLog.create_log(
                    action='login_failed',
                    target_username=user.username,
                    target_type='company',
                    performed_by=user.username,
                    details=f'Locked out until {verification.timeout_until}.',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            else:
                AuditLog.create_log(
                    action='login_failed',
                    target_username=user.username,
                    target_type='company',
                    performed_by=user.username,
                    details='Invalid TOTP code.',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            messages.error(request, message)
 
    context = {'has_mobile': has_mobile}
 
    if not verification.is_totp_enabled:
        uri = get_totp_qr_uri(user)
        context['qr_base64'] = _generate_qr_base64(uri)
        context['totp_secret'] = verification.totp_secret
        context['is_setup'] = True
    else:
        context['is_setup'] = False
 
    return render(request, 'verify_2fa.html', context)
 
 
def verify_otp(request):
    """
    SMS OTP fallback view.
    GET:  shows Send OTP button.
    POST action=send:   generates and sends OTP.
    POST action=verify: verifies submitted OTP.
    """
    user, error = _get_pending_user(request)
    if not user:
        messages.error(request, error)
        return redirect('login')
 
    try:
        mobile = user.company_profile.mobile
    except Exception:
        mobile = None
 
    if not mobile:
        messages.error(request, 'No mobile number registered. Please contact your administrator.')
        return redirect('verify_2fa')
 
    otp_sent = request.session.get('otp_sent', False)
 
    if request.method == 'POST':
        action = request.POST.get('action')
 
        if action == 'send':
            generate_otp(user)
            request.session['otp_sent'] = True
            # TODO: send via SparrowSMS here
            messages.success(request, 'OTP sent to your registered mobile number.')
            return render(request, 'verify_otp.html', {'otp_sent': True})
 
        elif action == 'verify':
            code = request.POST.get('code', '').strip()
            success, message = verify_otp_service(user, code)
 
            if success:
                request.session.pop('pending_2fa_user', None)
                request.session.pop('pending_2fa_expiry', None)
                request.session.pop('otp_sent', None)
 
                login(request, user)
 
                AuditLog.create_log(
                    action='login',
                    target_username=user.username,
                    target_type='company',
                    performed_by=user.username,
                    details='SMS OTP verified. Login successful.',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
 
                return redirect('dashboard')
 
            else:
                verification = user.user_verification
                verification.refresh_from_db()
                if verification.timeout_until and timezone.now() < verification.timeout_until:
                    AuditLog.create_log(
                        action='login_failed',
                        target_username=user.username,
                        target_type='company',
                        performed_by=user.username,
                        details=f'Locked out until {verification.timeout_until}.',
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                else:
                    AuditLog.create_log(
                        action='login_failed',
                        target_username=user.username,
                        target_type='company',
                        performed_by=user.username,
                        details='Invalid OTP code.',
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                messages.error(request, message)
                return render(request, 'verify_otp.html', {'otp_sent': True})
 
    context = {
        'otp_sent': otp_sent,
        'otp_expire_seconds': getattr(settings, 'OTP_EXPIRE_SECONDS', 120),
    }
    return render(request, 'verify_otp.html', context)
 
 
# ============================================================
# DASHBOARD
# ============================================================
 
@login_required
def dashboard(request):
    """Routes users to the appropriate dashboard based on their role."""
    user = request.user
    user_type = user.get_user_type()
 
    if user_type in ('staff', 'admin'):
        return redirect('/admin/')
    elif user_type == 'company':
        return redirect('company_dashboard')
    else:
        messages.error(request, 'Account type not recognized.')
        logout(request)
        return redirect('login')
 
 
# ============================================================
# COMPANY VIEWS
# ============================================================
 
@login_required
@company_required
def company_dashboard(request):
    company = request.user.company_profile.company
    total_groups = Group.objects.filter(
        company=company,
        isdeleted=False,
    ).count()
    context = {
        'company': company,
        'total_groups': total_groups,
        'is_primary': request.user.company_profile.is_primary,
    }
    return render(request, 'Dashboard/Company/dashboard.html', context)
 
 
@login_required
@company_required
def company_groups(request):
    company = request.user.company_profile.company
    context = {'company': company}
    return render(request, 'Dashboard/Company/groups.html', context)
 
 
# ============================================================
# COMPANY REPORT VIEWS
# ============================================================
 
@login_required
@company_required
def maturity_forecasting_report(request):
    company = request.user.company_profile.company
    groups = Group.objects.filter(company=company, isdeleted=False).values('group_id', 'group_name')
    context = {'company': company, 'groups': groups}
    return render(request, 'Dashboard/Company/reports/maturity_forecasting_report.html', context)
 
 
@login_required
@company_required
def transfer_report(request):
    company = request.user.company_profile.company
    groups = Group.objects.filter(company=company, isdeleted=False).values('group_id', 'group_name')
    context = {'company': company, 'groups': groups}
    return render(request, 'Dashboard/Company/reports/Transfer_report.html', context)
 
 
@login_required
@company_required
def claim_report(request):
    company = request.user.company_profile.company
    groups = Group.objects.filter(company=company, isdeleted=False).values('group_id', 'group_name')
    context = {'company': company, 'groups': groups}
    return render(request, 'Dashboard/Company/reports/claim_report.html', context)
 
 
@login_required
@company_required
def business_detail_report(request):
    company = request.user.company_profile.company
    groups = Group.objects.filter(company=company, isdeleted=False).values('group_id', 'group_name')
    context = {'company': company, 'groups': groups}
    return render(request, 'Dashboard/Company/reports/Business_detail_report.html', context)
 
 
@login_required
@company_required
def loan_repayment_report(request):
    company = request.user.company_profile.company
    groups = Group.objects.filter(company=company, isdeleted=False).values('group_id', 'group_name')
    context = {'company': company, 'groups': groups}
    return render(request, 'Dashboard/Company/reports/group_loan_report.html', context)
 
 
@login_required
@company_required
def policy_summary(request):
    company = request.user.company_profile.company
    context = {'company': company}
    return render(request, 'Dashboard/Company/policy_summary_report.html', context)
 
 
@login_required
@company_required
def surrender_calculator(request):
    company = request.user.company_profile.company
    context = {'company': company}
    return render(request, 'Dashboard/Company/surrender_calculator.html', context)
 
 
# ============================================================
# PRIMARY COMPANY USER VIEWS
# ============================================================
 
@login_required
@primary_company_required
def company_info(request):
    """
    Allows the primary company account user to update company contact
    information (pan_number, primary_contact_person, primary_person_mobile,
    primary_person_email) and manage company documents.
 
    GET:  renders the form pre-populated with existing data.
    POST: updates company info or uploads documents.
    """
    company = request.user.company_profile.company
 
    # Get or prepare document instance (may not exist yet)
    try:
        document = company.documents
    except CompanyDocument.DoesNotExist:
        document = None
 
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
 
        # ── Company info update ──────────────────────────────
        if form_type == 'company_info':
            info_data = {
                'pan_number':             request.POST.get('pan_number', '').strip() or None,
                'primary_contact_person': request.POST.get('primary_contact_person', '').strip() or None,
                'primary_person_mobile':  request.POST.get('primary_person_mobile', '').strip() or None,
                'primary_person_email':   request.POST.get('primary_person_email', '').strip() or None,
                'nepali_name':            request.POST.get('nepali_name', '').strip() or None,
                'email':                  request.POST.get('email', '').strip() or None,
                'phone_number':           request.POST.get('phone_number', '').strip() or None,
                'telephone_number':       request.POST.get('telephone_number', '').strip() or None,
            }
 
            try:
                CompanyService.update_company_info(
                    company=company,
                    info_data=info_data,
                    user=request.user,
                )
                messages.success(request, 'Company information updated successfully.')
            except Exception as e:
                messages.error(request, f'Failed to update company information: {str(e)}')
 
            return redirect('company_info')
 
        # ── Document upload ──────────────────────────────────
        elif form_type == 'company_documents':
            authorized_by    = request.POST.get('authorized_by', '').strip() or None
            business_purpose = request.POST.get('business_purpose', '').strip() or None

            try:
                if document is None:
                    document = CompanyDocument(
                        company=company,
                        created_by=request.user.username,
                    )

                document.modified_by = request.user.username

                # Only set if not already filled
                if not document.authorized_by and authorized_by:
                    document.authorized_by = authorized_by
                if not document.business_purpose and business_purpose:
                    document.business_purpose = business_purpose
                if not document.signature and 'signature' in request.FILES:
                    document.signature = request.FILES['signature']
                if not document.stamp and 'stamp' in request.FILES:
                    document.stamp = request.FILES['stamp']
                if not document.official_request_letter and 'official_request_letter' in request.FILES:
                    document.official_request_letter = request.FILES['official_request_letter']

                document.save()
                messages.success(request, 'Documents updated successfully.')
            except Exception as e:
                messages.error(request, f'Failed to update documents: {str(e)}')

            return redirect('company_info')
 
    context = {
        'company': company,
        'document': document,
    }
    return render(request, 'Dashboard/Company/company_info.html', context)
 
 
@login_required
@primary_company_required
def manage_accounts(request):
    """
    Allows the primary company account user to:
      GET:  view all company accounts and their approval status,
            plus account slot stats.
      POST: create a new company account (is_approved=False, enforce_limit=True).
    """
    company = request.user.company_profile.company
    stats = CompanyAccountService.get_account_stats(company)
 
    accounts = CompanyAccount.objects.filter(
        company=company
    ).select_related('account').order_by('-is_primary', '-is_approved', 'full_name')
 
    if request.method == 'POST':
        # Check limit before even trying — give early feedback
        if stats['remaining'] <= 0:
            messages.error(
                request,
                f"Account limit reached ({stats['limit']} accounts maximum). "
                f"Please contact your administrator to increase the limit."
            )
            return redirect('manage_accounts')
 
        username    = request.POST.get('username', '').strip()
        password    = request.POST.get('password', '').strip()
        full_name   = request.POST.get('full_name', '').strip() or None
        mobile      = request.POST.get('mobile', '').strip() or None
        email       = request.POST.get('email', '').strip() or None
        designation = request.POST.get('designation', '').strip() or None
        department  = request.POST.get('department', '').strip() or None
 
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('manage_accounts')
 
        profile_data = {
            'company':     company,
            'full_name':   full_name,
            'mobile':      mobile,
            'email':       email,
            'designation': designation,
            'department':  department,
            'is_primary':  False,   # Primary is always set by staff, never by portal
            'is_approved': False,   # Portal path — always pending
        }
 
        try:
            CompanyAccountService.create_company_account(
                username=username,
                password=password,
                profile_data=profile_data,
                user=request.user,
                enforce_limit=True,
            )
            messages.success(
                request,
                f"Account '{username}' created successfully and is pending approval."
            )
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Failed to create account: {str(e)}')
 
        return redirect('manage_accounts')
 
    context = {
        'company':  company,
        'accounts': accounts,
        'stats':    stats,
    }
    return render(request, 'Dashboard/Company/manage_accounts.html', context)


@login_required
@primary_company_required
@require_POST
def reset_account_password(request, account_id):
    """
    Allows the primary company user to reset the password of another
    account in the same company. Called from the modal on manage_accounts.
    """
    company = request.user.company_profile.company

    try:
        target_profile = CompanyAccount.objects.select_related('account').get(
            account__id=account_id,
            company=company,
        )
    except CompanyAccount.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Account not found.'}, status=404)

    if target_profile.account == request.user:
        return JsonResponse(
            {'success': False, 'error': 'Use the change password form for your own account.'},
            status=400,
        )

    new_password     = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    if not new_password or not confirm_password:
        return JsonResponse({'success': False, 'error': 'Both password fields are required.'}, status=400)

    if new_password != confirm_password:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=400)

    try:
        CompanyAccountService.reset_company_account_password(
            target_company_account=target_profile,
            new_password=new_password,
            user=request.user,
        )
    except PermissionDenied as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)

    return JsonResponse({
        'success': True,
        'message': f"Password for '{target_profile.account.username}' has been reset successfully.",
    })

 
# ============================================================
# PASSWORD
# ============================================================
 
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
 
    if getattr(settings, 'ENFORCE_PASSWORD_STRENGTH', False):
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
        ip_address=request.META.get('REMOTE_ADDR'),
    )
 
    return JsonResponse({'success': True, 'message': 'Password changed successfully.'})
 
 
# ============================================================
# LOGOUT
# ============================================================
 
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')
