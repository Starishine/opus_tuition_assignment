"""
validator.py — per-file-type validation stage 
Responsibilities:
  - Resolve actual column names to canonical names (fuzzy, once per file)
  - Apply field cleaners to each row
  - Check required fields are present after cleaning
  - Distinguish MISSING_REQUIRED_FIELD from INVALID_STATUS / INVALID_DATE /
    INVALID_NUMERIC with specific, human-readable reason details
  - Split rows into (clean_rows, quarantine_entries)

Quarantine entry shape:
  {
    "row_number":    int,   # 1-based spreadsheet row (header + offset)
    "raw_data":      dict,  # original cell values before any cleaning
    "reason_code":   str,   # machine-readable: MISSING_REQUIRED_FIELD etc.
    "reason_detail": str,   # human-readable: what the ops team needs to fix
  }
"""

import logging
import pandas as pd
from typing import Optional

from .cleaner import (
    clean_text,
    parse_date,
    parse_numeric,
    normalise_status,
    drop_blank_rows,
    drop_decorative_rows,
)
from .col_resolver import resolve_columns, rget
from .constants import STATUS_COLUMNS, MISSING_SENTINELS, EXPECTED_COLUMNS

logger = logging.getLogger("data_pipeline.validator")

# Canonical status values — sourced from STATUS_COLUMNS in constants.py

CANONICAL_STATUS: dict[str, list[str]] = {
    "tutor_assignments":  STATUS_COLUMNS["tutor_assignments"],  # active, inactive, pending
    "lessons_attendance": STATUS_COLUMNS["lessons"],            # present, absent, late
    "invoice":            STATUS_COLUMNS["invoice"],            # paid, unpaid, pending
}


# Quarantine helper functions

def _quarantine_entry(
    row_number: int,
    raw_data: dict,
    reason_code: str,
    reason_detail: str, ) -> dict:
    return {
        "row_number": row_number,
        "raw_data": raw_data,
        "reason_code": reason_code,
        "reason_detail": reason_detail,
    }

# Produces the correct quarantine entry for a status field that came back None.
# Distinguishes genuinely missing from unrecognised value.
def _status_error(
    field: str,
    raw_value,
    row_number: int,
    raw_data: dict,
    canonical: list[str] ) -> dict:

    if raw_value is None or pd.isna(raw_value):
        return _quarantine_entry(
            row_number, raw_data,"MISSING_REQUIRED_FIELD", 
            f"Field '{field}' is blank or null (row {row_number})",
        )
    raw_str = str(raw_value).strip()
    if raw_str.lower() in MISSING_SENTINELS or raw_str == "":
        return _quarantine_entry( row_number, raw_data, "MISSING_REQUIRED_FIELD",
                                 f"Field '{field}' is blank or null (row {row_number})",
        )
    return _quarantine_entry(
        row_number, raw_data,"INVALID_STATUS",
        f"Field '{field}': received \"{raw_str}\", expected one of {canonical} (row {row_number})",
    )

# Distinguishes unparseable date from genuinely missing date
def _date_error(field: str, raw_value, row_number: int, raw_data: dict) -> dict:
    if raw_value is not None and not pd.isna(raw_value):
        return _quarantine_entry(row_number, raw_data, "INVALID_DATE",
            f"Field '{field}': could not parse \"{raw_value}\" as a date (row {row_number})",
        )
    return _quarantine_entry( row_number, raw_data, "MISSING_REQUIRED_FIELD",
        f"Field '{field}' is blank or null (row {row_number})",
    )

# Distinguishes unparseable numeric from genuinely missing value
def _numeric_error(field: str, raw_value, row_number: int, raw_data: dict) -> dict:
    if raw_value is not None and not pd.isna(raw_value):
        return _quarantine_entry(
            row_number, raw_data, "INVALID_NUMERIC",
            f"Field '{field}': could not parse \"{raw_value}\" as a number (row {row_number})",
        )
    return _quarantine_entry(
        row_number, raw_data, "MISSING_REQUIRED_FIELD",
        f"Field '{field}' is blank or null (row {row_number})",
    )

# Per-file-type validators

# Clean and validate tutor_assignments_raw.xlsx rows.
# Required: tutor name, student name, subject, hourly rate, start date, status
# Optional: level, contact email

# Column resolution handles variants like:
# "Hourly Rate (SGD)", "hourly_rate", "Rate" - canonical "hourly rate"
# "Start Date", "start_date" - canonical "start date"
def validate_tutor_assignments(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    df = drop_blank_rows(df)
    df = drop_decorative_rows(df)
    df = df.reset_index(drop=True)

    # Resolve actual column names to canonical names once, before the row loop
    col_map = resolve_columns(list(df.columns), EXPECTED_COLUMNS["tutor_assignments"])

    clean_rows: list[dict] = []
    quarantine: list[dict] = []

    for i, raw in enumerate(df.to_dict(orient="records")):
        row_num = i + 2  # +1 for 1-based, +1 for header row
        errors: list[dict] = []

        tutor_name    = clean_text(rget(raw, col_map, "tutor name"))
        student_name  = clean_text(rget(raw, col_map, "student name"))
        subject       = clean_text(rget(raw, col_map, "subject"))
        level         = clean_text(rget(raw, col_map, "level"))
        contact_email = clean_text(rget(raw, col_map, "contact email"))

        raw_rate    = rget(raw, col_map, "hourly rate")
        hourly_rate = parse_numeric(raw_rate)

        raw_date   = rget(raw, col_map, "start date")
        start_date = parse_date(raw_date)

        raw_status = rget(raw, col_map, "status")
        status     = normalise_status(raw_status, CANONICAL_STATUS["tutor_assignments"])

        # Required field checks - tutor, student, subject, hourly rate, start date, status
        for field, val in [("tutor name", tutor_name), 
                           ("student name", student_name), 
                           ("subject", subject),
                           ]:
            if val is None:
                errors.append(_quarantine_entry(row_num, raw,
                    "MISSING_REQUIRED_FIELD", f"Field '{field}' is blank or null (row {row_num})",))

        if start_date is None:
            errors.append(_date_error("start date", raw_date, row_num, raw))

        if hourly_rate is None:
            errors.append(_numeric_error("hourly rate", raw_rate, row_num, raw))

        if status is None:
            errors.append(_status_error(
                "status", raw_status, row_num, raw, CANONICAL_STATUS["tutor_assignments"],
            ))

        if errors:
            quarantine.extend(errors)
        else:
            clean_rows.append({
                "tutor_name": tutor_name,
                "student_name": student_name,
                "subject": subject,
                "level": level,
                "hourly_rate": hourly_rate,
                "start_date": start_date,
                "status": status,
                "contact_email": contact_email,
            })

    return pd.DataFrame(clean_rows), quarantine

# Clean and validate lesson_logs_messy.xlsx rows.
# Required: assignment id, date, duration, attendance
# Optional: lesson id, notes, fee

# Edge cases:
# - TBC / N/A in duration treated as missing (MISSING_REQUIRED_FIELD), not INVALID_NUMERIC
# - "0" fee is a valid zero — excluded from MISSING_SENTINELS check
# - lesson id optional because the file may have no header row
def validate_lesson_logs(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    df = drop_blank_rows(df)
    df = drop_decorative_rows(df)
    df = df.reset_index(drop=True)

    col_map = resolve_columns(list(df.columns), EXPECTED_COLUMNS["lesson_logs"])

    clean_rows: list[dict] = []
    quarantine: list[dict] = []

    for i, raw in enumerate(df.to_dict(orient="records")):
        row_num = i + 2
        errors: list[dict] = []

        lesson_id     = clean_text(rget(raw, col_map, "lesson id"))
        assignment_id = clean_text(rget(raw, col_map, "assignment id"))
        notes         = clean_text(rget(raw, col_map, "notes"))

        raw_date   = rget(raw, col_map, "date")
        date       = parse_date(raw_date)

        raw_attendance = rget(raw, col_map, "attendance")
        attendance     = normalise_status(raw_attendance, CANONICAL_STATUS["lessons_attendance"])

        # Duration: TBC / N/A → MISSING, not INVALID_NUMERIC
        raw_duration = rget(raw, col_map, "duration")
        duration_str = str(raw_duration).strip().lower() if pd.notna(raw_duration) else ""
        if duration_str in MISSING_SENTINELS or duration_str == "":
            duration = None
        else:
            duration = parse_numeric(raw_duration)

        # Fee: "0" is a valid zero — exclude it from the sentinel check
        raw_fee = rget(raw, col_map, "fee")
        fee_str = str(raw_fee).strip().lower() if pd.notna(raw_fee) else ""
        if fee_str in (MISSING_SENTINELS - {"0"}) or fee_str == "":
            fee = None
        else:
            fee = parse_numeric(raw_fee)

        # Required field checks - assignment id, date, duration, attendance
        if assignment_id is None:
            errors.append(_quarantine_entry(
                row_num, raw,"MISSING_REQUIRED_FIELD",
                f"Field 'assignment id' is blank or null (row {row_num})",
            ))

        if date is None:
            errors.append(_date_error("date", raw_date, row_num, raw))

        if duration is None:
            if pd.notna(raw_duration) and duration_str not in MISSING_SENTINELS:
                errors.append(_numeric_error("duration", raw_duration, row_num, raw))
            else:
                errors.append(_quarantine_entry(
                    row_num, raw, "MISSING_REQUIRED_FIELD", f"Field 'duration' is blank or null (row {row_num})",
                ))

        if attendance is None:
            errors.append(_status_error(
                "attendance", raw_attendance, row_num, raw, CANONICAL_STATUS["lessons_attendance"],
            ))

        if errors:
            quarantine.extend(errors)
        else:
            clean_rows.append({
                "lesson_id": lesson_id,
                "assignment_id": assignment_id,
                "date": date,
                "duration": duration,
                "attendance": attendance,
                "notes": notes,
                "fee": fee
            })

    return pd.DataFrame(clean_rows), quarantine

# Clean and validate invoice_export_q1.xlsx rows.
# Required: invoice id, tutor id, student_name, invoice date, amount, payment status
# Optional: payment date, notes

# Edge cases:
# - 'SGD ' prefix on amount values — stripped by parse_numeric
# - Trailing-space status like 'Pending ' — caught by normalise_status's strip
def validate_invoices (df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:

    df = drop_blank_rows(df)
    df = drop_decorative_rows(df)
    df = df.reset_index(drop=True)

    col_map = resolve_columns(list(df.columns), EXPECTED_COLUMNS["invoice"])

    clean_rows: list[dict] = []
    quarantine: list[dict] = []

    for i, raw in enumerate(df.to_dict(orient="records")):
        row_num = i + 2
        errors: list[dict] = []

        invoice_id   = clean_text(rget(raw, col_map, "invoice id"))
        tutor_id     = clean_text(rget(raw, col_map, "tutor id"))
        student_name = clean_text(rget(raw, col_map, "student name"))
        notes        = clean_text(rget(raw, col_map, "notes"))

        raw_date     = rget(raw, col_map, "invoice date")
        invoice_date = parse_date(raw_date)

        raw_pdate    = rget(raw, col_map, "payment date")
        payment_date = parse_date(raw_pdate)

        raw_amount   = rget(raw, col_map, "amount")
        amount       = parse_numeric(raw_amount)

        raw_status   = rget(raw, col_map, "payment status")
        status       = normalise_status(raw_status, CANONICAL_STATUS["invoice"])

        # --- Required field checks ---
        for field, val in [
            ("invoice id", invoice_id),
            ("tutor id", tutor_id),
            ("student name", student_name),
        ]:
            if val is None:
                errors.append(_quarantine_entry(
                    row_num, raw,
                    "MISSING_REQUIRED_FIELD", f"Field '{field}' is blank or null (row {row_num})",
                ))

        if invoice_date is None:
            errors.append(_date_error("invoice date", raw_date, row_num, raw))

        if amount is None:
            errors.append(_numeric_error("amount", raw_amount, row_num, raw))

        if status is None:
            errors.append(_status_error(
                "payment status", raw_status, row_num, raw, CANONICAL_STATUS["invoice"]))

        if errors:
            quarantine.extend(errors)
        else:
            clean_rows.append({
                "invoice_id": invoice_id,
                "tutor_id": tutor_id,
                "student_name": student_name,
                "invoice_date": invoice_date,
                "amount": amount,
                "status": status,
                "payment_date": payment_date,
                "notes": notes,
            })

    return pd.DataFrame(clean_rows), quarantine


# Dispatch table — pipeline.py uses this to call the right validator

VALIDATORS: dict[str, callable] = {
    "tutor_assignments": validate_tutor_assignments,
    "lesson_logs": validate_lesson_logs,
    "invoice": validate_invoices
}