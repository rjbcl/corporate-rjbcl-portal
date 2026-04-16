## Main System (Portal Database - PostgreSQL)

### models.py

**Core Models:**

- **AuditBase (Abstract)**  
  - Common base model providing audit trail functionality
  - Fields: `created_by`, `modified_by`, `created_at`, `modified_at`
  - Inherited by all main models for tracking changes

- **Account (Custom User Model)**  
  - Custom authentication model extending `AbstractBaseUser` and `PermissionsMixin`
  - Primary key: `username` (CharField, unique)
  - Fields: `is_active`, `is_staff`, `is_superuser`, `groups`, `user_permissions`
  - **User Types:**
    - `admin` - Superuser with unrestricted access
    - `staff` - Staff members with role-based permissions (Viewer, Editor, Approver, Admin)
    - `company` - Company account users (linked to Company model)
    - `individual` - Individual policy holders (linked to Individual model)
  - **Key Methods:**
    - `get_user_type()` - Returns user classification based on linked profile
    - `get_display_name()` - Returns appropriate display name (company/individual name or username)
  - **Manager:** `AccountManager` with `create_user()` and `create_superuser()` methods

- **Company**  
  - One-to-one relationship with `Account` via `username` field
  - Primary key: `company_id` (AutoField)
  - Key fields: `company_name`, `nepali_name`, `email`, `phone_number`, `telephone_number`, `isactive`
  - Stores organization details for group insurance policies
  - **Business Rules:**
    - When `isactive=False`, all related groups are automatically deactivated
    - Deleting a company cascades to delete all related groups and the linked account

- **Group**  
  - Belongs to a `Company` (ForeignKey)
  - Primary key: `row_id` (AutoField)
  - Unique constraint: `group_id` (synced from external insurance system)
  - Key fields: `group_name`, `isactive`, `isdeleted`
  - Represents insurance groups/departments within a company
  - **Business Rules:**
    - Each group can only be assigned to one company at a time
    - Groups are loaded from external API and cached locally
    - Soft deletion via `isdeleted` flag instead of hard delete

- **Individual**  
  - One-to-one relationship with `Account` via `username` field
  - Belongs to a `Group` (ForeignKey)
  - Primary key: `user_id` (AutoField)
  - Key fields: `user_full_name`
  - Represents individual policy holders within a group
  - **Business Rules:**
    - Must belong to an active group
    - Deleting an individual also deletes the linked account

- **AuditLog**  
  - Tracks all system actions for security and compliance
  - Fields: `action`, `target_username`, `target_type`, `performed_by`, `timestamp`, `details`, `ip_address`
  - **Actions Logged:**
    - `password_reset`, `role_change`, `soft_delete`, `hard_delete`, `create`, `update`, `login`, `login_failed`, `logout`, `permission_change`
  - **Auto-cleanup:** Maintains maximum of 20 most recent logs (oldest automatically deleted)
  - Creates immutable audit trail via `create_log()` class method

---

### services.py

**Service Layer Pattern - Encapsulates business logic and enforces permissions**

- **PermissionMixin**
  - Base mixin providing `check_permission()` method
  - Validates user permissions before allowing operations
  - Raises `PermissionDenied` exception if unauthorized

- **CompanyService**
  - **Methods:**
    - `validate_group_availability()` - Ensures groups aren't assigned to multiple companies
    - `create_company()` - Creates company + account + groups in single transaction
    - `update_company()` - Updates company details, account credentials, and group assignments
    - `soft_delete_company()` - Deactivates company and cascades to groups
    - `hard_delete_company()` - Permanently deletes company (superuser only)
    - `approve_company()` - Reactivates soft-deleted company
  - **Business Rules Enforced:**
    - Groups cannot be assigned to multiple companies
    - Username must be unique across all accounts
    - Inactive company → all groups automatically inactive
    - All operations create audit logs
    - Uses `@transaction.atomic` for data integrity

- **IndividualService**
  - **Methods:**
    - `create_individual()` - Creates individual + account in single transaction
    - `update_individual()` - Updates individual details and account credentials
    - `soft_delete_individual()` - Deactivates individual account
    - `hard_delete_individual()` - Permanently deletes individual (superuser only)
    - `approve_individual()` - Reactivates soft-deleted individual
  - **Business Rules Enforced:**
    - Must belong to an active group
    - All operations create audit logs
    - Password changes are tracked separately

- **AccountService**
  - **Methods:**
    - `can_modify_account()` - Checks if user has permission to modify target account
    - `reset_password()` - Resets password with permission check and audit logging
  - **Permission Rules:**
    - Users cannot modify their own accounts via service
    - Editors cannot modify staff accounts
    - Admins cannot modify superuser accounts

---

### admin.py

**Django Admin Customization with Role-Based Access Control**

- **CompanyAdminForm**
  - Custom form for Company model
  - **Features:**
    - Loads group choices from external API via `GroupAPIService`
    - Select2 widget for searchable multi-select group assignment
    - Validates username uniqueness and group availability
    - Optional username/password change on edit
  - **Validation:**
    - Prevents duplicate group assignments across companies
    - Requires username and password for new companies
    - Allows blank username/password on edit to keep current values
  - **Integration:**
    - Delegates all business logic to `CompanyService`
    - Passes request user for permission checks and audit logging

- **IndividualAdminForm**
  - Custom form for Individual model
  - Same username/password validation pattern as CompanyAdminForm
  - Delegates to `IndividualService` for all operations
  - Autocomplete for group selection using Django's built-in autocomplete

- **AccountAdmin**
  - Extends Django's `UserAdmin` for custom Account model
  - **Custom Features:**
    - Displays user type (admin/staff/company/individual) in list view
    - Shows assigned staff roles (groups) for staff users
    - Password reset action for bulk operations
    - Prevents staff role assignment to company/individual accounts
  - **Permission-Based Behavior:**
    - **Superuser:** Full access to all accounts
    - **Admin:** Can manage all except superusers, can create staff accounts
    - **Editor:** Can view all, edit company/individual only (staff accounts readonly)
    - **Viewer/Approver:** Can only view their own account
  - **Audit Integration:**
    - Logs password changes, role changes, permission changes
    - Tracks account creation and deletion
    - Records IP addresses for security

- **CompanyAdmin**
  - **Features:**
    - List view with username, company name, and active status
    - Search by company name
    - Filter by active status
    - Soft delete action (bulk operation)
  - **Permission-Based Behavior:**
    - **Superuser:** Full CRUD access
    - **Admin/Editor:** Can create, view, edit, soft delete
    - **Viewer/Approver:** Read-only access (all fields disabled)
  - **UI Customization:**
    - Select2 CSS/JS loaded via CDN
    - Readonly fields for Viewer/Approver roles
    - Custom change view hides Save buttons for read-only users

- **IndividualAdmin**
  - Similar structure to CompanyAdmin
  - Additional display: Shows company name and group name in list view
  - Autocomplete for group selection
  - Password reset action for individuals

- **GroupAdmin**
  - **Features:**
    - Manual refresh cache button (Admin/Superuser only)
    - Displays company assignment, active status, deleted status
    - Soft delete action
  - **Integration:**
    - Refresh button calls `GroupAPIService.refresh_cache()`
    - Syncs with external insurance API

- **AuditLogAdmin**
  - **Access Control:**
    - Only Admin and Superuser can view
    - No add permission (logs created automatically)
    - Only Superuser can delete
    - All fields readonly
  - **Features:**
    - List view with timestamp, action, target, performer
    - Filter by action type and timestamp
    - Search by username and details

**Custom Admin Features:**
- `@staff_member_required` decorator for cache refresh view
- Role-based fieldset customization
- Custom actions with permission checks
- Audit logging for all admin operations
- Prevention of privilege escalation (non-superusers cannot create superusers)

---

### Key Features (Main System)

- **Separation of Concerns**  
  - Forms: UI validation and field rendering
  - Services: Business logic and permission enforcement
  - Admin: Django admin customization and role-based access

- **Data Integrity**  
  - Each group can belong to only one company
  - Username uniqueness enforced across all user types
  - Transactional operations with `@transaction.atomic`
  - Soft deletion preserves data for audit purposes

- **Cascading Rules**  
  - Inactive company → all related groups automatically inactive
  - Deleting company → cascades to groups and account
  - Group changes tracked with old/new values for audit

- **Security & Compliance**  
  - All operations logged in AuditLog with performer, timestamp, and IP
  - Role-based permissions enforced at service layer
  - Password changes tracked separately
  - Permission escalation prevented (Editors can't promote to staff)

- **External API Integration**  
  - Groups loaded from external insurance system API
  - Cached locally with manual refresh capability
  - Handles API failures gracefully with fallback

---

## API System (External Database - MSSQL)

### models.py

**Read-Only Models Mapping to External Insurance Database**

- **GroupInformation**
  - Maps to `tblGroupInformation` table in external MSSQL database
  - Primary key: `row_id` (BigAutoField)
  - Unique identifier: `group_id` (used for linking with portal)
  - **Key Fields:**
    - `group_name`, `group_name_nepali` - Group names in English and Nepali
    - `fiscal_year` - Insurance period
    - `discount_rate`, `adb_discount_rate` - Pricing information
    - `master_policy_no` - Master policy number
    - `is_active` - Active status
    - `account_number` - Company account reference
    - `retirement_age`, `min_age`, `max_age` - Policy eligibility criteria
    - `min_term`, `max_term` - Coverage period limits
  - **Meta:**
    - `managed = False` - Django won't create/modify this table
    - `db_table = 'tblGroupInformation'` - Exact table name in external DB
    - Uses `.using('company_external')` for all queries

- **GroupEndowment**
  - Maps to `view_copo_groupEndowment` VIEW (not a table)
  - **Composite Primary Key:** `register_no` + `policy_no`
  - **View Purpose:** Combines two tables with data prioritization:
    - `tblGroupEndowmentDetails` - More reliable/updated payment and status data
    - `tblGroupEndowment` - Detailed personal and policy information
  
  - **Fields from Details Table (Prioritized):**
    - `premium`, `sum_assured`, `total_premium` - Financial information
    - `maturity_date`, `doc` (Date of Commencement) - Important dates
    - `policy_status`, `policy_type` - Current status
    - `paid_date`, `paid_amount`, `instalment` - Payment tracking
    - `claim_status`, `late_fine`, `late_fine_percent` - Claim information
  
  - **Fields from Endowment Table (Detailed Info):**
    - Personal: `name`, `nep_name`, `gender`, `dob`, `age`, `occupation`
    - Contact: `email`, `mobile`, `address`, `phone_number_residence`
    - Family: `father_name`, `mother_name`, `nominee_name`, `nominee_relationship`
    - Location: `province_id`, `district_id`, `municipality_id`, `ward_no`
    - Documents: `id_type`, `id_no`, `age_proof_doc_type`, `age_proof_doc_no`
    - Policy Details: `employee_id`, `appointed_date`, `previous_policy`
    - Status History: `approved_date`, `lapse_date`, `termination_date`, `cancel_date`
  
  - **Meta:**
    - `managed = False` - Read-only, no migrations
    - `db_table = 'view_copo_groupEndowment'` - Points to SQL view
    - `unique_together = [['register_no', 'policy_no']]` - Composite key
    - Default ordering: `-maturity_date` (newest first)

---

### serializers.py

**DRF Serializers for API Response Formatting**

- **CustomTokenObtainPairSerializer**
  - Extends `TokenObtainPairSerializer` from `rest_framework_simplejwt`
  - **Purpose:** Customize JWT login response with additional user information
  - **Validation:**
    - Authenticates username and password
    - Checks if user is active
    - Verifies user type is 'company' or 'individual' (blocks staff from API)
  - **Response Data:**
    - `access` - JWT access token (30 min expiry)
    - `refresh` - JWT refresh token (1 day expiry)
    - `user_type` - 'company' or 'individual'
    - `username` - Account username
    - **For Company Users:**
      - `company_id`, `company_name`, `is_active`
    - **For Individual Users:**
      - `user_id`, `user_full_name`, `group_id`
  - **Security:**
    - Only allows company and individual accounts
    - Returns 403 for inactive accounts
    - Returns 403 for staff/admin accounts

- **GroupInformationSerializer**
  - ModelSerializer for `GroupInformation` model
  - **Fields:** All model fields (37 fields total)
  - **Read-Only:** All fields marked as read-only (no POST/PUT/PATCH)
  - **Use Cases:**
    - Fetch group details for company dashboards
    - Display group information in policy views
    - Filter and search group metadata

- **GroupEndowmentSerializer**
  - ModelSerializer for `GroupEndowment` model
  - **Fields:** `'__all__'` - All 90+ fields from the view
  - **Read-Only:** All fields (external database is read-only)
  - **Use Cases:**
    - Display policy details to companies
    - Show individual policy information
    - Generate reports and statistics

---

### views.py

**API Endpoints with Authentication and Permission Control**

- **CustomTokenObtainPairView**
  - Extends `TokenObtainPairView` from `rest_framework_simplejwt`
  - **Endpoint:** `POST /api/corporate/auth/login/`
  - **Permission:** `AllowAny` (public login endpoint)
  - **Process:**
    1. Validates username and password
    2. Checks user type (must be 'company' or 'individual')
    3. Verifies account is active
    4. Returns JWT token with user information
  - **Error Responses:**
    - 401: Invalid credentials
    - 403: Staff accounts not allowed / Inactive account
  - **Example Request:**
```json
    {
        "username": "nea_user",
        "password": "secure123"
    }
```
  - **Example Response:**
```json
    {
        "access": "eyJ0eXAi...",
        "refresh": "eyJ0eXAi...",
        "user_type": "company",
        "company_id": 5,
        "company_name": "Nepal Electricity Authority"
    }
```

- **CompanyPoliciesViewSet** (ReadOnlyModelViewSet)
  - **Endpoint:** `/api/corporate/company/policies/`
  - **Permission:** `IsAuthenticated` + `IsCompanyUser`
  - **Auto-Filtering:** Automatically filters to show only logged-in company's policies
  - **Process:**
    1. Gets authenticated company from `request.user.company_profile`
    2. Finds all groups belonging to this company (from portal DB)
    3. Queries external DB for policies in those groups
    4. Returns only this company's employee policies
  - **Available Actions:**
    - `GET /policies/` - List all policies (paginated, 100 per page)
    - `GET /policies/{register_no}/` - Get specific policy
    - `GET /policies/statistics/` - Get company statistics
  - **Filtering:**
    - `?policy_status=A` - Filter by status (A=Active, L=Lapsed)
    - `?fiscal_year=2023-24` - Filter by fiscal year
    - `?gender=Male` - Filter by gender
    - `?search=Ram` - Search by name, policy number, employee ID
    - `?ordering=-premium` - Sort by premium (descending)
  - **Statistics Endpoint:**
```json
    {
        "total_policies": 150,
        "active_policies": 120,
        "lapsed_policies": 20,
        "inactive_policies": 10,
        "total_sum_assured": 75000000.00,
        "total_premium": 750000.00
    }
```

- **IndividualPoliciesViewSet** (ReadOnlyModelViewSet)
  - **Endpoint:** `/api/corporate/individual/policies/`
  - **Permission:** `IsAuthenticated` + `IsIndividualUser`
  - **Auto-Filtering:** Returns only the logged-in individual's own policy
  - **Process:**
    1. Gets authenticated individual from `request.user.individual_profile`
    2. Finds their group_id
    3. Queries external DB for policies matching their employee_id
    4. Returns only their own policy data
  - **Security:** Individuals cannot see other employees' policies

- **GroupInformationViewSet** (ReadOnlyModelViewSet)
  - **Endpoint:** `/api/corporate/groups/`
  - **Permission:** `IsAuthenticated` (default)
  - **Purpose:** Fetch group metadata from external database
  - **Filtering:**
    - `?group_id=NEA001` - Exact group ID match
    - `?fiscal_year=2023-24` - Filter by fiscal year
    - `?is_active=true` - Filter by active status
    - `?search=Nepal` - Search group names
  - **Use Cases:**
    - Display group details in company dashboards
    - Validate group information
    - Show group metadata alongside policies

- **GroupEndowmentViewSet** (ReadOnlyModelViewSet)
  - **Endpoint:** `/api/corporate/endowments/`
  - **Permission:** `IsAuthenticated` (default)
  - **Purpose:** General access to endowment/policy data
  - **Custom Actions:**
    - `@action by_company` - Get all policies for a specific company
  - **by_company Endpoint:**
    - **URL:** `GET /api/corporate/endowments/by_company/?company_id=5`
    - **Process:**
      1. Validates company_id parameter
      2. Finds all groups for that company (from portal DB)
      3. Fetches all policies for those groups (from external DB)
      4. Returns complete dataset
    - **Response:**
```json
      {
          "company_id": 5,
          "group_ids": ["NEA001", "NEA002"],
          "count": 150,
          "endowments": [...]
      }
```
  - **Filtering & Search:**
    - 8 filter fields: group_id, policy_status, fiscal_year, gender, etc.
    - 7 search fields: name, policy_no, employee_id, mobile, etc.
    - 5 ordering fields: maturity_date, doc, name, premium, sum_assured

- **company_policies_web** (Function-Based View)
  - **Endpoint:** `GET /api/corporate/endowments/by_company/`
  - **Permission:** `IsAuthenticated` (Session-based for web dashboard)
  - **Purpose:** Same as CompanyPoliciesViewSet.by_company but for web interface
  - **Security Check:**
    - Non-superusers can only access their own company's data
    - Validates `company_id` parameter matches logged-in user's company
  - **Returns:** Same structure as by_company action

---

### permissions.py

**Custom Permission Classes for Role-Based Access**

- **IsCompanyUser**
  - Extends `BasePermission`
  - **Check:** `user.get_user_type() == 'company'`
  - **Usage:** Applied to `CompanyPoliciesViewSet`
  - **Effect:** Only users with linked Company profile can access
  - **Error Message:** "Only company accounts can access this resource."

- **IsIndividualUser**
  - Extends `BasePermission`
  - **Check:** `user.get_user_type() == 'individual'`
  - **Usage:** Applied to `IndividualPoliciesViewSet`
  - **Effect:** Only users with linked Individual profile can access
  - **Error Message:** "Only individual accounts can access this resource."

**Permission Flow:**
1. Django checks `IsAuthenticated` first (JWT or Session)
2. Custom permission checks user type
3. ViewSet's `get_queryset()` further filters data based on user's company/group
4. Result: Multi-layer security ensuring users only see their own data

---

### urls.py

**API URL Routing with Django REST Framework Router**
```python
router = DefaultRouter()
router.register(r'groups', GroupInformationViewSet, basename='group')
router.register(r'endowments', GroupEndowmentViewSet, basename='endowment')
router.register(r'company/policies', CompanyPoliciesViewSet, basename='company-policies')
router.register(r'individual/policies', IndividualPoliciesViewSet, basename='individual-policies')
```

**Registered URLs:**
- `/api/corporate/groups/` - Group metadata (list, detail)
- `/api/corporate/endowments/` - All policies (with by_company action)
- `/api/corporate/company/policies/` - Company's policies only (auto-filtered)
- `/api/corporate/individual/policies/` - Individual's policy only (auto-filtered)

**Authentication URLs:**
- `POST /api/corporate/auth/login/` - JWT token obtain
- `POST /api/corporate/auth/refresh/` - JWT token refresh

**Web Dashboard URL:**
- `GET /api/corporate/endowments/by_company/` - Session-authenticated endpoint

---

### settings.py (API-Related Configuration)

**Database Configuration:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # Portal database (accounts, companies, groups)
    },
    'company_external': {
        'ENGINE': 'mssql',
        # External insurance database (policies, payments)
    }
}
```

**REST Framework Settings:**
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # For mobile/API
        'rest_framework.authentication.SessionAuthentication',        # For web dashboard
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # All endpoints require auth
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,  # Return 100 records per page by default
}
```

**JWT Configuration:**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),   # Token expires in 30 minutes
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),      # Refresh token lasts 1 day
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**Caching (for Group API):**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 86400,  # Cache groups for 24 hours
    }
}
```

---

### Key Features (API System)

- **Dual Database Architecture**  
  - Portal DB (PostgreSQL): User accounts, companies, group assignments
  - External DB (MSSQL): Insurance policies, payments, claims
  - Seamless cross-database queries with `.using('company_external')`

- **Read-Only External Access**  
  - All external DB models are unmanaged (`managed = False`)
  - No migrations run against external database
  - Data integrity maintained by insurance system

- **Smart Data Prioritization**  
  - Uses SQL view to combine two tables
  - Prioritizes `tblGroupEndowmentDetails` for critical fields (premium, dates, status)
  - Enriches with detailed info from `tblGroupEndowment` (personal, contact, family)

- **Multi-Layer Security**  
  - JWT authentication for API access
  - Session authentication for web dashboard
  - Custom permission classes (IsCompanyUser, IsIndividualUser)
  - Automatic data filtering based on user type
  - Companies see only their groups' policies
  - Individuals see only their own policy

- **Flexible Filtering & Search**  
  - Django Filter Backend for exact matches
  - Search across multiple fields (name, policy number, employee ID)
  - Ordering by any field (premium, dates, names)
  - Pagination (100 records per page)

- **RESTful API Design**  
  - Standard CRUD operations (Read-only: List, Retrieve)
  - Custom actions (statistics, by_company)
  - Consistent response format
  - Proper HTTP status codes

- **Performance Optimization**  
  - Database views for complex joins
  - Indexed composite primary keys
  - Cached group data (24-hour TTL)
  - Optimized queries with `.select_related()` and `.prefetch_related()`

---

## Complete Data Flow Example

### Scenario: Company User Logs In and Views Policies

1. **Login (JWT Authentication):**
```bash
   POST /api/corporate/auth/login/
   {
       "username": "nea_admin",
       "password": "secure123"
   }
```
   - `CustomTokenObtainPairView` handles request
   - Authenticates against `Account` model in portal DB
   - Validates user type is 'company'
   - Fetches company info from `Company` model
   - Returns JWT token + company details

2. **View Policies (Auto-Filtered):**
```bash
   GET /api/corporate/company/policies/
   Authorization: Bearer eyJ0eXAi...
```
   - `CompanyPoliciesViewSet` receives request
   - `JWTAuthentication` validates token
   - `IsCompanyUser` permission checks user type
   - `get_queryset()` method:
     - Gets `company_profile` from `request.user`
     - Queries portal DB: `Group.objects.filter(company_id=company)`
     - Extracts `group_ids` list
     - Queries external DB: `GroupEndowment.objects.using('company_external').filter(group_id__in=group_ids)`
   - Returns paginated results (100 per page)

3. **Get Statistics:**
```bash
   GET /api/corporate/company/policies/statistics/
   Authorization: Bearer eyJ0eXAi...
```
   - Uses same queryset as above
   - Calculates aggregates in Python:
     - `count()` for total policies
     - Filters for active/lapsed counts
     - Sums premium and sum_assured
   - Returns JSON with statistics

4. **Search for Employee:**
```bash
   GET /api/corporate/company/policies/?search=Ram&policy_status=A
   Authorization: Bearer eyJ0eXAi...
```
   - Same filtering as #2
   - Additional filters applied:
     - `SearchFilter` on name/policy_no/employee_id
     - `DjangoFilterBackend` for policy_status
   - Returns matching policies only

---

## Security Mechanisms

### Authentication Layers
1. **JWT for API:** Stateless, token-based, mobile-friendly
2. **Session for Web:** Cookie-based, Django's built-in auth
3. **Dual Support:** Both methods work simultaneously

### Authorization Layers
1. **User Type Check:** Company vs Individual vs Staff
2. **Custom Permissions:** IsCompanyUser, IsIndividualUser
3. **Queryset Filtering:** Auto-filter by company or group
4. **Service Layer:** Permission checks before any operation

### Data Isolation
1. **Company Users:** See only their groups' policies
2. **Individual Users:** See only their own policy
3. **Staff Users:** Blocked from API (admin interface only)
4. **Cross-Company Protection:** Cannot access other companies' data

### Audit & Compliance
1. **All Operations Logged:** Create, update, delete, password reset
2. **Immutable Logs:** Cannot be edited, only viewed/deleted by superuser
3. **Auto-Rotation:** Maintains last 20 logs
4. **IP Tracking:** Records source IP for security analysis

---

## Error Handling

### Common API Errors

**401 Unauthorized:**
- Missing or invalid JWT token
- Expired access token (> 30 minutes)
- Invalid credentials on login

**403 Forbidden:**
- Staff account attempting API access
- Inactive company/individual account
- Company trying to access another company's data
- Missing required permissions

**404 Not Found:**
- Policy with given register_no doesn't exist
- Group ID not found
- Company ID not found

**400 Bad Request:**
- Missing required parameter (e.g., company_id)
- Invalid parameter format (e.g., company_id must be integer)
- Invalid filter values

**500 Internal Server Error:**
- External database connection failure
- Unexpected query error
- Service layer exception

---

## API Response Formats

### List Response (Paginated):
```json
{
    "count": 150,
    "next": "http://api.com/policies/?page=2",
    "previous": null,
    "results": [
        {
            "register_no": "REG001",
            "policy_no": "POL001",
            "name": "Ram Sharma",
            "premium": 5000.00,
            ...
        }
    ]
}
```

### Detail Response:
```json
{
    "register_no": "REG001",
    "policy_no": "POL001",
    "name": "Ram Sharma",
    "group_id": "NEA001",
    "premium": 5000.00,
    "sum_assured": 500000.00,
    "policy_status": "A",
    ...
}
```

### Error Response:
```json
{
    "error": "company_id parameter is required",
    "example": "/api/corporate/endowments/by_company/?company_id=1"
}
```

---

## Future Enhancements

### Planned Features
- [ ] Real-time notifications for policy updates
- [ ] Bulk policy upload API
- [ ] Policy document download endpoint
- [ ] Payment history tracking
- [ ] Claim submission API
- [ ] Mobile app push notifications
- [ ] GraphQL API alternative
- [ ] WebSocket support for live updates
- [ ] Advanced analytics and reporting
- [ ] Data export in multiple formats (CSV, PDF, Excel)

### Performance Optimizations
- [ ] Redis caching for frequently accessed data
- [ ] Database query optimization with indexes
- [ ] Asynchronous task processing with Celery
- [ ] CDN for static assets
- [ ] Database connection pooling
- [ ] Query result caching

### Security Enhancements

 - [ ] Two-factor authentication (2FA)
 - [ ] API rate limiting per user
 - [ ] IP whitelisting for sensitive operations
 - [ ] Encrypted field storage for PII
 - [ ] GDPR compliance features
 - [ ] Security audit logging improvements