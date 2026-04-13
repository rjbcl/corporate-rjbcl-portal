# Corporate Portal API Documentation

## Overview

This document describes the REST API endpoints available to authenticated company users of the Corporate Portal. All endpoints are prefixed with the base URL:

```
https://your-base-url.com/api/corporate/
```

All API responses are in JSON format. Authentication is handled via JWT (JSON Web Token). **Only active company accounts** can access these endpoints.

---

## Authentication

### Login

Obtain a JWT access and refresh token pair.

**Endpoint:** `POST /api/corporate/auth/login/`

**Authentication:** None (public endpoint)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Company account username |
| `password` | string | Yes | Account password |

**Example Request:**
```json
{
  "username": "company_user",
  "password": "yourpassword"
}
```

**Success Response (200):**
```json
{
  "access": "<JWT access token>",
  "refresh": "<JWT refresh token>",
  "username": "company_user"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| `401` | Invalid credentials |
| `403` | Account is not a company account, or company account is inactive |

---

### Refresh Token

Obtain a new access token using a valid refresh token.

**Endpoint:** `POST /api/corporate/auth/refresh/`

**Authentication:** None

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh` | string | Yes | A valid JWT refresh token |

**Example Request:**
```json
{
  "refresh": "<JWT refresh token>"
}
```

**Success Response (200):**
```json
{
  "access": "<new JWT access token>"
}
```

---

## General Conventions

### Authorization Header

All authenticated endpoints require the JWT access token to be passed in the request header:

```
Authorization: Bearer <access token>
```

### Date Format

All dates must be provided in `YYYY-MM-DD` format (AD only).

```
"from_date": "2024-01-01"
"to_date":   "2024-12-31"
```

### Access Control

Each company can only access data belonging to their own groups. Any attempt to access another company's data will return a `403 Forbidden` response.

### Common Error Response Shape

```json
{
  "error": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `400` | Bad request / missing or invalid parameters |
| `401` | Unauthenticated — token missing or invalid |
| `403` | Forbidden — account inactive or accessing unauthorized data |
| `404` | Resource not found |
| `500` | Server error |

---

## Groups

### Get Group Information

Returns all groups associated with the authenticated company.

**Endpoint:** `GET /api/corporate/groups/`

**Authentication:** JWT required

**Query Parameters:** None (data is automatically scoped to the authenticated company)

**Success Response (200):**
```json
{
    "count": 3,
    "group_ids": [
        "G01",
        "G02",
        "G03"
    ],
    "results": [
        {
            "group_id": "G01",
            "group_name": "Dummy Group",
            "group_name_nepali": "Nepali Name in Devnagari",
            "is_active": true,
            "total_members_count": 123,
            "total_active_policies": 123,
            "total_premium": "123",
            "total_sa": "123.0000",
            "death_claim": 123,
            "surrender_claim": 123,
            "maturity_claim": 123,
            "transfer_claim": 123,
            "terminate_claim": 123,
            "cancel_claim": 123
        }
    ]
```

> **Note:** Fill in response field names based on your `GroupInformationSerializer`.

---

## Policies

### List Company Policies

Returns a paginated list of all endowment policies belonging to the authenticated company's groups.

**Endpoint:** `GET /api/corporate/company/policies/`

**Authentication:** JWT required

**Query Parameters (all optional):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `policy_status` | string | Filter by policy status (e.g. `A` for active, `L` for lapsed) |
| `fiscal_year` | string | Filter by fiscal year |
| `gender` | string | Filter by gender |
| `policy_type` | string | Filter by policy type |
| `is_adb` | boolean | Filter by ADB flag |
| `register_no` | string | Filter by register number |
| `employee_id` | string | Filter by employee ID |
| `claim_status` | string | Filter by claim status |
| `branch` | string | Filter by branch |
| `search` | string | Search across name, policy number, employee ID, mobile, email, register number |
| `ordering` | string | Order by field: `maturity_date`, `doc`, `name`, `premium`, `sum_assured`. Prefix with `-` for descending (default: `-maturity_date`) |

**Success Response (200):**
```json
{
  "count": 119773,
  "next": "http://xyz.com/api/corporate/company/policies/?page=2",
  "previous": null,
  "results": [
                {
                    "register_no": "reg123",
                    "policy_no": "pol123",
                    "group_id": "G123",
                    "doc": "2024-11-23",
                    "term": 123,
                    "sum_assured": "123.0000",
                    "premium": "123.0000",
                    "fup": "2025-11-23T00:00:00Z",
                    "maturity_date": "2044-11-23",
                    "policy_status": "A",
                    "policy_type": "S",
                    "late_fine": "0.0000",
                    "paid_date": "2025-02-02T12:34:01.317000Z",
                    "instalment": 1,
                    "paid_amount": "123.0000",
                    "batch_no": "123",
                    "intrest": null,
                    "claim_status": null,
                    "late_fine_percent": null,
                    "reduced_instalment": null,
                    "employee_id": "",
                    "name": "John Dow",
                    "nep_name": "",
                    "gender": "M",
                    "occupation": "",
                    "dob": "2000-01-22T00:00:00Z",
                    "extra_premium": "0.0000",
                    "total_premium": null,
                    "address": "",
                    "email": "",
                    "mobile": "",
                    "adb": null,
                    "occ_extra_amount": null,
                    "adb_discount": null,
                    "father_name": null,
                    "mother_name": null,
                    "nominee_name": "John Doe",
                    "nominee_address": null,
                    "transfer_date": null,
                    "duplicate_policy_date": null,
                    "lapse_date": null,
                    "lapse_active_date": null,
                    "doe": null,
                    "basic_premium": "123.0000",
                    "is_adb": "N",
                    "after_dis_rebate_rate": "123",
                    "fiscal_year": "123",
                    "nominee_relationship": null,
                    "claim_date": null,
                    "termination_date": null,
                    "plan_id": 1,
                    "is_multiple_policy_issued": true
                },
```

---

### Policy Statistics

Returns aggregate statistics for the authenticated company's policies.

**Endpoint:** `POST /api/corporate/company/policies/statistics/`

**Authentication:** JWT required

**Request Body:** None

**Success Response (200):**
```json
{
  "total_policies": 500,
  "active_policies": 420,
  "lapsed_policies": 50,
  "inactive_policies": 30,
  "total_sum_assured": 125000000.00,
  "total_premium": 3500000.00
}
```

---

## Policy Utilities

### Policy Search

Searches policies by policy number, name, or employee ID. Returns up to 15 results.

**Endpoint:** `POST /api/corporate/policy-search/`

**Authentication:** JWT required

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search query (matches against policy number, name, and employee ID) |

**Example Request:**
```json
{
  "q": "John"
}
```

**Success Response (200):**
```json
[
  {
    "policyNo": "DUMMY_POLICY_NO",
    "name": "DUMMY_NAME",
    "employeeid": "DUMMY_EMP_ID"
  }
]
```

Returns an empty array `[]` if the query is blank or no matches are found.

---

### Policy Summary

Returns full summary details for a specific policy.

**Endpoint:** `POST /api/corporate/policy-summary/`

**Authentication:** JWT required

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy_no` | string | Yes | The policy number to look up |

**Example Request:**
```json
{
  "policy_no": "05208669"
}
```

**Success Response (200):**
```json
[
    {
        "PolicyNo": "POL123",
        "Branch": "300",
        "Name": "KRISHNA BAHADUR PAKHREL",
        "NepName": null,
        "GroupId": "G01",
        "DOB": "1953-11-15T00:00:00",
        "Gender": null,
        "Address": null,
        "Email": null,
        "Mobile": null,
        "FatherName": null,
        "MotherName": null,
        "NomineeName": null,
        "NomineeRelationship": null,
        "ClaimDate": null,
        "DistrictID": null,
        "WardNo": null,
        "NomineePhone": null,
        "NomineeAddress": null,
        "Occupation": "A",
        "Sumassured": "123.0000",
        "DOC": "1994-11-23",
        "PaidDate": "2008-11-23T00:00:00",
        "FUP": "2009-11-23T00:00:00",
        "Term": 123,
        "Premium": "123.0600",
        "Instalment": 123,
        "PaidAmount": "123.9000",
        "maturitydate": "2009-01-23",
        "PolicyStatus": "M",
        "PolicyType": null
    }
]
```

> **Note:** Fill in response field names from `view_copo_policySummary`.

---

### Policy Loans

Returns loan details for a specific policy. The policy must belong to the authenticated company.

**Endpoint:** `POST /api/corporate/reports/policy-loans/`

**Authentication:** JWT required

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy_no` | string | Yes | The policy number |

**Example Request:**
```json
{
  "policy_no": "05208669"
}
```

**Success Response (200):**
```json
[
    {
        "PolicyNo": "POL123",
        "loanID": "123",
        "LoanDate": "2021-11-17T00:00:00",
        "LoanAmount": "123.00",
        "InterestRate": "123.00",
        "Instalment": 123,
        "Status": "CLEARED",
        "LastPaidDate": "2022-01-13T00:00:00",
        "VoucherNo": "123"
    }
]
```

Returns an empty array `[]` if no loans exist for the policy.

---

### Surrender Calculator

Returns the surrender value and active loan status for a specific policy.

**Endpoint:** `POST /api/corporate/surrender-calculator/`

**Authentication:** JWT required

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy_no` | string | Yes | The policy number |

**Example Request:**
```json
{
  "policy_no": "05208669"
}
```

**Success Response (200):**
```json
{
  "SurrenderValue":"3297858.0000",
  "HasActiveLoan":false
}
```

| Field | Description |
|-------|-------------|
| `hasActiveLoan` | `1` if an active loan exists, `0` if not |
| `SurrenderAmount` | Calculated surrender value |

---

## Reports

> All report endpoints require JWT authentication and accept only `POST` requests. Dates must be in `YYYY-MM-DD` format.

---

### Maturity Forecasting Report

Returns policies expected to mature within a given date range for a specific group.

**Endpoint:** `POST /api/corporate/reports/maturity-forecasting/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
{
    "success": true,
    "count": 1687,
    "group_id": "G01",
    "from_date": "2026-01-01",
    "to_date": "2032-12-31",
    "date_type": "ad",
    "policies": [
        {
            "SN": 1,
            "PolicyNo": "POL123",
            "Branch": "300",
            "Name": "John Doe",
            "NepName": null,
            "GroupId": "G01",
            "DOB": "24/01/1972",
            "DOC": "23/11/2006",
            "SumAssured": "123.0000",
            "Term": 123,
            "Instalment": 123,
            "Premium": "23123079.4300",
            "MaturityDate": "23/01/2026",
            "TotalPolicy": 123,
            "RemainingDayToMature": 224,
            "PolicyStatus": "A"
        }
    ]
}
```

---

### Loan Repayment Report

Returns loan repayment records for a group within a date range.

**Endpoint:** `POST /api/corporate/reports/loan-repayment/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
{
    "success": true,
    "count": 388,
    "group_id": "G01",
    "from_date": "2024-01-01",
    "to_date": "2026-12-31",
    "date_type": "ad",
    "repayments": [
        {
            "PolicyNo": "POL123",
            "FullName": "John Doe",
            "LoanId": "123",
            "LoanDate": "2014-12-10",
            "LoanAmount": "123.00",
            "Instalment": 1,
            "DuePrincipal": "123.0000",
            "PaidPrincipal": "123.0000",
            "RemainingPrincipal": "0.0000",
            "PaidInterest": "123.0000",
            "RemainingInterest": "0.0000",
            "Cash": "0.0000",
            "Cheque": "0.0000",
            "Bank": "123.0000",
            "PaymentFrom": "Nepal Bank ltd.",
            "Status": "CLEARED",
            "PaidDate": "2024-01-01",
            "Tran/Cheque Date": "2024-01-01",
            "VoucherNo": "123"
        },
    ]
}
```

---

### Maturity Claim Report

Returns matured policies that have been claimed within a date range.

**Endpoint:** `POST /api/corporate/reports/maturity-claim/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
{
        "GroupId": "G01",
        "PolicyNo": "POL123",
        "EmployeeId": null,
        "Name": "John Doe",
        "NepName": null,
        "DOB": "27/07/1972",
        "SA": "123.0000",
        "Premium": "qwe.1200",
        "DOC": "23/11/2001",
        "MaturityDate": "23/11/2023",
        "Bonus": "123.0000",
        "TotalTax": "123.0000",
        "ClaimAmount": "123.0000",
        "LoanAmount": "0.0000",
        "CalculatedInterest": "0.0000",
        "NetClaimAmount": "123.0000",
        "ClaimDate": "09/01/2024",
        "VoucherNo": "123",
        "ClaimId": "123"
}
```

---

### Death Claim Report

Returns death claim records for a group within a date range.

**Endpoint:** `POST /api/corporate/reports/death-claim/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
{
            "GroupId": "G01",
            "PolicyNo": "POL123",
            "EmployeeId": null,
            "Name": "John Doe",
            "NepName": null,
            "DOB": "17/07/1971",
            "SA": "123.0000",
            "Premium": "123.6300",
            "DOC": "23/11/2025",
            "MaturityDate": "23/11/2035",
            "Bonus": "123.8000",
            "ClaimAmount": "123.0000",
            "LoanAmount": "123.0000",
            "InterestOnLoanAmount": "123.0000",
            "TotalClaimAmount": "123.8000",
            "NetClaimAmount": "123.8000",
            "DeathDate": "24/02/2024",
            "IntimationDate": "16/01/2024",
            "TerminationDate": "22/03/2024",
            "VoucherNo": "123",
            "ClaimId": "123",
            "Instalment": 123
}
```

---

### Surrender Claim Report

Returns surrender claim records for a group within a date range.

**Endpoint:** `POST /api/corporate/reports/surrender-claim/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
    {
        "SNo": 1,
        "GroupId": "G01",
        "PolicyNo": "POL123",
        "EmployeeId": null,
        "Name": "John Doe",
        "NepName": null,
        "DOB": "28/11/1964",
        "DOC": "23/11/2014",
        "SA": "123.0000",
        "Premium": "123.7700",
        "Term": "123",
        "MaturityDate": "23/12/2025",
        "SurrenderAmount": "123.0000",
        "SurrenderDate": "29/11/2024",
        "IntimationDate": "11/15/2025",
        "VoucherNo": "123",
        "Tax": "123.0000",
        "LoanAmount": "123.0000",
        "LoanInterest": "0.0000",
        "NetPayable": "123",
        "ClaimId": "123",
        "Instalment": 123
    }
```

---

### Group Transfer Report

Returns transfer records for members moved between groups within a date range.

**Endpoint:** `POST /api/corporate/reports/group-transfer/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `transfer_date_from` | string | Yes | Start date (`YYYY-MM-DD`) |
| `transfer_date_to` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "transfer_date_from": "2024-01-01",
  "transfer_date_to": "2024-12-31"
}
```

**Success Response (200):**
```json
{
    "success": true,
    "count": 10,
    "group_id": "G01",
    "transfer_date_from": "2023-01-01",
    "transfer_date_to": "2026-12-31",
    "date_type": "ad",
    "transfers": [
        {
            "EmployeeId": null,
            "PolicyNo": "POL123",
            "PreviousPolicy": "123",
            "GroupId": "G01",
            "Name": "John Doe",
            "Nepali Name": "John Doe",
            "DOB": "27/07/1986",
            "DOC": "23/11/2015",
            "SA": "123.0000",
            "Term": "123",
            "BasicPremium": "123.9100",
            "ADB": "0.0000",
            "Premium": "123.00",
            "PaidAmount": "123.0000",
            "Maturity Date": "23/01/2035",
            "Instalment": 123,
            "TransferDate": "28/05/2023"
        }
    ]
}
```

---

### Group Business Detail Report

Returns new or renewal business details for a group within a date range.

**Endpoint:** `POST /api/corporate/reports/group-business-detail/`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group_id` | string/int | Yes | The group ID |
| `flag` | string | Yes | `NB` for new business, `RB` for renewal business |
| `filter_by` | string | Yes | `PaidDate` or `ValueDate` |
| `from_date` | string | Yes | Start date (`YYYY-MM-DD`) |
| `to_date` | string | Yes | End date (`YYYY-MM-DD`) |

**Example Request:**
```json
{
  "group_id": 101,
  "flag": "NB",
  "filter_by": "PaidDate",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200):**
```json
[
    {
        "BranchName": "abc",
        "Name": "John Doe",
        "RegisterNo": "R123",
        "PolicyNo": "POL123",
        "GroupId": "G01",
        "SA": 123,
        "Premium": "123.0000",
        "Term": 123,
        "DOC": "23/11/2024",
        "NextDueDate": "23/11/2025",
        "DOB": "23/09/1989",
        "Gender": "M",
        "ValueDate": "2025-02-02T12:32:00.653000",
        "ValueDate_Formatted": "02/02/2025",
        "MaturityDate": "23/11/2036",
        "PaidDate": "2024-11-22T00:00:00",
        "PaidDate_Formatted": "22/11/2024",
        "VoucherNo": "123",
        "RiderID": null,
        "RiderSA": 123,
        "RiderPremium": "0.0000",
        "Status": null,
        "Instalment": null,
        "RiderSA_Renewal": null,
        "Paid Date": null
    }
]
```

| `flag` value | Report Type |
|--------------|-------------|
| `NB` | New Business |
| `RB` | Renewal Business |

| `filter_by` value | Description |
|-------------------|-------------|
| `PaidDate` | Filter records by the date payment was made |
| `ValueDate` | Filter records by the policy value date |

---

## Quick Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login/` | POST | None | Obtain JWT tokens |
| `/auth/refresh/` | POST | None | Refresh access token |
| `/groups/` | GET | JWT | List company groups |
| `/company/policies/` | GET | JWT | List company policies |
| `/company/policies/{id}/` | GET | JWT | Get single policy |
| `/company/policies/statistics/` | POST | JWT | Policy statistics |
| `/policy-search/` | POST | JWT | Search policies |
| `/policy-summary/` | POST | JWT | Policy summary detail |
| `/reports/policy-loans/` | POST | JWT | Policy loan details |
| `/surrender-calculator/` | POST | JWT | Surrender value lookup |
| `/reports/maturity-forecasting/` | POST | JWT | Maturity forecasting report |
| `/reports/loan-repayment/` | POST | JWT | Loan repayment report |
| `/reports/maturity-claim/` | POST | JWT | Maturity claim report |
| `/reports/death-claim/` | POST | JWT | Death claim report |
| `/reports/surrender-claim/` | POST | JWT | Surrender claim report |
| `/reports/group-transfer/` | POST | JWT | Group transfer report |
| `/reports/group-business-detail/` | POST | JWT | New/renewal business report |