from django.contrib import admin  # type: ignore
from django.utils.html import format_html  # type: ignore
from django.contrib import messages  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import path, reverse  # type: ignore

from .models import APIKey


# @admin.register(APIKey)
# class APIKeyAdmin(admin.ModelAdmin):
#     """
#     Admin interface for API key management.
#     Superadmin only — key generation is done via the
#     'Generate New Key' action on the change page.

#     The raw key is shown once in a success message immediately
#     after generation. It is never stored or retrievable again.
#     """

#     list_display = [
#         'company',
#         'is_active',
#         'created_by',
#         'created_at',
#         'last_used_at',
#         'key_preview',
#     ]
#     list_filter = ['is_active']
#     search_fields = ['company__company_name', 'created_by']
#     readonly_fields = [
#         'key_hash',
#         'created_by',
#         'created_at',
#         'last_used_at',
#     ]

#     # Disallow manual key creation — must use generate action
#     def has_add_permission(self, request):
#         return False

#     def get_urls(self):
#         urls = super().get_urls()
#         custom = [
#             path(
#                 '<path:object_id>/generate-key/',
#                 self.admin_site.admin_view(self.generate_key_view),
#                 name='apikey_generate',
#             ),
#         ]
#         return custom + urls

#     def change_view(self, request, object_id, form_url='', extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['show_generate_button'] = True
#         extra_context['generate_url'] = reverse(
#             'admin:apikey_generate', args=[object_id]
#         )
#         return super().change_view(request, object_id, form_url, extra_context)

#     def generate_key_view(self, request, object_id):
#         """
#         Generates a new API key for the company, replacing any existing one.
#         Shows the raw key once in a success message.
#         Only accessible to superadmins.
#         """
#         if not request.user.is_superuser:
#             self.message_user(
#                 request,
#                 'Only superadmins can generate API keys.',
#                 level=messages.ERROR,
#             )
#             return HttpResponseRedirect(
#                 reverse('admin:api_corporate_apikey_changelist')
#             )

#         api_key_obj = APIKey.objects.select_related('company').get(pk=object_id)

#         try:
#             raw_key = APIKey.generate_key(
#                 company=api_key_obj.company,
#                 created_by=request.user.username,
#             )
#             self.message_user(
#                 request,
#                 format_html(
#                     '<strong>New API key generated for {}.</strong><br>'
#                     'Copy this key now — it will never be shown again:<br>'
#                     '<code style="font-size:1.1em; background:#f8f8f8; '
#                     'padding:4px 8px; border-radius:4px;">{}</code>',
#                     api_key_obj.company.company_name,
#                     raw_key,
#                 ),
#                 level=messages.SUCCESS,
#             )
#         except ValueError as e:
#             self.message_user(request, str(e), level=messages.ERROR)

#         return HttpResponseRedirect(
#             reverse('admin:api_corporate_apikey_change', args=[object_id])
#         )

#     @admin.display(description='Key Hash Preview')
#     def key_preview(self, obj):
#         """Shows first 8 chars of hash — enough to identify, not enough to misuse."""
#         return f"{obj.key_hash[:8]}…" if obj.key_hash else '—'

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('company')


# def register_company_api_key_inline():
#     """
#     Optionally call this from main_system/admin.py to add
#     an APIKey inline on the Company admin page.
#     """
#     from main_system.admin import CompanyAdmin
#     from django.contrib.admin import StackedInline

#     class APIKeyInline(StackedInline):
#         model = APIKey
#         extra = 0
#         readonly_fields = ['key_hash', 'created_by', 'created_at', 'last_used_at']
#         can_delete = False
#         show_change_link = True
#         verbose_name = 'API Key'
#         verbose_name_plural = 'API Key'

#         def has_add_permission(self, request, obj=None):
#             return False

#     CompanyAdmin.inlines = list(getattr(CompanyAdmin, 'inlines', [])) + [APIKeyInline]