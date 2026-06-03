import re
import hashlib 
import pandas as pd

from pathlib import Path

try:
    from .constants import EXPECTED_COLUMNS
except ImportError:
    from constants import EXPECTED_COLUMNS

def detect_file_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    print(suffix)
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
def _score_row_as_header(row: pd.Series, expected: list[str]) -> float:
    """
    Return the fraction of non-null cells in *row* that appear in *expected*.
    Cells are lowercased and stripped before comparison.
    """
    cells = [
        str(v).strip().lower()
        for v in row
        if pd.notna(v) and str(v).strip() != ""
    ]
    if not cells:
        return 0.0
    matched = sum(1 for c in cells if c in expected)
    return matched / len(cells)
 
 
def _next_row_looks_like_data(df_raw: pd.DataFrame, row_idx: int) -> bool:
    """
    Return True if the row immediately below *row_idx* contains at least one
    value that looks like a number or a date string.
 
    Secondary signal used to avoid selecting a decorative title row that
    happens to contain column-name-like words.
    """
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
        if re.search(r"\d{1,4}[\/\-\s]\d{1,2}", s):
            return True
    return False

if __name__ == "__main__":
    detect_file_type("../data/tutor_assignments_raw.xlsx")
    print(generate_file_hash("../data/tutor_assignments_raw.xlsx"))
    print_file_content("../data/tutor_assignments_raw.xlsx")