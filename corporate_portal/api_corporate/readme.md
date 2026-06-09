# Corporate Portal API Documentation

## Overview

This document describes the REST API for accessing corporate group insurance data.
The API is intended for server-to-server integration only — do not call these endpoints
from a browser or mobile app directly.

**Base URL:** `https://api.rbs.gov.np/api/corporate`

---

## Authentication

All requests must include your API key in the request header:

```
X-API-Key: copo_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

API keys are issued by the portal administrator. Keep your key secure — treat it like
a password. If your key is compromised, contact the administrator to revoke and reissue it.

**If your key is missing or invalid:**
```json
HTTP 403
{ "detail": "Invalid or revoked API key." }
```

**If your company account is inactive:**
```json
HTTP 403
{ "detail": "Company account is inactive." }
```

---

## General Notes

- All request bodies must be JSON with `Content-Type: application/json`
- All dates are in `YYYY-MM-DD` format unless stated otherwise
- Datetime fields in responses are ISO 8601 format
- `null` values indicate the field exists but has no data
- An empty results array `[]` means the query succeeded but returned no data

---

## Endpoints

---

### 1. List Groups

Returns all groups belonging to your company.

```
GET /groups/
```

**Request:**
```
GET https://api.rbs.gov.np/api/corporate/groups/
X-API-Key: copo_xxx...
```

**Response:**
```json
{
    "count": 2,
    "group_ids": ["052", "071"],
    "results": [
        {
            "group_id": "052",
            "group_name": "Example Group One",
            "group_name_nepali": null,
            "is_active": true,
            "total_members_count": 120,
            "total_active_policies": 98,
            "total_premium": "980000.00",
            "total_sa": "24500000.00",
            "death_claim": 2,
            "surrender_claim": 1,
            "maturity_claim": 5,
            "transfer_claim": 0,
            "terminate_claim": 0,
            "cancel_claim": 0
        }
    ]
}
```

---

### 2. Policy Search

Search for policies by policy number, member name, or employee ID.
Returns up to 15 matching results.

```
POST /policy-search/
```

**Request body:**
```json
{
    "q": "search term"
}
```

**Response:**
```json
[
    {
        "policyNo": "05208090",
        "name": "LAXMI GIRI",
        "employeeid": "EMP001"
    }
]
```

**Notes:**
- `q` is matched against policy number, name, and employee ID simultaneously
- Returns an empty array if no matches found
- Use this to look up a `policy_no` before calling the policy detail endpoint

---

### 3. Policy Detail

Returns full policy summary and loan details for a single policy.

```
POST /policy-detail/
```

**Request body:**
```json
{
    "policy_no": "05208090"
}
```

**Response:**
```json
{
    "success": true,
    "policy_no": "05208090",
    "summary": [
        {
            "PolicyNo": "05208090",
            "Branch": "300",
            "Name": "LAXMI GIRI",
            "NepName": null,
            "GroupId": "052",
            "DOB": "1978-01-08T00:00:00",
            "Gender": null,
            "Address": null,
            "Email": null,
            "Mobile": null,
            "FatherName": null,
            "MotherName": null,
            "NomineeName": null,
            "NomineeRelationship": null,
            "ClaimDate": null,
            "Sumassured": "176400.0000",
            "DOC": "2003-11-23",
            "FUP": "2023-11-23T00:00:00",
            "Term": 20,
            "Premium": "8001.5900",
            "Instalment": 20,
            "PaidAmount": "160031.8000",
            "maturitydate": "2023-11-23",
            "PolicyStatus": "M",
            "PolicyType": null
        }
    ],
    "loans": [
        {
            "PolicyNo": "05208090",
            "loanID": 1,
            "LoanDate": "2020-05-01T00:00:00",
            "LoanAmount": "50000.0000",
            "InterestRate": "10.00",
            "Instalment": 12,
            "Status": "A",
            "LastPaidDate": "2021-05-01T00:00:00",
            "VoucherNo": "V001"
        }
    ]
}
```

**Notes:**
- `summary` is an array but will contain at most one record per policy number
- `loans` is an empty array if the policy has no loans
- Returns `403` if the policy does not belong to your company's groups

**Policy status codes:**

| Code | Meaning |
|------|---------|
| `A`  | Active  |
| `L`  | Lapsed  |
| `M`  | Matured |
| `S`  | Surrendered |
| `D`  | Death Claim |

---

### 4. Policy Loans

Returns loan records for a specific policy.

```
POST /reports/policy-loans/
```

**Request body:**
```json
{
    "policy_no": "05208090"
}
```

**Response:**
```json
[
    {
        "PolicyNo": "05208090",
        "loanID": 1,
        "LoanDate": "2020-05-01T00:00:00",
        "LoanAmount": "50000.0000",
        "InterestRate": "10.00",
        "Instalment": 12,
        "Status": "A",
        "LastPaidDate": "2021-05-01T00:00:00",
        "VoucherNo": "V001"
    }
]
```

---

### 5. Policy Summary Report

Returns summary data for a single policy from the reporting view.

```
POST /policy-summary/
```

**Request body:**
```json
{
    "policy_no": "05208090"
}
```

---

### 6. Maturity Forecasting Report

Returns policies approaching maturity within a date range.

```
POST /reports/maturity-forecasting/
```

**Request body:**
```json
{
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "date_type": "ad"
}
```

**Response:**
```json
{
    "success": true,
    "count": 10,
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "date_type": "ad",
    "policies": [ { ... } ]
}
```

**Notes:**
- `date_type` accepts `"ad"` (Gregorian) or `"bs"` (Bikram Sambat)
- `group_id` must belong to your company

---

### 7. Group Transfer Report

Returns transfer records for a group within a date range.

```
POST /reports/group-transfer/
```

**Request body:**
```json
{
    "group_id": "052",
    "transfer_date_from": "2024-01-01",
    "transfer_date_to": "2024-12-31",
    "date_type": "ad"
}
```

**Response:**
```json
{
    "success": true,
    "count": 3,
    "group_id": "052",
    "transfer_date_from": "2024-01-01",
    "transfer_date_to": "2024-12-31",
    "date_type": "ad",
    "transfers": [ { ... } ]
}
```

---

### 8. Loan Repayment Report

Returns loan repayment records for a group within a date range.

```
POST /reports/loan-repayment/
```

**Request body:**
```json
{
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "date_type": "ad"
}
```

**Response:**
```json
{
    "success": true,
    "count": 5,
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "date_type": "ad",
    "repayments": [ { ... } ]
}
```

---

### 9. Death Claim Report

Returns death claim records for a group within a date range.

```
POST /reports/death-claim/
```

**Request body:**
```json
{
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
}
```

---

### 10. Maturity Claim Report

Returns maturity claim records for a group within a date range.

```
POST /reports/maturity-claim/
```

**Request body:**
```json
{
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
}
```

---

### 11. Surrender Claim Report

Returns surrender claim records for a group within a date range.

```
POST /reports/surrender-claim/
```

**Request body:**
```json
{
    "group_id": "052",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
}
```

---

### 12. Business Detail Report

Returns new or renewal business detail for a group within a date range.

```
POST /reports/group-business-detail/
```

**Request body:**
```json
{
    "group_id": "052",
    "flag": "NB",
    "filter_by": "PaidDate",
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
}
```

**Parameter values:**

| Field | Options | Meaning |
|-------|---------|---------|
| `flag` | `NB` | New Business |
| `flag` | `RB` | Renewal Business |
| `filter_by` | `PaidDate` | Filter by payment date |
| `filter_by` | `ValueDate` | Filter by value date |

---

### 13. Surrender Calculator

Calculates the surrender value for a policy.

```
POST /surrender-calculator/
```

**Request body:**
```json
{
    "policy_no": "05208090",
    "claim_date": "2024-06-01"
}
```

**Notes:**
- `claim_date` is optional — omit it to calculate based on today's date
- Returns `404` if the policy is not found or does not belong to your company

---

## Error Reference

| Status | Meaning |
|--------|---------|
| `400`  | Missing or invalid request parameters |
| `403`  | Authentication failed, company inactive, or access to requested data denied |
| `404`  | Requested record not found |
| `500`  | Server error — contact the administrator |

All error responses follow this shape:
```json
{
    "error": "Human readable message"
}
```

---

## Quick Start Example

```python
import requests

API_KEY = "copo_your_key_here"
BASE_URL = "https://api.rbs.gov.np/api/corporate"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

# 1. Get your groups
groups = requests.get(f"{BASE_URL}/groups/", headers=HEADERS).json()
group_id = groups["group_ids"][0]

# 2. Search for a policy
results = requests.post(
    f"{BASE_URL}/policy-search/",
    headers=HEADERS,
    json={"q": "LAXMI"},
).json()
policy_no = results[0]["policyNo"]

# 3. Get full policy detail
detail = requests.post(
    f"{BASE_URL}/policy-detail/",
    headers=HEADERS,
    json={"policy_no": policy_no},
).json()

print(detail["summary"])
print(detail["loans"])
```

---

*For API key provisioning or support, contact your portal administrator.*