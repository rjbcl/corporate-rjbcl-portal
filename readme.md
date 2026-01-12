# Backend Overview

## models.py

- **AuditBase**  
  Common abstract base model providing created/modified timestamps and audit fields.

- **Account**  
  Custom user model with manager.  
  Handles authentication and authorization for:
  - staff
  - admin
  - company users
  - individual users

- **Company**  
  One-to-one relationship with `Account`.  
  Stores company-specific details and status.

- **Group**  
  Belongs to a `Company`.  
  Represents company groups loaded from a local JSON source.

- **Individual**  
  One-to-one relationship with `Account`.  
  Belongs to a `Group` and stores individual user details.

---

## admin.py

- **CompanyAdminForm**
  - Loads group choices from a local JSON file
  - Uses Select2 widget for group selection
  - Delegates create/update/delete logic to `CompanyService`
  - Enforces:
    - No duplicate group assignment across companies
    - Username/password required on first save
    - Optional password change on edit

- **IndividualAdminForm**
  - Lightweight form for individual users
  - Same username/password validation rules
  - Delegates logic to `IndividualService`

- **Custom ModelAdmin Classes**
  - Plug in custom forms
  - Add list views, filters, and search
  - Override delete hooks so deleting a company/individual also deletes the related `Account` via the service layer
  - `AccountAdmin` extends Django’s `UserAdmin` and adds a **User Type** column derived from linked profile (Company / Individual / Staff)

- **Media Assets**
  - Select2 CSS and JS loaded via CDN for group selection UI

---

## services.py

- **CompanyService**
  - Validates group availability (no duplicate assignment across companies)
  - Creates company along with account and groups
  - Updates company, account, and groups
  - Cascades inactive company → all related groups inactive
  - Deletes company and its associated account

- **IndividualService**
  - Creates individual with account
  - Updates individual details, account data, and password
  - Deletes individual and its associated account

---

## Key Features

- **Separation of Concerns**  
  Forms handle UI and validation, services handle business logic.

- **Data Integrity**  
  A group can belong to only one company at a time.

- **Cascading Rules**  
  Inactive company automatically deactivates all related groups.

- **Account Management**  
  Deleting a company or individual also deletes the linked account.
