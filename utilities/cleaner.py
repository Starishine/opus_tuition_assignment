# utilities/cleaner.py - functions for cleaning and transforming individual cell values and dropping blank/decorative rows from data frames
# Responsibilities:
# - Transforms individual cell values 
# - Remove blanks and decorative rows from a data frame

import re
import logging
import pandas as pd
from datetime import datetime
from typing import Optional
 
from .constants import DATE_FORMATS, EXPECTED_COLUMNS, MISSING_SENTINELS
 
logger = logging.getLogger("data_pipeline.cleaner")

## Cell value cleaning and parsing

# Strip whitespace and convert empty strings / missing values to None
def clean_text(value: str) -> Optional[str]:
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value.lower() in MISSING_SENTINELS:
        return None
    return value if value else None

# Parses a date string into a consistent ISO 8601 format (YYYY-MM-DD) or returns None if parsing fails.
def parse_date(value: str) -> Optional[str]:
    value = clean_text(value)
    if value is None:
        return None
    
    for fmt in DATE_FORMATS:
        try:
            # Format to ISO 8601 (YYYY-MM-DD) for consistency
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    logger.warning(f"Unable to parse date: {value}", 
                   extra={"stage": "cleaning", "raw_value": value},)
    return None

def parse_numeric(value: str) -> Optional[float]:
    value = clean_text(value)
    if value is None:
        return None
    
    # Remove common currency symbols and codes before parsing
    cleaned_value = re.sub(r"[A-Z]{3}\s*|[$£€\s]", "", value, flags=re.IGNORECASE)
    cleaned_value = cleaned_value.replace(",", "")
    try:
        return float(cleaned_value)
    except ValueError:
        logger.warning(f"Unable to parse numeric value: {value}", 
                       extra={"stage": "cleaning", "raw_value": value},)
        return None
    

## Row level cleaning
def drop_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    initial_count = len(df)
    df_cleaned = df.dropna(how="all").reset_index(drop=True)
    dropped_count = initial_count - len(df_cleaned)
    logger.info(f"Dropped {dropped_count} blank rows", 
                extra={"stage": "cleaning", "dropped_rows": dropped_count})
    return df_cleaned

# Remove rows that are likely decorative (e.g. footers, notes) based on having too few non-null values or not looking like data rows
def drop_decorative_rows(df: pd.DataFrame, min_non_null: int = 2) -> pd.DataFrame:
    def _is_decorative(row: pd.Series) -> bool:
        # build list of non-null, non-empty values in the row
        non_null = [v for v in row if pd.notna(v) and str(v).strip() != ""]
        # if there are more than min_non_null values, it's probably not decorative
        if len(non_null) >= min_non_null:
            return False
        for v in non_null:
            s = str(v).strip()
            try:
                float(s)
                return False # if it can be parsed as a number, it's probably not decorative
            except ValueError:
                pass
            if re.search(r"\d{1,4}[\/\-]\d{1,2}", s):
                return False # looks like a date — keep it
        return True
 
    before = len(df)
    mask = df.apply(_is_decorative, axis=1) # True for rows to drop
    df = df[~mask].reset_index(drop=True) # Filter out decorative rows, only keeping data rows that are false
    dropped = before - len(df)
    if dropped:
        logger.info(
            "Decorative rows removed",
            extra={"stage": "cleaning", "rows_dropped": dropped},
        )
    return df

