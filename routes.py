# routes.py - Route definitions for the data pipeline.
# Responsibilities:
# - Define routes for the data pipeline.
# - Each route corresponds to a specific validation or transformation step.

import sys
import uuid
import logging
import tempfile
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pipeline import run_pipeline

app = FastAPI(
    title="Opus Tuition Pipeline API",
    docs_url="/docs",
    openapi_url="/openapi.json" 
)

import logging
from pythonjsonlogger import jsonlogger
from pipeline import run_pipeline
from pathlib import Path
from db.storage import get_all_uploads, get_report_by_upload_id, insert_uploads, check_duplicate_hash, get_records, get_quarantine, delete_upload_api

# Set up JSON logging

# Defining directory 
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True) # Create logs directory if it doesn't exist
log_file = log_dir / "pipeline.log"

# Clear any default handlers to avoid duplicate logs
logging.getLogger().handlers.clear()

# Configure the root logger and set level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create the file handler N
handler = logging.FileHandler(log_file)

# Set up standard log format with timestamp, level, name and message
format_str = "%(asctime)s %(levelname)s %(name)s %(message)s"
formatter = jsonlogger.JsonFormatter(format_str)
handler.setFormatter(formatter)
logger.addHandler(handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

logger = logging.getLogger("data_pipeline.routes")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    upload_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix.lower()

    # Save the uploaded file to a temporary location for processing.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 1. Check for exact file duplicates using hash comparison before processing
        existing_upload_id = check_duplicate_hash(result.get("file_hash"))
        if existing_upload_id: 
            raise HTTPException(status_code=409, detail={
                "error": "DUPLICATE_FILE",
                "message": f"This file has already been uploaded with upload_id: {existing_upload_id}",
                "original_upload_id": existing_upload_id
            })
        
        # 2. Run the data pipeline on the new uploaded file.
        result = run_pipeline(tmp_path, upload_id)
        
        # 3. Insert into database 
        final_response  = insert_uploads (
            upload_id = upload_id,
            file_name = file.filename,
            result = result
        )

    except ValueError as e:
        logger.error(f"Value error for upload_id {upload_id}: {e}", exc_info=True)
        error_msg = str(e)
        if "Unsupported file type" in error_msg:
            raise HTTPException(status_code=422, detail={
                "error": "UNSUPPORTED_FILE_TYPE",
                "message": "Only .xlsx and .csv files are accepted"
            })
        error_type = "DEPENDENCY_ERROR" if "DEPENDENCY_ERROR" in str(e) else "PIPELINE_ERROR"
        raise HTTPException(status_code=422, detail={
            "error": error_type,
            "message": error_msg
        })
    except HTTPException as e:
        logger.warning(f"HTTPException raised for upload_id {upload_id}: {e.detail}")
        # Allow our custom 409 (or other HTTP exceptions) to pass through cleanly
        raise
    except Exception as e:
        logger.error(f"Unexpected pipeline failure for upload_id {upload_id}: {e}", exc_info=True)
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
        uploads = get_all_uploads()
        logger.info(f"Retrieved all uploads. Count: {len(uploads)}")
        return {"uploads": uploads} 
    except Exception as e:
        logger.error(f"Error occurred while retrieving uploads: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
            })

# get report for a specific upload_id
@app.get("/report/{upload_id}")
def get_report_by_id(upload_id: str): 
    try: 
        report = get_report_by_upload_id(upload_id)
        logger.info(f"Retrieved report for upload_id: {upload_id}")
    except Exception as e:
        logger.error(f"Error occurred while retrieving report for upload_id {upload_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
            })
    if not report:
        logger.warning(f"No report found for upload_id: {upload_id}")
        raise HTTPException(status_code=404, detail={
            "error": "NOT_FOUND",
            "message": f"No report found for upload_id: {upload_id}"
        })
    return report

@app.get("/records")
def api_get_records(file_type: str, upload_id: str = None, date_from: str = None, date_to: str = None):
    valid_file_types = ["tutor_assignments", "lesson_logs", "invoice"]
    if file_type not in valid_file_types:
        logger.warning(f"Invalid file_type parameter: {file_type}")
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_FILE_TYPE",
            "message": f"Invalid file type. Must be one of: {', '.join(valid_file_types)}"
        })
    try:
        records = get_records(file_type, upload_id, date_from, date_to)
        logger.info(f"Retrieved records for file_type: {file_type}, upload_id: {upload_id}, date_from: {date_from}, date_to: {date_to}. Count: {len(records)}")
        return {"file_type": file_type, "count": len(records), "records": records}
    except Exception as e:
        logger.error(f"Error occurred while retrieving records: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
        })
    
@app.get("/quarantine")
def get_quarantine(upload_id: str):
    try:
        records = get_quarantine(upload_id)
        logger.info(f"Retrieved quarantine records for upload_id: {upload_id}. Count: {len(records)}")
        return {"count": len(records), "quarantine": records}
    except Exception as e:
        logger.error(f"Error occurred while retrieving quarantine records for upload_id {upload_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "DATABASE_ERROR",
            "message": str(e)
        })
    
@app.delete("/delete/{upload_id}")
def delete_upload(upload_id: str):
    try:
        record = delete_upload_api(upload_id)
        logger.info(f"Deleted upload record for upload_id: {upload_id}")
        if not record:
            logger.warning(f"No upload found to delete with id: {upload_id}")
            raise HTTPException(status_code=404, detail={
                "error": "NOT_FOUND",
                "message": f"No upload found with id '{upload_id}'"
            })
    except ValueError as e:
        logger.error(f"Error occurred while deleting upload {upload_id}: {e}", exc_info=True)
        if "DEPENDENCY_ERROR" in str(e):
            raise HTTPException(status_code=400, detail={
                "error": "DEPENDENCY_ERROR",
                "message": str(e)
            })
        else:
            logger.error(f"Unexpected error occurred while deleting upload {upload_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={
                "error": "DATABASE_ERROR",
                "message": str(e)
            })
    return {"deleted": upload_id}