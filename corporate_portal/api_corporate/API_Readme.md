# Corporate API Documentation

## Overview

This API allows companies to access their group insurance policies in json format. All endpoints require authentication using JWT tokens.

**Base URL:** `https://xyz.com/api/corporate/`

****
## Authentication

### Login (Obtain JWT Token)

Authenticate and receive a JWT access token for subsequent API calls.

**Endpoint:** `POST /api/corporate/auth/login/`

**Authentication:** None (public endpoint)

**Request Body:**
```json
{
  "username": "your_company_username",
  "password": "your_password"
}
```

**Success Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "username": "company_username"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Account is inactive or not a company account

**Notes:**
- Access token expire every 30 minutes
- Only active company accounts can access the API
- Store the `access` token securely for authenticating subsequent requests
- The access token should be included in the `Authorization` header as: `Bearer <access_token>`

### Refresh Token

When your access token expires, use the refresh token to obtain a new access token without re-authenticating. This token expires after a day.

**Endpoint:** `POST /api/corporate/auth/refresh/`

**Authentication:** None required

**Request Body:**
```json
{
  "refresh": "your_refresh_token"
}
```

**Success Response (200 OK):**
```json
{
  "access": "new_access_token"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired refresh token

**Notes:**
- Refresh tokens are valid for 1 day after generation. Then login is required again.


---

## Company Policies

### Get Company Policies

Retrieve all insurance policies associated with your company's groups.

**Endpoint:** `GET /api/corporate/company/policies/`

**Authentication:** Required (JWT)

**Headers:**
```
Authorization: Bearer <your_access_token>
```

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | Search by name, policy number, mobile, email | `?search=John` |
| `policy_status` | string | Filter by policy status (A=Approved, L=Lapsed, M= Matured, S = Surrendred, I = Acitive, C= Cancel, T = Transfer ) | `?policy_status=A` |
| `gender` | string | Filter by gender (M/F) | `?gender=M` |
| `ordering` | string | Order results | `?ordering=-maturity_date` |

**Success Response (200 OK):**
```json
{
    "count": 1,
    "next": "link_to_next_page",
    "previous": "link_to_previous_page",
    "results": [
        {
            "register_no": "REG123",
            "policy_no": "POL123",
            "branch": "300",
            "group_id": "123",
            "doc": "2021-11-23",
            "term": 17,
            "sum_assured": "84000.0000",
            "premium": "4620.0000",
            "fup": "2025-11-23T00:00:00Z",
            "maturity_date": "2038-11-23",
            "policy_status": "A",
            "policy_type": "MP",
            "late_fine": "0.0000",
            "paid_date": "2024-11-22T00:00:00Z",
            "instalment": 4,
            "paid_amount": "18480.0000",
            "batch_no": "179",
            "details_remarks": "",
            "intrest": null,
            "claim_status": null,
            "late_fine_percent": null,
            "reduced_instalment": null,
            "employee_id": null,
            "name": "SARMILA ADHIKARI",
            "nep_name": null,
            "gender": "F",
            "occupation": "A",
            "dob": "1992-06-29T00:00:00Z",
            "age": "30",
            "extra_premium": "0.0000",
            "total_premium": "13860.0000",
            "id_no": null,
            "id_type": null,
            "appointed_date": "2021-07-22T00:00:00Z",
            "endowment_remarks": null,
            "address": null,
            "email": null,
            "mobile": null,
            "adb": null,
            "previous_policy": null,
            "occ_extra_amount": null,
            "adb_discount": null,
            "father_name": null,
            "mother_name": null,
            "nominee_name": null,
            "nominee_address": null,
            "phone_number_residence": null,
            "transfer_date": null,
            "duplicate_policy_date": null,
            "approved_date": "2021-12-26T14:36:15.670000Z",
            "approved_by": "bindu.sharma",
            "lapse_date": null,
            "lapse_active_date": null,
            "doe": null,
            "approve_remarks": null,
            "modified_date": null,
            "basic_premium": "4620.0000",
            "is_adb": null,
            "after_dis_rebate_rate": "55.0002",
            "fiscal_year": "7879",
            "nominee_relationship": null,
            "claim_date": null,
            "termination_date": null,
            "is_ind_issue": null,
            "province_id": null,
            "district_id": null,
            "municipality_id": null,
            "ward_no": null,
            "age_proof_doc_type": null,
            "age_proof_doc_no": null,
            "nep_address": null,
            "nep_father_name": null,
            "nep_mother_name": null,
            "nep_nominee_name": null,
            "nep_nominee_address": null,
            "nom_district_id": null,
            "nominee_ward_no": null,
            "nominee_phone": null,
            "plan_id": 1,
            "is_multiple_policy_issued": true,
            "terminate_by": null,
            "cancel_date": null,
            "cancel_by": null,
            "active_date": null,
            "active_by": null,
            "terminate_remarks": null,
            "cancel_remarks": null,
            "active_remarks": null,
            "lapse_by": null,
            "lapse_remarks": null
        },
  ]
}
```

---

### Get Policy Statistics

Get aggregate statistics for your company's policies.

**Endpoint:** `GET /api/corporate/company/policies/statistics/`

**Authentication:** Required (JWT)

**Headers:**
```
Authorization: Bearer <your_access_token>
```

**Success Response (200 OK):**
```json
{
  "total_policies": 500,
  "active_policies": 450,
  "lapsed_policies": 30,
  "inactive_policies": 20,
  "total_sum_assured": 500000000.00,
  "total_premium": 12500000.00
}
```

**Example Request:**
```bash
curl -H "Authorization: Bearer <token>" \
  "https://your-domain.com/api/corporate/company/policies/statistics/"
```

---

## Reports

All report endpoints require authentication and automatically filter data based on your company's groups.

### Maturity Forecasting Report

Generate a report of policies maturing within a specified date range.

**Endpoint:** `POST /api/corporate/reports/maturity-forecasting/`

**Authentication:** Required (JWT)

**Headers:**
```
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "group_id": "GRP001",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
}
```

**Parameters:**
- `group_id` (required): Your group ID
- `from_date` (required): Start date (YYYY-MM-DD)
- `to_date` (required): End date (YYYY-MM-DD)

**Success Response (200 OK):**
```json
{
  "success": true,
  "count": 25,
  "group_id": "GRP001",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "date_type": "ad",
  "policies": [
    {"SN":1,
    "PolicyNo":"POL123",
    "Branch":"300",
    "Name":"Ram Krshna Shah",
    "NepName":null,
    "GroupId":"GP123",
    "DOB":"10/05/1999",
    "DOC":"23/11/2000",
    "SumAssured":"2706732.0000",
    "Term":20,
    "Instalment":20,
    "Premium":"391132.6100",
    "MaturityDate":"23/11/2025",
    "TotalPolicy":14,
    "RemainingDayToMature":-113,
    "PolicyStatus":"A"},
  ]
}
```

---

### Death Claim Report

Generate a report of death claims for a specified period.

**Endpoint:** `POST /api/corporate/reports/death-claim/`

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "group_id": "GRP001",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200 OK):**
```json
[
  {
    "GroupId":"GP123",
    "PolicyNo":"POL123",
    "EmployeeId":null,
    "Name":"Ram Krishna",
    "NepName":null,
    "DOB":"17/05/1999",
    "SA":"1124928.0000",
    "Premium":"144898.7000",
    "DOC":"23/11/2012",
    "MaturityDate":"23/11/2026",
    "Bonus":"504491.5200",
    "ClaimAmount":"1629420.0000",
    "LoanAmount":"0.0000",
    "InterestOnLoanAmount":"0.0000",
    "TotalClaimAmount":"1629419.5200",
    "NetClaimAmount":"1629419.5200",
    "DeathDate":"30/10/2023",
    "IntimationDate":"27/12/2023",
    "TerminationDate":"30/10/2023",
    "VoucherNo":"DP30080810000202",
    "ClaimId":"D-80810000032",
    "Instalment":11
  }
]
```

---

### Maturity Claim Report

Generate a report of maturity claims for a specified period.

**Endpoint:** `POST /api/corporate/reports/maturity-claim/`

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "group_id": "GRP001",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200 OK):**
```json
[
  {
    "GroupId":"GP123",
    "PolicyNo":"POL123",
    "EmployeeId":null,
    "Name":"Ram Krishna",
    "NepName":null,
    "DOB":"27/06/1999",
    "SA":"2269680.0000",
    "Premium":"531500.3200",
    "DOC":"23/11/2004",
    "MaturityDate":"23/11/2021",
    "Bonus":"1134822.0000",
    "TotalTax":"52378.0000",
    "ClaimAmount":"3404502.0000",
    "LoanAmount":"0.0000",
    "CalculatedInterest":"0.0000",
    "NetClaimAmount":"3352124.0000",
    "ClaimDate":"05/12/2021",
    "VoucherNo":"MP300787900000181",
    "ClaimId":"CM123"
  }
]
```

---

### Surrender Claim Report

Generate a report of surrender claims for a specified period.

**Endpoint:** `POST /api/corporate/reports/surrender-claim/`

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "group_id": "GRP001",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

**Success Response (200 OK):**
```json
[
  {
    "SNo":1,
    "GroupId":"052",
    "PolicyNo":"05211586",
    "EmployeeId":null,
    "Name":"LAL BAHADUR CHAND",
    "NepName":null,
    "DOB":"28/11/1967",
    "DOC":"23/11/2012",
    "SA":"1124928.0000",
    "Premium":"170707.7700",
    "Term":"13",
    "MaturityDate":"23/11/2025",
    "SurrenderAmount":"1680142.0000",
    "SurrenderDate":"29/12/2024",
    "IntimationDate":"11/05/2025",
    "VoucherNo":"SP30081820011636",
    "Tax":"25032.0000",
    "LoanAmount":"1512128.0000",
    "LoanInterest":"0.0000",
    "NetPayable":"1655110.0000",
    "ClaimId":"GS-30081820001154",
    "Instalment":13
  }
]
```

---

## Group Information

### Get Group Information

Retrieve information about insurance groups.

**Endpoint:** `GET /api/corporate/groups/`

**Authentication:** Required to view groups belonging to company

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `group_id` | string | Filter by group ID |
| `is_active` | boolean | Filter by active status |
| `search` | string | Search by group name |

**Success Response (200 OK):**
```json
{
  "count":3,
  "group_ids":["052","179","GE1016"],
  "results":[
    {"group_id":"052",
    "group_name":"NEPAL ELECTRICITY AUTHORITY",
    "group_name_nepali":"नेपाल विद्युत प्राधिकरण",
    "is_active":true,
    "total_members_count":102792,
    "total_active_policies":2695,
    "total_premium":"1762643679.7100",
    "total_sa":"9137321448.0000",
    "death_claim":766,
    "surrender_claim":1334,
    "maturity_claim":7146,
    "transfer_claim":30,
    "terminate_claim":51,
    "cancel_claim":49
    }
  ]
}
```

---

## Error Codes

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad Request - Missing required parameters or invalid data |
| 401 | Unauthorized - Invalid or missing authentication token |
| 403 | Forbidden - You don't have permission to access this resource |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Something went wrong on our end |


---

## Rate Limiting

- API requests are rate-limited to ensure fair usage
- Contact support if you need higher rate limits

---

## Best Practices

1. **Store tokens securely** - Never expose JWT tokens in client-side code
2. **Handle token expiration** - Implement token refresh logic
3. **Use pagination** - For large datasets, use the pagination parameters
4. **Filter at the API level** - Use query parameters to reduce data transfer

---

## Support

For technical support or questions about the API:
- **Email:** support@yourcompany.com
- **Documentation:** https://docs.yourcompany.com
- **Status Page:** https://status.yourcompany.com

---

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- Company policies endpoint
- Report generation endpoints
- Group information endpoint