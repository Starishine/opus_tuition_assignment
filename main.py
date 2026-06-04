"""
main.py - Main runner for the data ingestion and validation pipeline.
"""
import logging
from pythonjsonlogger import jsonlogger
from pipeline import run_pipeline

# Set up JSON logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":
    run_pipeline("./data/tutor_assignments_raw.xlsx", "test_upload_001", output_fmt="json")
