# routes.py - Route definitions for the data pipeline.
# Responsibilities:
# - Define routes for the data pipeline.
# - Each route corresponds to a specific validation or transformation step.

import uuid
import logging
import tempfile
import shutil

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pipeline import run_pipeline

logger = logging.getLogger("data_pipeline.routes")
app = FastAPI(title = "Data Pipeline API")

import logging
from pythonjsonlogger import jsonlogger
from pipeline import run_pipeline
from pathlib import Path
from db.storage import get_all_uploads, get_report_by_upload_id, insert_uploads, check_duplicate_hash

# Set up JSON logging

# Defining directory 
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True) # Create logs directory if it doesn't exist
log_file = log_dir / "pipeline.log"

# Configure logging to write to file and console with JSON format
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
handler = logging.FileHandler(log_file)
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=422, detail={
            "error": "UNSUPPORTED_FILE_TYPE",
            "message": "Only .xlsx and .csv files are accepted"
        })

    upload_id = str(uuid.uuid4())
    suffix = ".xlsx" if file.filename.endswith(".xlsx") else ".csv"

    # Save the uploaded file to a temporary location for processing.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 1. Run the data pipeline on the uploaded file.
        result = run_pipeline(tmp_path, upload_id)

        # 2. Check for exact file duplicates
        existing_upload_id = check_duplicate_hash(result.get("file_hash"))
        if existing_upload_id: 
            raise HTTPException(status_code=409, detail={
                "error": "DUPLICATE_FILE",
                "message": f"This file has already been uploaded with upload_id: {existing_upload_id}",
                "original_upload_id": existing_upload_id
            })
        # 3. Insert into database 
        final_response  = insert_uploads (
            upload_id = upload_id,
            file_name = file.filename,
            result = result
        )

    except ValueError as e:
        # Cleanly catches ValueErrors from both run_pipeline AND insert_uploads
        error_type = "DEPENDENCY_ERROR" if "DEPENDENCY_ERROR" in str(e) else "PIPELINE_ERROR"
        raise HTTPException(status_code=422, detail={
            "error": error_type,
            "message": str(e)
        })
    except HTTPException:
        # Allow our custom 409 (or other HTTP exceptions) to pass through cleanly
        raise
    except Exception as e:
        logger.error(f"Unexpected pipeline failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "INTERNAL_ERROR",
            "message": "Pipeline failed unexpectedly. Check server logs."
        })
        
    # If we made it here, the entire process succeeded!
    logger.info(
        "File upload and processing successful", 
        extra={
            "upload_id": upload_id,
            "original_filename": file.filename,
            "file_type": final_response.get("file_type"),
            "metrics": {
                "rows_received": final_response.get("rows_received"),
                "rows_accepted": final_response.get("rows_accepted"),
                "rows_quarantined": final_response.get("rows_quarantined"),
            }
        }
    )

    return {
        "upload_id": upload_id,
        "file_type": final_response.get("file_type"),
        "rows_received": final_response.get("rows_received"),
        "rows_accepted": final_response.get("rows_accepted"),
        "rows_quarantined": final_response.get("rows_quarantined"),
        "quarantine": final_response.get("quarantine"),
    }

# Get all upload records 
@app.get("/all_uploads")
def list_uploads():
    try: 
        return {"uploads": get_all_uploads()} 
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
            })

# get report for a specific upload_id
@app.get("/report/{upload_id}")
def get_report_by_id(upload_id: str): 
    try: 
        report = get_report_by_upload_id(upload_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
            })
    if not report:
        raise HTTPException(status_code=404, detail={
            "error": "NOT_FOUND",
            "message": f"No report found for upload_id: {upload_id}"
        })
    return report

@app.get("/records")
def get_records(file_type: str, upload_id: str = None, date_from: str = None, date_to: str = None):
    valid_file_types = ["tutor_assignments", "lesson_logs", "invoice"]
    if file_type not in valid_file_types:
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_FILE_TYPE",
            "message": f"Invalid file type. Must be one of: {', '.join(valid_file_types)}"
        })
    try:
        records = get_records(file_type, upload_id, date_from, date_to)
        return {"file_type": file_type, "count": len(records), "records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
        })
    
@app.get("/quarantine")
def get_quarantine(upload_id: str):
    try:
        records = get_quarantine(upload_id)
        return {"count": len(records), "quarantine": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
        })