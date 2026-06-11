# OPUS Data Ingestion Pipeline

A FastAPI backend pipeline that ingests messy Excel and CSV files, detects structure automatically, cleans and validates records, and separates invalid rows into a quarantine layer with specific, human-readable reason codes. Then, it saves valid clean records into a cloud database

---

## What It Does

- **Structure detection** — finds the header row without being told where it is (scans first 30 rows)
- **Cleaning** — normalises dates to ISO 8601, strips currency symbols, handles missing sentinels
- **Validation** — enforces required fields per file type with specific error codes
- **Deduplication** — detects exact and alias duplicates across uploads
- **Quarantine** — invalid rows are stored with reason codes, not silently dropped
- **Partial failure** — valid rows are always stored even when other rows in the same file fail

Supports three file types: `tutor_assignments`, `lesson_logs`, `invoice`.

---

## Project Structure

```
opus-tutition_assignment/
├── routes.py                  # FastAPI endpoints
├── pipeline.py                # Main pipeline 
├── utilities/
│   ├── detector.py            # Header detection + file f
│   ├── validator.py           # Per-file-type validation
│   ├── cleaner.py             # Cell-level cleaning 
│   ├── deduplicator.py        # Duplicate detection
│   ├── col_resolver.py        # Fuzzy column name 
│   └── constants.py           # Canonical columns, formats, sentinels
├── db/
│   └── storage.py             # All database reads and writes
│   └── schema.sql             # Database schema
├── frontend/                  # React (Vite) UI
├── tests/                     # Full unit test suite
├── docs/
│   └── sample-outputs/        # Intermediate pipeline outputs (local mode only)
├── logs/                      # Log files (local mode only)
├── .env.example               # Environment variable template
├── requirements.txt           # Project dependency installation
└── README.md
```

---

## Prerequisites

Before you begin, make sure you have the following installed:

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Git | any | `git --version` |

---

## Running the application
You have two options - use the live deployed link or run it locally

## Option 1 - Deployed Version (Recommended)
No set up required. Everything is set up for you. 
| | Link |
|---|---|
| **Frontend UI** | https://opus-tuition-assignment.vercel.app/ |
| **Database** | Supabase — access invitation sent via email |

> To access the intermediate files, visit supabase dashboard, navigate to Sania's Project and on the left menus bar, go to storage and click on 'pipeline-data-outputs'

## Option 2 - Local setup

## Local Setup — Backend

### 1. Clone the repository

```bash
git clone https://github.com/Starishine/opus_tuition_assignment.git
cd opus_tuition_assignment
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

```bash
# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your terminal prompt.

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the backend server

```bash
uvicorn routes:app --reload
```

The FAST API will be available at **http://127.0.0.1:8000**

Verify it is running by opening **http://127.0.0.1:8000/docs** — you should see the Swagger UI with all endpoints listed.

---

## Local Setup — Frontend

Open a **second terminal** (keep the backend running in the first).

```bash
cd frontend
npm install
npm run dev
```

The Frontend UI will be available at **http://localhost:5173**

---

## Running the Tests
Open a **third terminal**. From the **project root** with your virtual environment active:

```bash
python -m pytest .\test\ -v
```

Expected output shows all tests passing across five sections:
- Date normalisation 
- Currency symbol stripping
- Duplicate detection 
- Required field validation 
- Quarantine reason code specificity

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload a file, run the pipeline, return processing report |
| `GET` | `/all_uploads` | List all uploads ordered by most recent |
| `GET` | `/records` | Return accepted records, filterable by `file_type`, `upload_id`, `date_from`, `date_to` |
| `GET` | `/quarantine` | Return quarantined rows, optionally filtered by `upload_id` |
| `GET` | `/report/{upload_id}` | Return the full processing report for a specific upload |
| `DELETE` | `/uploads/{upload_id}` | Delete an upload and all its associated records |

All error responses are structured JSON — HTTP status codes alone are never returned without a body.

**Example error response:**
```json
{
  "error": "DUPLICATE_FILE",
  "message": "This file has already been uploaded.",
  "original_upload_id": "3f2a1b..."
}
```

---

## Upload Order

The three file types have a dependency order. Upload them in this sequence:

```
1. tutor_assignments file   — creates tutors, students, assignments
2. lesson_logs / invoice      — references assignment IDs
```

>> If lessons or invoices are uploaded before assignments, a 'PIPELINE ERROR' will be reflected in the UI, guiding the user to upload assignment file before invoice/lesson_logs

---

## Environment Behaviour

The pipeline automatically switches behaviour based on whether the `RENDER` environment variable is set:

| | Local (RENDER not set) | Production (RENDER=true) |
|---|---|---|
| **Logs** | Console + `logs/pipeline.log` | stdout only (Render log console) |
| **Intermediate outputs** | `docs/sample-outputs/` on disk | Supabase Storage bucket |
| **Database** | Supabase PostgreSQL | Supabase PostgreSQL |

---
