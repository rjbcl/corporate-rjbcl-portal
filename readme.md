# Project Structure Summary

## Models (`models.py`)

- **Account** – Stores login credentials (username, password, type)  
- **Company** – Company details, linked to Account  
- **Group** – Groups assigned to companies (with `group_id` from JSON)  
- **Individual** – Individual users, linked to Account and Group  
- All models inherit from **AuditBase** for tracking creation/modification  

---

## Services (`services.py`)

### CompanyService – Business logic layer
- Creates/updates companies with accounts and groups  
- Validates group availability (prevents duplicate assignments)  
- Handles cascading: inactive companies → inactive groups  
- Manages username uniqueness  

---

## Admin Interface (`admin.py`)

### CompanyAdminForm – Handles company registration/editing
- Creates Account automatically when registering company  
- Searchable multi-select for groups (loaded from JSON)  
- Username/password optional when editing (keeps existing if blank)  

### IndividualAdminForm – Handles individual user registration/editing
- Similar account creation flow as companies  

---

## Key Features

- **Separation of Concerns** – Forms handle UI/validation, Services handle business logic  
- **Data Integrity** – Groups can only belong to one company at a time  
- **Cascading Rules** – Inactive company → all groups inactive  
- **Account Management** – Deleting company/individual automatically deletes their account  