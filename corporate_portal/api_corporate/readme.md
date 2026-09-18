# Corporate Portal API

REST API for server-to-server access to corporate group insurance data.

## Base URL

Production:

```text
https://api.rbs.gov.np:3000/api/corporate
```


## Authentication

### Provisioning an API key

There is no public login or token endpoint. A portal superuser issues the key from Django admin:

1. Open **Admin > Companies**.
2. Select exactly one company.
3. Choose **Generate API key**.
4. Copy the key immediately. It is displayed only once.

The company must have an approved primary `CompanyAccount`. Generating a new key revokes the previous key. Only a SHA-256 hash of the key is stored by the server.

### Request headers

Send the raw key on every request:

```http
X-API-Key: copo_<64 hexadecimal characters>
```

For JSON requests also send:

```http
Content-Type: application/json
```

Do not use `Authorization: Bearer ...`; JWT login and refresh endpoints are not enabled in the current API.

## Access rules

- A company can access only its own active, non-deleted groups and related policies.
- Group-based reports reject groups belonging to another company with `403`.
- Staff and superusers may access broader data and may use `company_id` where documented.
- An inactive company or inactive primary account cannot authenticate.
- Dates use `YYYY-MM-DD` unless noted otherwise.
- Response dates and datetimes are returned as JSON strings, generally in ISO 8601 format.


## Endpoints

### Groups and dashboards

#### List groups

```http
GET /groups/
```

Request body: none.

Optional staff/superuser query parameter:

```text
/groups/?company_id=1
```

Response:

```json
{
  "count": 2,
  "group_ids": ["052", "071"],
  "results": []
}
```

#### Company dashboard data

```http
GET /endowments/by_company/?company_id=1
```

Request body: none.

Regular company users may provide only their own company ID. Staff and superusers may provide another company ID.

Response fields:

```json
{
  "company_id": 1,
  "group_ids": ["052"],
  "summary": {},
  "latest_policies": [],
  "fup_data": []
}
```

### Policy and endowment lists

#### List company policies

```http
GET /company/policies/
```

Optional query parameters:

```text
page
search
policy_status
fiscal_year
gender
policy_type
is_adb
employee_id
claim_status
ordering
```

Response is paginated:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

#### Company policy statistics

```http
POST /company/policies/statistics/
```

```json
{}
```

#### List endowments

```http
GET /endowments/
```

Optional query parameters:

```text
page
search
group_id
policy_status
fiscal_year
gender
policy_type
is_adb
register_no
employee_id
claim_status
ordering
```

Response is paginated with `count`, `next`, `previous`, and `results`.

### Policy requests

#### Search policies

```http
POST /policy-search/
```

```json
{
  "q": "LAXMI"
}
```

Returns an array of matching `{ "policyNo": ..., "name": ..., "employeeid": ... }` objects. A blank `q` returns `[]`.

#### Policy detail

```http
POST /policy-detail/
```

```json
{
  "policy_no": "05208090"
}
```

Response:

```json
{
  "success": true,
  "policy_no": "05208090",
  "summary": [],
  "loans": []
}
```

#### Policy summary

```http
POST /policy-summary/
```

```json
{
  "policy_no": "05208090"
}
```

Returns a JSON array of policy summary records.

#### Policy loans

```http
POST /reports/policy-loans/
```

```json
{
  "policy_no": "05208090"
}
```

Returns a JSON array of loan records.

#### Surrender calculator

```http
POST /surrender-calculator/
```

```json
{
  "policy_no": "05208090",
  "claim_date": "2024-06-01"
}
```

`claim_date` is optional. The response is one surrender-result object.

### Group reports

#### Maturity forecasting

```http
POST /reports/maturity-forecasting/
```

```json
{
  "group_id": "052",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "date_type": "ad"
}
```

`date_type` is optional and defaults to `ad`.

#### Loan repayment

```http
POST /reports/loan-repayment/
```

```json
{
  "group_id": "052",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "date_type": "ad"
}
```

`date_type` is optional and defaults to `ad`.

#### Group transfer

```http
POST /reports/group-transfer/
```

```json
{
  "group_id": "052",
  "transfer_date_from": "2024-01-01",
  "transfer_date_to": "2024-12-31",
  "date_type": "ad"
}
```

`date_type` is optional and defaults to `ad`.

#### Group business detail

```http
POST /reports/group-business-detail/
```

```json
{
  "group_id": "052",
  "flag": "NB",
  "filter_by": "PaidDate",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

Valid values:

- `flag`: `NB` (new business) or `RB` (renewal business)
- `filter_by`: `PaidDate` or `ValueDate`

Returns a JSON array.

#### Death claims

```http
POST /reports/death-claim/
```

```json
{
  "group_id": "052",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

Returns a JSON array.

#### Maturity claims

```http
POST /reports/maturity-claim/
```

```json
{
  "group_id": "052",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

Returns a JSON array.

#### Surrender claims

```http
POST /reports/surrender-claim/
```

```json
{
  "group_id": "052",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

Returns a JSON array.

## Status codes and errors

Authentication failures from API-key validation normally return `401`:

```json
{
  "detail": "Invalid or revoked API key."
}
```

Common application responses:

| Status | Meaning |
|---|---|
| `200` | Request succeeded; no records may be represented by an empty array or result set |
| `400` | Missing or invalid request parameters |
| `401` | Missing, invalid, or revoked API key |
| `403` | Inactive company or access to another company’s data |
| `404` | Requested policy/result not found, depending on endpoint |
| `500` | Server or reporting error |

Most application errors use this shape:

```json
{
  "error": "Human-readable error message"
}
```

## Testing with cURL

```bash
curl -i \
  -H "X-API-Key: copo_your_key_here" \
  "https://api.rbs.gov.np/api/corporate/groups/"
```

```bash
curl -i -X POST \
  -H "X-API-Key: copo_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"group_id":"052","from_date":"2024-01-01","to_date":"2024-12-31"}' \
  "https://api.rbs.gov.np/api/corporate/reports/death-claim/"
```

For key provisioning or revocation, contact a portal superuser.
