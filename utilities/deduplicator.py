"""
deduplicator.py - detect and remove duplicate rows from a data frame based on key columns
Responsibilities:
- Detect and remove duplicate rows from a data frame based on key columns defined in constants.py.
- Duplicates are identified based on the UNIQUE_KEYS for each file type. If no key columns are present, a warning is logged and deduplication is skipped.
- Returns a cleaned data frame with duplicates removed, and a list of quarantine entries for the duplicates

"""
import logging
import pandas as pd

from .constants import UNIQUE_KEYS
logger = logging.getLogger("data_pipeline.deduplicator")

def detect_duplicates(df:pd.DataFrame, file_type:str) -> tuple[pd.DataFrame, list[dict]]: 
    primary_keys = UNIQUE_KEYS[file_type]

    if not primary_keys:
        raise ValueError(f"No unique keys defined for file type: {file_type}")
    
    present_keys = [k for k in primary_keys if k in df.columns]
    if not present_keys:
        logger.warning(
            "No key columns present for duplicate detection — skipping",
            extra={"stage": "deduplication", "file_type": file_type},
        )
        return df, []
    
    # Looks up duplicated based on the present key columns, keeping the first occurrence and marking subsequent ones as duplicates.
    is_dup = df.duplicated(subset=present_keys, keep="first")
    # Keep rows that are false(not duplicates)
    unique_df = df[~is_dup].reset_index(drop=True)
    # Keep rows that are true (duplicates)
    dup_df = df[is_dup].reset_index(drop=True)

    quarantine_entries: list[dict] = []
    for _, dup_row in dup_df.iterrows():
        quarantine_entries.append({
            "row_number":    None,   # position lost after validation pass; raw_data is the identifier
            "raw_data": dup_row.to_dict(),
            "reason_code": "DUPLICATE_RECORD",
            "reason_detail": (
                f"Duplicate of an earlier record with the same "
                f"{present_keys} value(s)."
            ),
        })
 
    if quarantine_entries:
        logger.info(
            "Duplicates detected",
            extra={
                "stage": "deduplication",
                "file_type": file_type,
                "duplicate_count": len(quarantine_entries),
                "key_columns": present_keys,
            },
        )
 
    return unique_df, quarantine_entries