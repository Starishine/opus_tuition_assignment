""" 
utilities/detector.py - functions for detecting file types, header rows, and generating file hashes for caching
Responsibilities:
- Detect file type based on header row matching and file name heuristics
- Generate file hashes for caching and change detection
"""

import re
import hashlib 
import pandas as pd
import logging

from pathlib import Path

from .constants import EXPECTED_COLUMNS

logger = logging.getLogger("data_pipeline.detector")

def validate_file_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    logger.info(f"Detecting file type for: {path}")
    if suffix not in ['.csv', '.xlsx']:
        raise ValueError(f"Unsupported file type: {suffix}. Only .csv and .xlsx are supported.")

# Generate a hash of the file contents for caching and change detection
def generate_file_hash(path: str | Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def print_file_content(path: str | Path) -> None:
    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        df = pd.read_csv(path)
    elif suffix == '.xlsx':
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Only .csv and .xlsx are supported.")
    
    print(df.head())

## Detecting headers

# Return the fraction of non-null cells in *row* that appear in *expected*.
# Cells are lowercased and stripped before comparison.
def _score_row_as_header(row: pd.Series, expected: list[str]) -> float:
    cells = [
        str(v).strip().lower()
        for v in row
        if pd.notna(v) and str(v).strip() != ""
    ]
    print(f"Scoring row: {cells} against expected: {expected}")
    if not cells:
        return 0.0
    matched = sum(1 for c in cells if c in expected)
    print(f"Matched: {matched}")
    return matched / len(cells)
 
# Sanity check to avoid picking a decorative title row that happens to contain column-name-like words.
def _next_row_looks_like_data(df_raw: pd.DataFrame, row_idx: int) -> bool:
    next_idx = row_idx + 1
    if next_idx >= len(df_raw):
        return False
 
    for val in df_raw.iloc[next_idx]:
        if pd.isna(val):
            continue
        s = str(val).strip()
        try:
            float(s.replace(",", "").lstrip("$SGD "))
            return True
        except ValueError:
            pass
        # check for date like patterns 
        if re.search(r"\d{1,4}[\/\-\s]\d{1,2}", s):
            return True
    return False


# Public API 

def detect_header_row(path: str | Path, threshold: float = 0.5, 
                      max_scan_rows: int = 30) -> tuple[int, str]:
    if Path(path).suffix.lower() == '.xlsx':
        df_raw = pd.read_excel(path, header=None, nrows=max_scan_rows)
    else:
        df_raw = pd.read_csv(path, header=None, nrows=max_scan_rows)
    best_score = 0.0
    best_row_idx = 0
    best_file_type = ""

    for row_idx in range(len(df_raw)):
        row = df_raw.iloc[row_idx]
        for file_type, expected_cols in EXPECTED_COLUMNS.items():
            score = _score_row_as_header(row, expected_cols)
            print(f"Row{row_idx} vs {file_type}: {score}")
            if score > best_score:
                best_score = score
                best_row_idx = row_idx
                best_file_type = file_type
        if best_score >= threshold and _next_row_looks_like_data(df_raw, best_row_idx):
            logger.info(
                "Header detected",
                extra={
                    "stage": "structure_detection",
                    "row_index": best_row_idx,
                    "file_type": best_file_type,
                    "match_score": round(best_score, 2),
                },
            )
            return best_row_idx, best_file_type
    # if we scanned all rows, but theres no header, then try detecting the file type based on file name
    if best_score < threshold:
        logger.warning(
        "Header score below threshold — falling back to row 0. "
        "Detecting file type based on name.",
        extra={
            "stage": "structure_detection",
            "best_score": round(best_score, 2),
            "threshold": threshold,
            },
        )

        file_name = Path(path).name.lower()

        # remove spaces, underscores, and dashes for more matching
        found_name_match = False
        stripped_name = re.sub(r"[\s_-]+", "", file_name)
        for file_type in EXPECTED_COLUMNS.keys():
            stripped_file_type = re.sub(r"[\s_-]+", "", file_type)
            if stripped_file_type in stripped_name:
                logger.info(f"Inserting header for detected file type: {file_type} based on file name")
                insert_header(path, file_type)
                best_file_type = file_type
                best_row_idx = 0
                found_name_match = True
                break
        
        if not found_name_match:
            raise ValueError(f"Invalid file. Expected one of: {', '.join(EXPECTED_COLUMNS.keys())}.") 
    logger.info(
        "Header detected (threshold met, secondary check skipped)",
        extra={
            "stage": "structure_detection",
            "row_index": best_row_idx,
            "file_type": best_file_type,
            "match_score": round(best_score, 2),
        },
    )
    return best_row_idx, best_file_type


def insert_header(path: str | Path, file_type: str) -> None:
    expected_cols = EXPECTED_COLUMNS[file_type]
    if Path(path).suffix.lower() == '.xlsx':
        df_raw = pd.read_excel(path, header=None)
    else:
        df_raw = pd.read_csv(path, header=None)
    
    # Insert the expected columns as the first row
    new_df = pd.DataFrame([expected_cols], columns=df_raw.columns)
    new_df = pd.concat([new_df, df_raw], ignore_index=True)

    # Save back to the same file
    if Path(path).suffix.lower() == '.xlsx':
        new_df.to_excel(path, index=False, header=False)
    else:
        new_df.to_csv(path, index=False, header=False)

def load_file(path:str | Path) -> tuple[pd.DataFrame, str]:
    header_row, file_type = detect_header_row(path)

    if Path(path).suffix.lower() == '.xlsx':
        df = pd.read_excel(path, header=header_row)
    else: 
        df = pd.read_csv(path, header=header_row)
    
    # Clean the column names by stripping whitespace, replacing multiple spaces with a single space,
    # and lowercasing
    df.columns = [re.sub(r"\s+", " ", str(c).strip().lower()) for c in df.columns]

    return df, file_type


