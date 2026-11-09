# MediFlow Pharmacy Platform

## Technical Design Document (TDD)



**Project:** MediFlow Pharmacy Platform  

**Document type:** Technical Design Document  

**Version:** 1.0  

**Date:** November 2026



## 1. Project Overview



MediFlow is a web-based pharmacy ordering and prescription-review application. It demonstrates how customers can submit prescription documents and how pharmacists can review those submissions before an order is created.



The system is designed around three primary roles:



- **Customer:** Registers, signs in, browses medicine inventory, submits prescriptions, and views prescription and order status.

- **Pharmacist:** Reviews submitted prescriptions, checks medicine details, approves or rejects submissions, and manages supported order status transitions.

- **Administrator:** Has a separate application role for administrative access.



The application is a demonstration system and is not intended for processing real prescriptions or dispensing medicines.



## 2. Objectives



The main objectives are:



1. Provide authenticated customer and pharmacist workflows.

2. Maintain medicine and inventory information.

3. Allow customers to upload prescription documents.

4. Use AI-assisted extraction to prepare prescription information for review.

5. Require pharmacist review before prescription approval.

6. Create orders from approved prescriptions.

7. Reserve and release inventory through order workflows.

8. Record important actions for auditability.

9. Validate core business rules through automated tests.



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

| Password security | pwdlib with Argon2 |

| AI extraction | Google Gemini API |

| Vector search components | ChromaDB / pgvector integration |

| Testing | Pytest and HTTPX |

| Local infrastructure | Docker Compose |



## 4. High-Level Architecture



The application follows a frontend-backend architecture.



```text

Customer / Pharmacist / Administrator

&#x20;                 |

&#x20;                 v

&#x20;       React + TypeScript UI

&#x20;                 |

&#x20;            HTTP / JSON

&#x20;                 |

&#x20;                 v

&#x20;            FastAPI API

&#x20;                 |

&#x20;      +----------+-----------+

&#x20;      |          |           |

&#x20;      v          v           v

&#x20;Authentication  Business   AI Extraction

&#x20;and Authorization Services  (Gemini)

&#x20;      |          |           |

&#x20;      +----------+-----------+

&#x20;                 |

&#x20;                 v

&#x20;            SQLAlchemy

&#x20;                 |

&#x20;                 v

&#x20;             PostgreSQL

```



The React frontend communicates with the FastAPI backend through HTTP APIs. The backend validates requests, checks authorization, applies business rules, and persists application data in PostgreSQL.



Gemini is used for assisted prescription information extraction. Extracted information is treated as draft data and must be reviewed by a pharmacist.



## 5. Backend Design



The backend is organized into application modules for API routing, configuration, database access, models, schemas, and business services.



### Main responsibilities



- Authenticate users and validate access tokens.

- Enforce role-based access restrictions.

- Validate incoming request data.

- Manage medicine and inventory records.

- Process prescription uploads.

- Coordinate AI-assisted extraction.

- Manage pharmacist review decisions.

- Create and update orders.

- Maintain audit records.



Business logic is separated into service functions so that important rules can be tested independently of frontend behavior.



## 6. Database Design



PostgreSQL stores the application's persistent data.



### Main entities



| Entity | Responsibility |

|---|---|

| Users | Customer, pharmacist, and administrator accounts |

| Stores | Pharmacy store information |

| Medicines | Medicine catalogue and schedule classification |

| Inventory | Store-level medicine stock and reservations |

| Prescriptions | Uploaded documents, extraction data, and review status |

| Prescription Items | Medicine details associated with a prescription |

| Orders | Customer orders and their workflow status |

| Order Items | Medicines and quantities included in orders |

| Audit Logs | Records important application and workflow actions |



### Key relationships



- A customer can submit multiple prescriptions.

- A prescription can contain multiple prescription items.

- An approved prescription can be associated with an order.

- An order contains one or more order items.

- Inventory records connect medicines with stores.

- Audit logs record relevant user and business actions.



SQLAlchemy models define the database entities and relationships. Alembic manages schema changes through versioned migrations.



## 7. Authentication and Authorization



The application uses JWT-based authentication.



- User passwords are stored as password hashes rather than plaintext.

- Successful authentication returns an access token.

- Protected endpoints validate the token.

- Role-based dependencies restrict access to customer, pharmacist, and administrator operations.

- Public registration creates customer accounts only.



Pharmacist operations require pharmacist authorization. Customers cannot directly approve or reject their own prescriptions.



## 8. Prescription Workflow



The prescription workflow is designed to keep AI extraction separate from the final review decision.



```text

Customer uploads prescription

&#x20;            |

&#x20;            v

&#x20;    Document is stored

&#x20;            |

&#x20;            v

&#x20;  AI-assisted extraction

&#x20;            |

&#x20;            v

&#x20;    Draft information

&#x20;            |

&#x20;            v

&#x20;  Pharmacist review queue

&#x20;            |

&#x20;            v

&#x20;   Pharmacist checks data

&#x20;            |

&#x20;       +----+----+

&#x20;       |         |

&#x20;       v         v

&#x20;    Approve    Reject

&#x20;       |         |

&#x20;       v         v

&#x20;  Create order  Record reason

```



### AI extraction



The application can use Google Gemini to extract structured information from uploaded prescription documents.



Extracted information is a draft only. It is not treated as a verified prescription, medical decision, or dispensing authorization.



If extraction is unavailable or incomplete, the workflow must allow manual pharmacist review.



### Pharmacist review



The pharmacist can inspect the prescription details, edit medicine information, select medicines from the active catalogue, and submit a review decision.



The review workflow applies medicine schedule restrictions. Prohibited categories such as Schedule X and NARCOTIC, as well as UNKNOWN classifications, are not eligible for approval through the supported workflow.



Generic substitution requires customer consent.



A rejected prescription retains its rejection reason and status.



## 9. Order and Inventory Workflow



Orders are created following prescription approval.



The supported order status transitions are:



| Current status | Allowed next status |

|---|---|

| confirmed | preparing, cancelled |

| preparing | ready, cancelled |

| ready | dispatched, cancelled |

| dispatched | delivered |

| delivered | None |

| cancelled | None |



The backend validates each requested transition. Skipping workflow stages and reopening terminal statuses are not permitted.



Inventory reservation and release are handled by backend services. Cancellation releases the quantities reserved for the order. Inventory updates use guarded database operations to help prevent invalid stock changes.



Order status changes are recorded in audit logs.



## 10. API Design



The backend exposes versioned APIs under `/api/v1`.



The main API areas include:



| API area | Responsibility |

|---|---|

| Authentication | Registration, login, current-user information |

| Inventory | Medicine availability, inventory import, routing, and reservation |

| Stores | Store information |

| Prescriptions | Customer uploads and prescription information |

| Pharmacist | Review queue, prescription details, medicine catalogue, and review decisions |

| Orders | Order creation, listing, details, and status updates |

| Health | Application health checks |



The API uses JSON for normal request and response payloads. Prescription documents are uploaded using multipart form data.



Interactive API documentation is available through FastAPI Swagger UI at `/docs`.



## 11. Frontend Design



The frontend is built using React and TypeScript.



Main application areas include:



- Customer registration and login.

- Customer dashboard.

- Medicine inventory views.

- Prescription submission and status views.

- Pharmacist prescription queue.

- Pharmacist prescription review.

- Order views and supported status management.



React Router handles navigation. Protected routes restrict pages based on the authenticated user's role.



The frontend communicates with the backend through a shared API client configured using `VITE\_API\_BASE\_URL`.



## 12. Error Handling and Data Integrity



The backend validates input before performing business operations.



Important safeguards include:



- Authentication and role checks.

- Prescription status validation.

- Medicine schedule restrictions.

- Inventory quantity checks.

- Order transition validation.

- Database transaction handling.

- Rollback when service operations fail.

- Audit logging for important workflow changes.



The application returns appropriate HTTP error responses when requests are invalid, unauthorized, or conflict with current business state.



## 13. Testing Strategy



Automated backend tests use Pytest and HTTPX.



The test suite covers application behavior such as:



- Authentication and authorization.

- API request validation.

- Prescription upload and review workflows.

- AI extraction fallback behavior.

- Medicine schedule restrictions.

- Generic substitution consent.

- Order creation and status transitions.

- Inventory reservation and release.

- Error handling and database integrity.



Tests use isolated test database configuration and mocked external AI behavior where appropriate, avoiding dependence on a live Gemini API for normal automated test execution.



Frontend validation includes a TypeScript production build using `npm run build`.



### Latest recorded verification



- Backend automated tests: **140 passed, 1 warning**.
- Frontend production build: **successful**.
- Pharmacist Order Management: manually verified, including all supported order status transitions and persistence after refresh.
- Role-based access: customer access to pharmacist order management is blocked.

The backend warning is non-blocking and should be reviewed separately. These results reflect the latest development verification.



## 14. Security Considerations



- Passwords are hashed.

- Protected API routes require authentication.

- Role checks restrict privileged operations.

- Uploaded documents must be treated as sensitive data.

- Secrets and API keys are stored in environment configuration.

- Local environment files are excluded from version control.

- AI extraction does not replace pharmacist review.



A real deployment would additionally require production-grade file access controls, HTTPS, secure secret management, monitoring, backups, and regulatory review.



## 15. Known Limitations



- The project is a demonstration and has not undergone production validation.

- AI extraction may be incomplete or inaccurate.

- Pharmacist review remains necessary.

- Payment gateway integration is not implemented.

- Medicine pricing is not configured as a complete business pricing catalogue; demonstration order totals may be zero.

- Production operational, privacy, and regulatory requirements remain outside the scope of this implementation.



## 16. Future Improvements



Potential future enhancements include:



- Secure prescription document preview and access controls.

- Complete medicine pricing and payment integration.

- Automated deployment and CI/CD pipelines.

- Expanded frontend automated tests.

- Monitoring, structured logging, and alerting.

- More comprehensive inventory and multi-store fulfillment capabilities.

- Production-grade security and compliance validation.



## 17. Conclusion



MediFlow demonstrates an end-to-end pharmacy ordering and prescription-review workflow using a modern web stack. Its design separates AI-assisted extraction from pharmacist decision-making and applies backend validation to prescription, inventory, and order operations.



The implementation provides a foundation for further development while retaining clear boundaries around demonstration-only functionality.

