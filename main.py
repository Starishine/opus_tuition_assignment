"""
main.py - Main runner for the data ingestion and validation pipeline.
"""
import logging
from pythonjsonlogger import jsonlogger
from pipeline import run_pipeline
from pathlib import Path

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

if __name__ == "__main__":
    run_pipeline("./data/tutor_assignments_raw.xlsx", "test_upload_001", output_fmt="json")
    run_pipeline("./data/lesson_logs_messy.xlsx", "test_upload_002", output_fmt="json")
    run_pipeline("./data/invoice_export_q1.xlsx", "test_upload_003", output_fmt="json")
