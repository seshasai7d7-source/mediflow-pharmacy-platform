# MediFlow Pharmacy Platform
## Technical Design Document (TDD)

**GitHub Repository:** https://github.com/seshasai7d7-source/mediflow-pharmacy-platform

**Project:** MediFlow Pharmacy Platform  
**Document Type:** Technical Design Document  
**Version:** 1.1  
**Date:** November 2026  
**Deployment Status:** Local demonstration only; not deployed to a public hosting environment.

---

## 1. Project Overview

MediFlow is a web-based pharmacy ordering and prescription-review application. It demonstrates how customers can submit prescription documents, how pharmacists review those submissions, and how approved prescriptions can be used to create and manage orders.

The application also includes refill plan management and administrative functionality.

The system supports three primary roles:

- **Customer:** Registers, signs in, browses medicine inventory, submits prescriptions, views prescription and order information, and manages refill plans and requests.
- **Pharmacist:** Reviews prescription submissions, checks extracted medicine information, approves or rejects prescriptions, reviews refill plans and requests, and manages supported order status transitions.
- **Administrator:** Accesses administrative information, manages user and store records, and views operational overview information.

The application is a demonstration implementation. It is not intended for processing real prescriptions, accepting real payments, or dispensing medicines.

## 2. Project Objectives

The primary objectives are:

1. Provide authenticated customer, pharmacist, and administrator workflows.
2. Maintain medicine, store, and inventory information.
3. Allow customers to upload prescription documents.
4. Use AI-assisted extraction to prepare prescription information for review.
5. Require pharmacist review before prescription approval.
6. Create orders from approved prescriptions.
7. Reserve and release inventory through supported order workflows.
8. Support pharmacist-reviewed refill plans and refill requests.
9. Provide administrative visibility into users, stores, orders, prescriptions, and inventory.
10. Record important workflow actions for auditability.
11. Validate application behavior through automated tests.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React 19 |
| Programming language | TypeScript |
| Frontend build tool | Vite |
| Styling | Tailwind CSS |
| Backend framework | FastAPI |
| Backend language | Python |
| Data validation | Pydantic |
| ORM | SQLAlchemy |
| Database | PostgreSQL 16 |
| Database migrations | Alembic |
| Authentication | JWT |
| Password hashing | pwdlib with Argon2 |
| AI extraction | Google Gemini API |
| Testing | Pytest and HTTPX |
| Local infrastructure | Docker Compose |

## 4. Architecture and Design Rationale

### 4.1 High-level architecture

MediFlow uses a frontend-backend architecture.

**Application flow:**

Customer / Pharmacist / Administrator  
→ React and TypeScript frontend  
→ HTTP and JSON API communication  
→ FastAPI backend  
→ Authentication and authorization  
→ Business services and AI extraction  
→ SQLAlchemy ORM  
→ PostgreSQL database

The frontend handles user interaction and communicates with versioned backend APIs.

The backend is responsible for authentication, authorization, validation, business rules, database transactions, and workflow execution.

Google Gemini is used for assisted prescription information extraction. Its output is treated as draft information and does not replace pharmacist review.

### 4.2 Architecture rationale

- **React and TypeScript:** Provide a component-based interface and compile-time type checking.
- **FastAPI:** Provides API routing, request validation, dependency-based authorization, and interactive API documentation.
- **PostgreSQL:** Stores structured application data and supports relational integrity and transactional workflows.
- **SQLAlchemy:** Separates database operations from API request handling.
- **Alembic:** Provides version-controlled database schema migrations.
- **Service layer:** Keeps important business rules separate from route handlers and makes them easier to test.
- **Docker Compose:** Provides a reproducible local PostgreSQL environment.
- **Gemini:** Assists with prescription information extraction while keeping the final decision under pharmacist control.

## 5. Backend Design

The backend is organized into API routes, application configuration, database access, models, schemas, and business services.

Main responsibilities include:

- User authentication and JWT validation.
- Role-based access control.
- Request and data validation.
- Medicine and inventory management.
- Prescription document handling.
- AI-assisted prescription extraction.
- Pharmacist prescription review.
- Order creation and status management.
- Inventory reservation and release.
- Refill plan and request management.
- Administrative user and store management.
- Audit logging.

Business logic is separated into service functions where appropriate. This helps keep workflow rules consistent and supports automated testing.

## 6. Database Design

PostgreSQL stores the application's persistent data.

### 6.1 Main entities

| Entity | Responsibility |
|---|---|
| Users | Customer, pharmacist, and administrator accounts |
| Stores | Pharmacy store information |
| Medicines | Medicine catalogue and schedule classification |
| Inventory | Store-level stock and reserved quantities |
| Prescriptions | Uploaded documents, extraction information, and review status |
| Prescription Items | Medicine details associated with prescriptions |
| Orders | Customer orders and workflow status |
| Order Items | Medicines and quantities associated with orders |
| Refill Plans | Recurring refill arrangements and review information |
| Refill Requests | Customer requests generated from active refill plans |
| Audit Logs | Records important application and workflow actions |

### 6.2 Key relationships

- A customer can submit multiple prescriptions.
- A prescription can contain multiple prescription items.
- An approved prescription can be associated with an order.
- An order contains order items.
- Inventory records connect medicines with stores.
- A customer can have multiple refill plans.
- A refill plan is associated with a prescription.
- A refill plan can have multiple refill requests.
- An approved refill request can be associated with an order.
- Audit logs record relevant user and business actions.

SQLAlchemy models define the entities and relationships. Alembic manages database schema changes through versioned migrations.

## 7. Authentication and Authorization

The application uses JWT-based authentication.

Implemented controls include:

- Passwords are stored as hashes rather than plaintext.
- Successful authentication returns an access token.
- Protected endpoints validate authentication.
- Role-based dependencies restrict access to customer, pharmacist, and administrator operations.
- Public registration creates customer accounts only.
- Pharmacist and administrator accounts are provisioned through separate backend scripts using environment variables.
- Administrative operations require administrator authorization.

Customers cannot directly approve their own prescriptions or access pharmacist-only and administrator-only operations.

## 8. Prescription Workflow and AI Design

The prescription workflow separates AI-assisted extraction from the final pharmacist decision.

### 8.1 Workflow

1. Customer uploads a prescription document.
2. The document is stored by the application.
3. The backend attempts AI-assisted information extraction.
4. Extracted information is saved as draft data.
5. The prescription appears in the pharmacist review workflow.
6. The pharmacist inspects the prescription and medicine information.
7. The pharmacist can make supported corrections and submit a review decision.
8. An approved prescription can be used to create an order.

### 8.2 AI-assisted extraction

The application integrates Google Gemini using the configured model `gemini-2.5-flash`.

The AI extraction process is intended to prepare structured prescription information for pharmacist inspection.

Important design decisions:

- Extracted information is not automatically approved.
- AI output is not treated as a verified prescription or dispensing authorization.
- Incomplete or unavailable extraction must be handled through manual review.
- The application records a manual-review requirement when extraction cannot provide a sufficiently usable result.
- Automated tests mock external AI behavior rather than depending on a live Gemini API.

### 8.3 Pharmacist review and medicine restrictions

The pharmacist reviews the prescription before approval.

The supported review workflow applies medicine schedule restrictions. Schedule X, NARCOTIC, and UNKNOWN classifications are not eligible for approval through the implemented workflow.

Generic substitution requires customer consent.

Rejected prescriptions retain their review status and rejection information.

**Safety principle:** AI assists with information extraction only. Pharmacist review remains mandatory.

## 9. Order and Inventory Management

Orders are created from approved prescriptions.

### 9.1 Supported order status transitions

| Current status | Allowed next status |
|---|---|
| confirmed | preparing, cancelled |
| preparing | ready, cancelled |
| ready | dispatched, cancelled |
| dispatched | delivered |
| delivered | None |
| cancelled | None |

The backend validates status transitions. Skipping supported stages or reopening terminal statuses is not permitted.

### 9.2 Inventory handling

Inventory reservation and release are handled through backend services.

- Stock availability is checked before reservation.
- Reserved quantities are tracked.
- Cancellation releases the quantities reserved for the order.
- Guarded database operations help prevent invalid stock changes.
- Workflow changes are recorded in audit logs.

The implementation provides inventory reservation functionality but does not establish a fully automated production multi-store fulfillment system.

## 10. Refill Plan and Refill Request Workflow

MediFlow includes a pharmacist-reviewed refill workflow.

### 10.1 Refill plan creation

1. A customer creates a refill plan using an approved prescription.
2. The customer specifies a refill interval.
3. The plan enters `pending_review`.
4. A pharmacist or administrator reviews the plan.
5. An approved plan becomes `active` and receives a next refill date.
6. A rejected plan retains its rejection status and review information.

The implementation validates refill intervals and prevents duplicate active or pending plans for the same prescription.

### 10.2 Refill request processing

1. The customer submits a request against an active refill plan.
2. The backend checks that the plan is active and its due date has arrived.
3. The request enters `pending_review`.
4. A pharmacist or administrator reviews the request.
5. An approved request creates an order using the associated approved prescription.
6. The refill request, order, inventory changes, plan date update, and relevant audit records are committed through the supported transaction workflow.

### 10.3 Refill plan controls

Customers can pause, resume, or cancel eligible refill plans.

Pending refill requests are cancelled when the associated plan is paused or cancelled, according to the implemented service rules.

**Limitation:** This is a request-and-review workflow. It does not implement automated recurring orders or scheduled reminder notifications.

## 11. Administrator Functionality

The administrator module provides administrative visibility and management.

Implemented API capabilities include:

- Listing and searching users.
- Filtering users by role and active status.
- Updating supported user fields.
- Preventing an administrator from changing their own role or deactivating their own account through the protected update operation.
- Listing and searching stores.
- Viewing individual store information.
- Updating supported store fields.
- Viewing an operational overview.

The overview includes:

- User totals and active/inactive counts.
- User counts by role.
- Active and inactive store counts.
- Order counts by status.
- Prescription counts by status.
- Inventory record counts.
- Available and reserved inventory quantities.

Relevant administrative changes are recorded in audit logs.

## 12. API Design

The backend exposes versioned APIs under `/api/v1`.

| API area | Responsibility |
|---|---|
| Authentication | Registration, login, current-user information |
| Inventory | Medicine availability, inventory import, routing-related operations, and reservation |
| Stores | Store information |
| Prescriptions | Customer uploads and prescription information |
| Pharmacist | Prescription review queue, details, and review decisions |
| Orders | Order creation, listing, details, and status updates |
| Refills | Refill plans, customer requests, and pharmacist/admin review |
| Admin | User management, store management, and operational overview |
| Health | Application health checks |

The API uses JSON for normal request and response payloads. Prescription documents are uploaded using multipart form data.

FastAPI interactive documentation is available at `/docs` when the backend is running.

## 13. Frontend Design and UI Decisions

The frontend is built using React and TypeScript.

### 13.1 Main application areas

**Customer interface**
- Registration and login.
- Customer dashboard.
- Medicine inventory views.
- Prescription submission and status views.
- Order views.
- Refill plan creation and management.
- Refill request views.

**Pharmacist interface**
- Prescription review queue.
- Prescription details and extracted information.
- Medicine review and supported corrections.
- Approval and rejection actions.
- Order management.
- Refill plan and refill request queues.

**Administrator interface**
- Administrative overview.
- User listing, search, and filtering.
- Store listing and management.
- Operational counts and status information.

### 13.2 Design decisions

- Role-based navigation separates customer, pharmacist, and administrator workflows.
- Protected routes prevent users from accessing pages outside their assigned role.
- Workflow-specific screens expose actions relevant to the current business state.
- Shared API communication is configured through `VITE_API_BASE_URL`.
- Backend validation remains authoritative even when the frontend provides input validation.

## 14. Error Handling and Data Integrity

The backend validates input and business state before performing operations.

Important safeguards include:

- Authentication and role checks.
- Prescription status validation.
- Medicine schedule restrictions.
- Inventory quantity checks.
- Order transition validation.
- Refill plan and request state validation.
- Database transaction handling.
- Rollback when service operations fail.
- Audit logging for important workflow changes.

The application returns appropriate HTTP error responses when requests are invalid, unauthorized, or conflict with the current business state.

## 15. Testing Strategy and Verification

Automated backend tests use Pytest and HTTPX.

The test suite covers:

- Authentication and authorization.
- API request validation.
- Prescription upload and review workflows.
- AI extraction fallback behavior.
- Medicine schedule restrictions.
- Generic substitution consent.
- Order creation and status transitions.
- Inventory reservation and release.
- Refill plan and request business rules.
- Administrative and other backend behavior.
- Error handling and database integrity.

Tests use an isolated test database configuration and mocked external AI behavior where appropriate.

Frontend validation uses the TypeScript production build through `npm run build`.

### Latest development verification

| Verification | Result |
|---|---|
| Backend automated tests | **170 passed** |
| Admin account script syntax | Passed |
| Pharmacist account script syntax | Passed |
| Frontend production build | Successful |
| Pharmacist order workflow | Manually verified, including supported status transitions and persistence |
| Customer restriction on pharmacist order management | Manually verified |

The test result reflects the latest development run. It is not a claim of production certification or end-to-end testing of every challenge requirement.

## 16. Security Considerations

Implemented security measures include:

- Password hashing.
- JWT-based authentication.
- Role-based endpoint protection.
- Customer-only public registration.
- Environment-based configuration for sensitive settings.
- Separate provisioning of privileged demonstration accounts.
- Audit logging for important workflow operations.
- Pharmacist review before prescription approval.

Uploaded prescription documents must be treated as sensitive information.

A real deployment would additionally require production-grade document access controls, HTTPS, secure secret management, encryption and backup policies, monitoring, security testing, and applicable privacy and regulatory reviews.

## 17. Assumptions

The following assumptions define the scope of this demonstration:

1. The application uses synthetic demonstration accounts and data rather than real customer or patient records.
2. The application is evaluated as a local demonstration, not as a live pharmacy service.
3. Pharmacists and administrators are provisioned separately from public customer registration.
4. AI extraction provides draft information only and cannot make the final prescription approval decision.
5. Refill intervals and refill requests are managed through explicit customer and pharmacist/admin actions.
6. The demonstration database and inventory records are used to validate application workflows rather than represent live stock across an operating pharmacy chain.
7. Payment processing and production medicine pricing are outside the implemented scope.
8. The project uses the challenge brief as its business context; incomplete requirements are not represented as implemented functionality.

## 18. Known Limitations and Scope Exclusions

The following challenge capabilities are not fully implemented or have not been verified as complete:

- OTP-based customer authentication.
- Family or caregiver profile management.
- Production-ready payment integration, including UPI or cash-on-delivery workflows.
- Automated refill reminders and automatic recurring orders.
- Complete medicine pricing and invoice generation.
- Fully automated nearest-store fulfillment and geographic routing.
- Production central operations reporting and business performance metrics.
- Multilingual interfaces.
- Production hosting and deployment.
- Production-grade security, privacy, and regulatory validation.

Additional limitations:

- AI extraction may be incomplete or inaccurate.
- Pharmacist review remains necessary.
- Demonstration order totals may be zero because complete business pricing is not configured.
- The application has not undergone production operational validation.

## 19. Future Improvements

Potential future enhancements include:

- OTP authentication and family profiles.
- Secure prescription document preview and access controls.
- Complete medicine pricing and payment integration.
- Automated refill reminders and notification services.
- Automated nearest-store fulfillment and stock-aware routing.
- Improved invoice and handover workflows.
- Central operations reporting and performance metrics.
- Multilingual customer and pharmacist interfaces.
- Automated deployment and CI/CD pipelines.
- Expanded frontend automated tests.
- Monitoring, structured logging, and alerting.
- Production-grade security and compliance validation.

## 20. Conclusion

MediFlow demonstrates a pharmacy ordering and prescription-review application using React, TypeScript, FastAPI, PostgreSQL, and Google Gemini.

The implementation includes customer authentication, prescription submission, AI-assisted extraction, pharmacist review, order management, inventory reservation, refill plan and request workflows, and administrator functionality.

Its design separates AI-assisted extraction from pharmacist decision-making and applies backend validation to important prescription, inventory, order, and refill operations.

The project provides a working demonstration foundation while clearly identifying the additional functionality and operational safeguards required before a real pharmacy deployment.