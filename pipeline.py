"""
pipeline.py — main pipeline for processing uploaded files, calling stages in order:

Calls stages in order:
  detector   → load file, detect header
  validator  → clean fields, enforce required fields, build quarantine
  deduplicator → remove duplicates, add to quarantine

Returns a result dict that storage.py and routes.py consume.
Also writes intermediate JSON/CSV output to disk before the DB write,
so there is always an inspectable artefact even if storage fails.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from utilities.detector import load_file, generate_file_hash, validate_file_type
from utilities.validator import VALIDATORS
from utilities.deduplicator import detect_duplicates

logger = logging.getLogger("data_pipeline.pipeline")

# Directory for intermediate outputs (created if missing)
OUTPUT_DIR = Path("docs/sample-outputs")

# Write clean rows and quarantine entries to disk before the DB write.
# Returns a dict of {"clean": Path, "quarantine": Path}.
# Supports fmt="json" or fmt="csv"
def _write_intermediate(clean_df: pd.DataFrame, quarantine: list[dict], file_type: str,
                        upload_id: str, fmt: str = "json") -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    clean_path = OUTPUT_DIR / f"{upload_id}_{file_type}_clean.{fmt}"
    quar_path  = OUTPUT_DIR / f"{upload_id}_{file_type}_quarantine.{fmt}"

    if fmt == "csv":
        clean_df.to_csv(clean_path, index=False)
        pd.DataFrame(quarantine).to_csv(quar_path, index=False)
    else:
        clean_path.write_text(
            clean_df.to_json(orient="records", date_format="iso", indent=2),
            encoding="utf-8",
        )
        quar_path.write_text(
            json.dumps(quarantine, indent=2, default=str),
            encoding="utf-8",
        )

    paths["clean"] = clean_path
    paths["quarantine"] = quar_path

    logger.info(
        "Intermediate output written",
        extra={
            "stage":      "pipeline",
            "clean_file": str(clean_path),
            "quar_file":  str(quar_path),
        },
    )
    return paths

# Run the full ingestion pipeline for a single file.

#  Parameters
# path : path to the uploaded file (.xlsx or .csv)
# upload_id  : unique ID for this upload (assigned by the API layer)
# output_fmt : "json" or "csv" for intermediate output files

# Returns
# {
# "file_type": str,
# "file_hash": str,
# "rows_received": int,
# "rows_accepted": int,
# "rows_quarantined": int,
# "clean_df": pd.DataFrame,
# "quarantine": list[dict],
# "output_paths": dict[str, Path],
# }

# Raises ValueError — unsupported file type, unknown file type after detection
def run_pipeline(path: str | Path, upload_id: str, output_fmt: str = "json") -> dict:

    validate_file_type(path)
    file_hash = generate_file_hash(path)

    logger.info(
        "Pipeline start",
        extra={"stage": "pipeline", "file": str(path), "hash": file_hash, "upload_id": upload_id},
    )

    # Stage 1: detect structure + load
    df_raw, file_type = load_file(path)
    rows_received = len(df_raw)

    # Stage 2: validate (clean fields + enforce required + quarantine invalids)
    validator_fn = VALIDATORS.get(file_type)
    if not validator_fn:
        raise ValueError(
            f"No validator registered for file type '{file_type}'. "
            f"Known types: {list(VALIDATORS.keys())}"
        )
    clean_df, quarantine = validator_fn(df_raw)

    # Stage 3: deduplicate
    clean_df, dup_entries = detect_duplicates(clean_df, file_type)
    quarantine.extend(dup_entries)

    # Write intermediate outputs before touching the database
    output_paths = _write_intermediate(
        clean_df, quarantine, file_type, upload_id, fmt=output_fmt
    )

    result = {
        "file_type": file_type,
        "file_hash": file_hash,
        "rows_received": rows_received,
        "rows_accepted": len(clean_df),
        "rows_quarantined": len(quarantine),
        "clean_df": clean_df,
        "quarantine": quarantine,
        "output_paths": output_paths,
    }

    logger.info(
        "Pipeline complete",
        extra={
            "stage": "pipeline",
            "upload_id": upload_id,
            "file_type": file_type,
            "rows_received": rows_received,
            "rows_accepted": len(clean_df),
            "rows_quarantined": len(quarantine),
        },
    )

    return result