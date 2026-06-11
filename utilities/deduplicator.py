"""
deduplicator.py - detect and remove duplicate rows from a data frame based on key columns
Responsibilities:
- Detect and remove duplicate rows from a data frame based on key columns defined in constants.py.
- Duplicates are identified based on the UNIQUE_KEYS for each file type. If no key columns are present, a warning is logged and deduplication is skipped.
- Returns a cleaned data frame with duplicates removed, and a list of quarantine entries for the duplicates

"""
import logging
import pandas as pd

from .constants import SOURCE_ID_MAPPING, UNIQUE_KEYS
logger = logging.getLogger("data_pipeline.deduplicator")

def detect_duplicates(df:pd.DataFrame, file_type:str) -> tuple[pd.DataFrame, list[dict]]: 
    primary_keys = UNIQUE_KEYS[file_type]
    source_id_mapping = SOURCE_ID_MAPPING[file_type]

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

        # Safely extract the hidden metadata - row_number and raw_data - that we attached in the validator. If these keys are missing, we can still quarantine the duplicate based on the key column values, but we'll log a warning since it may make troubleshooting harder.
        row_num = dup_row.get("row_number", None)
        raw_dict = dup_row.get("raw_data", None)

        canonical_rows = unique_df[(unique_df[present_keys] == dup_row[present_keys]).all(axis=1)]
        alias_id = dup_row.get(source_id_mapping, None)
        canonical_id = canonical_rows.iloc[0].get(source_id_mapping, None) if not canonical_rows.empty else None
        # Fallback : use cleaned row but strip NaN values
        
        if not isinstance(raw_dict, dict):
            fallback_dict = dup_row.drop(["row_number", "raw_data"], errors="ignore").to_dict()
            raw_dict = {k: (None if pd.isna(v) else v) for k, v in fallback_dict.items()}
        
        quarantine_entries.append({
            "row_number": int(row_num),
            "raw_data": raw_dict,
            "reason_code": "DUPLICATE_RECORD",
            "reason_detail": (
                f"Duplicate of an earlier record with the same "
                f"{present_keys} value(s). Canonical source_id: {canonical_id}, duplicate source_id: {alias_id}."
            ),
            "alias_id": alias_id,
            "canonical_id": canonical_id
        })

    # Clean up the metadata columns so they don't leak into the final database output
    # cols_to_drop = ["row_number", "raw_data"]
    # unique_df = unique_df.drop(columns=[c for c in cols_to_drop if c in unique_df.columns], errors="ignore")

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