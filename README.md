You are a senior full-stack architect and AI engineer. Design and generate a scalable SaaS web application for Vastu report generation.

---

# 🧱 TECH STACK

* Backend: FastAPI (Python)
* Frontend: React + Fabric.js or Konva.js
* Database: MySQL
* ORM: SQLAlchemy
* Migrations: Alembic (Python-based migration system)
* Storage: Local file storage (with abstraction for future S3 support)
* Async Processing: Celery + Redis
* Payments: Razorpay
* PDF Generation: WeasyPrint or ReportLab
* Authentication: JWT (access + refresh tokens)

System MUST be API-first, modular, and reusable for future Flutter mobile applications.

---

# 🗄️ DATABASE & MIGRATION REQUIREMENTS (IMPORTANT)

## ORM

* Use SQLAlchemy (declarative models)

## Migration Tool

* Use Alembic for version-controlled migrations

## Requirements:

* Auto-generate migrations from models
* Maintain migration history
* Support rollback (downgrade)
* Environment-based configs (dev/staging/prod)

## Deliverables:

* `alembic/` setup with:

  * env.py
  * versions/
* Example commands:

  * create migration
  * upgrade DB
  * downgrade DB

---

# 📊 TASK TRACKING SYSTEM

(Include Google Sheets structure as defined previously)

---

# 👥 USER ROLES

1. Admin
2. End User

---

# 🔐 AUTHENTICATION & USER PROFILE

## Registration (MANDATORY)

* Name
* Email (required, unique)
* Phone Number (required, unique)
* Password (hashed)

---

## WHITE-LABEL PROFILE

Each user can configure:

* Logo (upload)
* Header Title
* Header Subtitle
* Email
* Phone
* Address
* Footer Text

Store in database + file storage.

---

# 👤 USER FEATURES

## IMAGE & CANVAS

* Upload image
* Rotate image
* Set starting degree

---

## POLYGON

* Draw polygon
* Label A, B, C...
* Apply → remove labels, lock, store coordinates

---

## ROOM & OBJECT MARKING

### Manual:

* Draw shapes
* Assign room/object types

---

### AI Mode:

* Detect rooms & objects
* YOLO / Detectron2
* Output bounding boxes + labels
* User approval required

---

# 📐 GEOMETRY ENGINE

* Compute centroid
* Apply rotation offset
* Generate:

  * 16 directions
  * 32 directions

---

# 📍 DIRECTION DETECTION

* Compute angle from centroid
* Map to sectors
* Detect Brahmasthan

MUST be mathematical, NOT AI-based.

---

# 📊 ANALYSIS ENGINE

* Map Room/Object → Direction
* Apply rules
* Generate results + remedies

---

# 💾 PROJECT MANAGEMENT

Store:

* Image
* Polygon
* Rooms
* Objects
* Directions
* Notes

---

# 📝 NOTES

* Add custom notes
* Include in report

---

# 📥 DOWNLOAD

## Image Export

## PDF REPORT

### White-label:

* User logo
* Header details
* Contact info
* Footer text
* No watermark

### Non white-label:

* Apply system watermark
* Default branding

---

# 💳 SUBSCRIPTION SYSTEM

## Plans:

* Name
* Price
* Duration
* Report limit
* White-label flag

## Enforcement:

* Track usage
* Block if exceeded

---

# 🧑‍💼 ADMIN FEATURES

## PACKAGE MANAGEMENT

* CRUD plans

---

## ROOM & OBJECT MASTER

* Define room types
* Define object types

---

## RULE ENGINE

* Rules for:

  * Rooms + Directions
  * Objects + Directions
  * Center

---

# 📄 REPORT CONFIG

* Templates
* Branding
* Sections

---

# 🧠 AI MODULE

* Independent microservice
* APIs:

  * /detect-rooms
  * /detect-objects

---

# 🎨 UI/UX

* Interactive canvas
* Toggle 16/32 views
* Smooth UX

---

# 🔐 SECURITY

* RBAC
* JWT
* Validation

---

# 📦 OUTPUT REQUIRED

## Backend

* Modular FastAPI structure
* SQLAlchemy models
* Alembic migrations

## Database Tables:

* users (with branding fields)
* plans
* subscriptions
* projects
* polygons
* rooms
* objects
* rules
* reports

---

## Migration Examples:

* Initial schema migration
* Add column migration
* Rollback example

---

## APIs

* Auth
* Projects
* Reports
* Subscriptions

---

## Core Modules

* Image processor
* Geometry engine
* AI integration
* Rule engine
* Report generator

---

## Frontend

* Component structure

---

## Task Tracking

* Google Sheets template

---

## Sample Code

* SQLAlchemy model
* Alembic migration
* Centroid calculation
* Direction mapping
* PDF generation

---

# ⚠️ NON-FUNCTIONAL REQUIREMENTS

* Clean architecture
* Scalable design
* Modular code
* Migration-safe schema updates
* No direct DB schema edits (ONLY via migrations)

---

