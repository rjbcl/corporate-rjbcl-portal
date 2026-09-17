from django.urls import path  # type: ignore
from .views import (
    policy_summary_report,
    group_information,
    company_policies_web,
    maturity_forecasting_report,
    death_claim_report,
    maturity_claim_report,
    surrender_claim_report,
    loan_repayment_report,
    policy_search,
    policy_loans,
    group_transfer_report,
    group_business_detail_report,
    surrender_calculator,
    policy_detail,
    # New function-based view replacements for the two ViewSets:
    company_policies_list,
    company_policies_statistics,
    group_endowment_list,
)

urlpatterns = [
    # Group Information
    path('groups/', group_information, name='group-information'),

    # Web dashboard endpoint (already ported)
    path('endowments/by_company/', company_policies_web, name='company-policies-web'),

    # CompanyPoliciesViewSet replacement
    path('company/policies/', company_policies_list, name='company-policies-list'),
    path('company/policies/statistics/', company_policies_statistics, name='company-policies-statistics'),

    # GroupEndowmentViewSet replacement (list only — by_company is already mapped above)
    path('endowments/', group_endowment_list, name='group-endowment-list'),

    # Report endpoints
    path('reports/maturity-forecasting/', maturity_forecasting_report, name='maturity-forecasting'),
    path('reports/loan-repayment/', loan_repayment_report, name='loan-repayment-report'),
    path('reports/policy-loans/', policy_loans, name='policy-loans'),
    path('reports/maturity-claim/', maturity_claim_report, name='maturity-claim-report'),
    path('reports/death-claim/', death_claim_report, name='death-claim-report'),
    path('reports/surrender-claim/', surrender_claim_report, name='surrender-claim-report'),
    path('reports/group-transfer/', group_transfer_report, name='group-transfer-report'),
    path('reports/group-business-detail/', group_business_detail_report, name='group-business-detail-report'),

    # Policy endpoints
    path('policy-search/', policy_search, name='policy-search'),
    path('policy-summary/', policy_summary_report, name='policy-summary-report'),
    path('surrender-calculator/', surrender_calculator, name='surrender-calculator'),
    path('policy-detail/', policy_detail, name='policy-detail'),
]