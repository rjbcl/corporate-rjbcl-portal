from typing import Callable, Dict

from .maturity_forecasting import fetch as fetch_maturity_forecasting
from .group_transfer        import fetch as fetch_group_transfer
from .loan_repayment        import fetch as fetch_loan_repayment
from .death_claim           import fetch as fetch_death_claim
from .maturity_claim        import fetch as fetch_maturity_claim
from .business_detail       import fetch as fetch_business_detail
from .surrender_claim       import fetch as fetch_surrender_claim
from .policy_summary        import fetch as fetch_policy_summary
from .surrender_calc import fetch as fetch_surrender_calculator
from .dashboard_data import fetch as fetch_dashboard_data
from .policy_detail import fetch as fetch_policy_detail
from .group_information import fetch as fetch_group_information
from .company_policies import (
    fetch_statistics as fetch_company_policies_statistics,
    fetch_by_company as fetch_company_policies_by_company,
    fetch_list as fetch_company_policies_list,
)



REPORTS: Dict[str, Callable] = {
    "maturity_forecasting": fetch_maturity_forecasting,
    "group_transfer":       fetch_group_transfer,
    "loan_repayment":       fetch_loan_repayment,
    "death_claim":          fetch_death_claim,
    "maturity_claim":       fetch_maturity_claim,
    "business_detail":      fetch_business_detail,
    "surrender_claim":      fetch_surrender_claim,
    "policy_summary":       fetch_policy_summary,
    "surrender_calculator": fetch_surrender_calculator,
    "dashboard_data": fetch_dashboard_data,
    "policy_detail": fetch_policy_detail,
    "group_information": fetch_group_information,
    "company_policies_statistics": fetch_company_policies_statistics,
    "company_policies_by_company": fetch_company_policies_by_company,
    "company_policies_list":       fetch_company_policies_list,
}