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
from db.storage import insert_uploads, check_duplicate_hash

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
        result = run_pipeline(tmp_path, upload_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "error": "PIPELINE_ERROR",
            "message": str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected pipeline failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error": "INTERNAL_ERROR",
            "message": "Pipeline failed unexpectedly. Check server logs."
        })
    
    existing_upload_id = check_duplicate_hash(result.get("file_hash"))
    if existing_upload_id: 
        raise HTTPException(status_code=409, detail={
            "error": "DUPLICATE_FILE",
            "message": f"This file has already been uploaded with upload_id: {existing_upload_id}",
            "original_upload_id": existing_upload_id
        })
    
    insert_uploads(
        upload_id=upload_id,
        file_name=file.filename,
        result=result
    )

    
    logger.info(
        "File upload and processing successful", 
        extra={
            "upload_id": upload_id,
            "original_filename": file.filename,
            "file_type": result["file_type"],
            "metrics": {
                "rows_received": result["rows_received"],
                "rows_accepted": result["rows_accepted"],
                "rows_quarantined": result["rows_quarantined"],
            }
        }
    )

    return {
        "upload_id": upload_id,
        "file_type": result["file_type"],
        "rows_received": result["rows_received"],
        "rows_accepted": result["rows_accepted"],
        "rows_quarantined": result["rows_quarantined"],
        "quarantine": result["quarantine"],
    }