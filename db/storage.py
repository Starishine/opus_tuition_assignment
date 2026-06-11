"""
storage.py - handles database reads and writes for the pipeline.
Responsibilities:
- Defines functions to write clean data and quarantine entries to the database.
"""

import logging
import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import pandas as pd

load_dotenv(override=True)
logger = logging.getLogger("data_pipeline.storage")

TABLE_MAP = {
    "tutor_assignments": "assignments",
    "lesson_logs": "lesson_logs",
    "invoice": "invoices",
}

# Database connection parameters from environment variables
def get_connection(): 
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# duplicate file upload check 
def check_duplicate_hash(file_hash: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT upload_id FROM uploads WHERE file_hash = %s", (file_hash,))
    row = cur.fetchone()
    return row[0] if row else None

# insert statements
def insert_uploads(upload_id: str, file_name: str, result: dict) -> tuple[str, str, int, int, int, list[dict]]: 
    file_type = result.get("file_type")
    clean_df = result.get("clean_df")
    quarantine = result.get("quarantine")
    rows_received = result.get("rows_received")
    rows_accepted = result.get("rows_accepted")
    rows_quarantined = result.get("rows_quarantined")

    try: 
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO uploads (upload_id, file_name, file_type, file_hash, rows_received,
            rows_accepted, rows_quarantined) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                upload_id,
                file_name,
                file_type,
                result.get("file_hash"),
                rows_received,
                rows_accepted,
                rows_quarantined
            )
        )

        if file_type == "tutor_assignments":
            insert_assignments(cur, upload_id, clean_df)
        elif file_type == "lesson_logs":
            late_quarantine = insert_lessons(cur, upload_id, clean_df)
            quarantine.extend(late_quarantine)
            rows_accepted = result.get("rows_accepted") - len(late_quarantine)
            rows_quarantined = result.get("rows_quarantined") + len(late_quarantine)

            cur.execute(""" UPDATE uploads SET rows_accepted = %s, rows_quarantined = %s WHERE upload_id = %s""", (
                rows_accepted,
                rows_quarantined,
                upload_id
             )
            )
        elif file_type == "invoice":
            late_quarantine = insert_invoices(cur, upload_id, clean_df)
            quarantine.extend(late_quarantine)
            rows_accepted = result.get("rows_accepted") - len(late_quarantine)
            rows_quarantined = result.get("rows_quarantined") + len(late_quarantine)

            cur.execute(""" UPDATE uploads SET rows_accepted = %s, rows_quarantined = %s WHERE upload_id = %s""", (
                rows_accepted,
                rows_quarantined,
                upload_id
             )
            )

        if quarantine:
            insert_quarantine(cur, upload_id, file_type, quarantine)
            insert_aliases(cur, quarantine, file_type)
        conn.commit()
        logger.info(
            "Upload saved to database",
            extra={"stage": "storage", "upload_id": upload_id, "file_type": file_type},
        )
    except Exception as e:
        logger.error(
            "Database write failed — transaction rolled back",
            extra={"stage": "storage", "upload_id": upload_id, "error": str(e)},
        )
        raise
    return {"upload_id": upload_id, 
            "file_type": file_type, 
            "rows_received": rows_received,
            "rows_accepted": rows_accepted, 
            "rows_quarantined": rows_quarantined,
            "quarantine": quarantine
            }


def insert_assignments(cur, upload_id, df):
    records = df.to_dict(orient="records")
    for row in records:
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        tutor_id = get_or_create_tutor(cur, row.get("tutor_name"), row.get("contact_email"))
        student_id = get_or_create_student(cur, row.get("student_name"), row.get("level"))
        source_id = row.get("assignment_id")
        subject = row.get("subject")
        start_date = row.get("start_date")
        hourly_rate = row.get("hourly_rate")
        status = row.get("status")

        cur.execute ("""
        INSERT INTO assignments (source_id, upload_id, tutor_id, student_id, subject, start_date, hourly_rate, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT(tutor_id, student_id, subject, start_date) DO UPDATE SET
            source_id = EXCLUDED.source_id,
            upload_id = EXCLUDED.upload_id,
            hourly_rate = EXCLUDED.hourly_rate,
            status = EXCLUDED.status
        """, (
            source_id,
            upload_id,
            tutor_id,
            student_id,
            subject,
            start_date,
            hourly_rate,
            status
         ))


def get_or_create_tutor(cur, tutor_name, tutor_email):
    cur.execute("""SELECT tutor_id FROM tutors WHERE tutor_name = %s""", (tutor_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    else:
        cur.execute(
            """INSERT INTO tutors (tutor_name, tutor_email) VALUES (%s, %s) 
            ON CONFLICT (tutor_name, tutor_email) DO UPDATE SET tutor_email = EXCLUDED.tutor_email
            RETURNING tutor_id""",
            (tutor_name, tutor_email)
        )
        return cur.fetchone()[0]
    
def get_or_create_student(cur, student_name, level):
    cur.execute("""SELECT student_id FROM students WHERE student_name = %s AND level = %s""", (student_name, level))
    row = cur.fetchone()
    if row:
        return row[0]
    else:
        cur.execute(
            """INSERT INTO students (student_name, level) VALUES (%s, %s) 
            ON CONFLICT (student_name, level) DO UPDATE SET level = EXCLUDED.level
            RETURNING student_id""",
            (student_name, level)
        )
        return cur.fetchone()[0]


def insert_lessons(cur, upload_id, df) -> list[dict]:
    # Precheck for assignmets 
    cur.execute(""" SELECT COUNT(*) FROM assignments """)
    total_assignments = cur.fetchone()[0]
    if total_assignments == 0:
        raise ValueError(
            "No assignments found in database. Upload the tutor assignments file before uploading lesson logs."
        )
    
    late_quarantine = [] 
    records = df.to_dict(orient="records")
    for row in records:
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        source_id = row.get("lesson_id")
        assignment_id = row.get("assignment_id")
        date = row.get("date")
        duration = row.get("duration")
        attendance = row.get("attendance")
        notes = row.get("notes")
        row_number = row.get("row_number")
        raw_data = row.get("raw_data")

        resolved_assignment_id = resolve_assignment_id(cur, assignment_id)

        if resolved_assignment_id is None:
            late_quarantine.append({
                "row_number": row_number,
                "reason_code": "UNRESOLVED_ASSIGNMENT_ID",
                "reason_detail": (
                    f"Assignment '{assignment_id}' does not exist in the database. "
                    f"The assignment row may have been quarantined during its upload "
                    f"(e.g. missing required field), or the assignments file has not "
                    f"been uploaded yet. Upload or fix the assignment first, then re-upload this file."
                ),
                "raw_data": raw_data,
            })
            continue

        cur.execute ("""
        INSERT INTO lessons (source_id, upload_id, assignment_id, date, duration, attendance, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (assignment_id, date, duration) DO UPDATE SET
            source_id = EXCLUDED.source_id,
            upload_id = EXCLUDED.upload_id,
            attendance = EXCLUDED.attendance,
            notes = EXCLUDED.notes
         """, (
            source_id, upload_id, resolved_assignment_id, date, duration,
            attendance, notes
         )) 
    return late_quarantine
        

def insert_invoices(cur, upload_id, df) -> list[dict]:
    # Precheck for assignmets 
    cur.execute(""" SELECT COUNT(*) FROM assignments """)
    total_assignments = cur.fetchone()[0]
    if total_assignments == 0:
        raise ValueError(
            "No assignments found in database. Upload the tutor assignments file before uploading lesson logs."
        )
    
    late_quarantine = []
    records = df.to_dict(orient="records")
    for row in records:
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        student_id = get_student_id(cur, row.get("student_name"))
        raw_data = row.get("raw_data")
        if student_id is None:
            late_quarantine.append({
                "row_number": row.get("row_number"),
                "reason_code": "UNRESOLVED_STUDENT_NAME",
                "reason_detail": (
                    f"Student '{row.get('student_name')}' does not exist in the database. "
                    f"The student may be referenced in the assignments file but that file has not "
                    f"been uploaded yet, or the student row in the assignments file was quarantined "
                    f"(e.g. missing required field). Upload or fix the assignments file first, then re-upload this file."
                ),
                "raw_data": raw_data,
            })
            continue

        source_id = row.get("invoice_id")
        assignment_id = row.get("assignment_id")
        invoice_date = row.get("invoice_date")
        payment_status = row.get("status")
        payment_date = row.get("payment_date")
        notes = row.get("notes")
        row_number = row.get("row_number")
        raw_data = row.get("raw_data")

        resolved_assignment_id = resolve_assignment_id(cur, assignment_id)
        if resolved_assignment_id is None:
            late_quarantine.append({
                "row_number": row_number,
                "reason_code": "UNRESOLVED_ASSIGNMENT_ID",
                "reason_detail": (
                    f"Assignment '{assignment_id}' does not exist in the database. "
                    f"The assignment row may have been quarantined during its upload "
                    f"(e.g. missing required field), or the assignments file has not "
                    f"been uploaded yet. Upload or fix the assignment first, then re-upload this file."
                ),
                "raw_data": raw_data,
            })
            continue
        cur.execute ("""
        INSERT INTO invoices (source_id, upload_id, assignment_id, student_id, invoice_date, payment_status, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (assignment_id, invoice_date, amount) DO UPDATE SET
            source_id = EXCLUDED.source_id,
            assignment_id = EXCLUDED.assignment_id,
            student_id = EXCLUDED.student_id,
            payment_status = EXCLUDED.payment_status,
            payment_date = EXCLUDED.payment_date,
            notes = EXCLUDED.notes
        """, (
            source_id,
            upload_id,
            resolved_assignment_id,
            student_id,
            invoice_date,
            payment_status,
            payment_date,
            notes
         ))
    return late_quarantine

def get_student_id(cur, student_name):
    cur.execute("""SELECT student_id FROM students WHERE student_name = %s""", (student_name,))
    row = cur.fetchone()
    return row[0] if row else None

def insert_quarantine(cur, upload_id, file_type, quarantine):
    for entry in quarantine:
        cur.execute("""
            INSERT INTO quarantine
                (upload_id, file_type, row_number, reason_code, reason_detail, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (upload_id, file_type, row_number) DO UPDATE SET
                reason_code = EXCLUDED.reason_code,
                reason_detail = EXCLUDED.reason_detail,
                raw_data = EXCLUDED.raw_data
        """, (
            upload_id,
            file_type,
            entry.get("row_number"),
            entry.get("reason_code"),
            entry.get("reason_detail"),
            json.dumps(entry.get("raw_data", {}), default=str),
        ))

def insert_aliases(cur, quarantine: list[dict], file_type: str):
    for entry in quarantine:
        if entry.get("reason_code") != "DUPLICATE_RECORD":
            continue
        alias_id = entry.get("alias_id")
        canonical_id = entry.get("canonical_id")
        if alias_id and canonical_id:
            # using ON CONFLICT DO NOTHING to avoid duplicate alias entries if the same duplicate appears multiple times in the file
            cur.execute("""
                INSERT INTO source_id_aliases (alias_id, canonical_id, file_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (alias_id, file_type) DO NOTHING
            """, 
            (alias_id,
            canonical_id,
            file_type
            ))
    
def resolve_assignment_id(cur, source_id: str) -> str | None:
    # Look up the assignment_id in the assignments table
    cur.execute("""SELECT source_id FROM assignments WHERE source_id = %s""", (source_id,))

    if cur.fetchone():
        return source_id
    # If not found, look for an alias in the aliases table
    cur.execute("""SELECT canonical_id FROM source_id_aliases WHERE alias_id = %s """, (source_id,))
    row = cur.fetchone()
    if row: 
        logger.info(
            "Resolved assignment alias",
            extra={"alias": source_id, "canonical": row[0], "stage": "storage"}
        )
        return row[0]
    return None

# Returns all uploaded files, ordered by most recent upload first
def get_all_uploads() -> list[dict]:
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""SELECT upload_id, file_name, file_type, uploaded_at, rows_received, rows_accepted, rows_quarantined 
                    FROM uploads 
                    ORDER BY uploaded_at DESC""")
    return [dict(row) for row in cur.fetchall()]


# Returns detailed report for a specific upload_id, including quarantine breakdown and raw data for quarantined rows
def get_report_by_upload_id(upload_id: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(""" SELECT * FROM uploads WHERE upload_id = %s """, (upload_id,))
    upload_row = cur.fetchone()
    if not upload_row:
        return None
    
    # Get quarantine entries for this upload
    cur.execute("""
                SELECT reason_code, COUNT(*) as count
                FROM quarantine
                WHERE upload_id = %s
                GROUP BY reason_code ORDER BY count DESC
            """, (upload_id,))
    breakdown = [dict(row) for row in cur.fetchall()]
    
    quarantine_rows = get_quarantine(upload_id)
    
    return {
        **dict(upload_row),
        "quarantine_breakdown": breakdown,
        "quarantine_rows": quarantine_rows
    }

def get_records(file_type: str, upload_id: str = None, date_from: str = None, date_to: str = None) -> list[dict]:
    params = []
    conditions = []
    if file_type == "tutor_assignments":
        base = """
            SELECT a.source_id AS assignment_id, a.upload_id,
                   t.tutor_name, t.tutor_email,
                   s.student_name, s.level,
                   a.subject, a.start_date, a.hourly_rate, a.status
            FROM assignments a
            JOIN tutors t ON t.tutor_id = a.tutor_id
            JOIN students s ON s.student_id = a.student_id
        """
        date_col = "a.start_date"
        upload_prefix = "a"

    elif file_type == "lesson_logs":
        base = """
            SELECT l.source_id AS lesson_id, l.upload_id,
                   l.assignment_id, l.date, l.duration,
                   l.attendance, l.notes
            FROM lessons l
        """
        date_col = "l.date"
        upload_prefix = "l"

    elif file_type == "invoice":
        base = """
            SELECT i.source_id AS invoice_id, i.upload_id,
                   i.assignment_id, s.student_name,
                   i.invoice_date, i.payment_status, i.payment_date, i.notes
            FROM invoices i
            JOIN students s ON s.student_id = i.student_id
        """
        date_col = "i.invoice_date"
        upload_prefix = "i"
    else:
        return []

    if upload_id:
        conditions.append(f"{upload_prefix}.upload_id = %s")
        params.append(upload_id)
    if date_from:
        conditions.append(f"{date_col} >= %s")
        params.append(date_from)
    if date_to:
        conditions.append(f"{date_col} <= %s")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"{base} {where} ORDER BY 1"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) 
    cur.execute(query, params)
    return [dict(r) for r in cur.fetchall()]
        
def get_quarantine(upload_id: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) 
    cur.execute("""
                SELECT row_number, reason_code, reason_detail, raw_data
                FROM quarantine WHERE upload_id = %s
                ORDER BY row_number
            """, (upload_id,))
    return [dict(r) for r in cur.fetchall()]

def delete_upload_api(upload_id: str): 
    conn = get_connection()
    cur = conn.cursor()
    TABLE_MAP = {
            "tutor_assignments": "assignments",
            "lesson_logs": "lessons", 
            "invoice": "invoices",
        }
    
    cur.execute("""SELECT file_type FROM uploads WHERE upload_id = %s""", (upload_id,))
    row = cur.fetchone()
    if not row:
        return False
    file_type = row[0]
    table_name = TABLE_MAP.get(file_type)

    if table_name == "assignments":
        # Check if any lessons or invoices are linked to this assignment
        cur.execute("""
            SELECT COUNT(*) FROM lessons WHERE assignment_id IN (
                SELECT source_id FROM assignments WHERE upload_id = %s
            )
        """, (upload_id,))
        linked_lessons = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM invoices WHERE assignment_id IN (
                SELECT source_id FROM assignments WHERE upload_id = %s
            )
        """, (upload_id,))
        linked_invoices = cur.fetchone()[0]

        if linked_lessons > 0 or linked_invoices > 0:
            # We raise a specific ValueError so the route can catch it easily
                raise ValueError(
                    f"DEPENDENCY_ERROR: Cannot delete this assignments file. "
                    f"It is currently linked to {linked_lessons} lesson(s) and {linked_invoices} invoice(s). "
                    f"Please delete the dependent Lesson Logs and Invoices files first."
                )
    if table_name:
        cur.execute(f"""DELETE FROM {table_name} WHERE upload_id = %s""", (upload_id,))
    cur.execute("""DELETE FROM quarantine WHERE upload_id = %s""", (upload_id,))
    cur.execute("""DELETE FROM uploads WHERE upload_id = %s""", (upload_id,))

    deleted = cur.rowcount > 0 
    conn.commit()
    return deleted
