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

load_dotenv()
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
def insert_uploads(upload_id: str, file_name: str, result: dict) -> None: 
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
            insert_lessons(cur, upload_id, clean_df)
        elif file_type == "invoice":
            insert_invoices(cur, upload_id, clean_df)

        if quarantine:
            insert_quarantine(cur, upload_id, file_type, quarantine)
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


def insert_assignments(cur, upload_id, df):
    for _, row in df.iterrows():
        tutor_id = get_or_create_tutor(cur, row.get("tutor_name"), row.get("contact_email"))
        student_id = get_or_create_student(cur, row.get("student_name"), row.get("level"))
        source_id = row.get("assignment_id")
        subject = row.get("subject")
        start_date = row.get("start_date")
        hourly_rate = row.get("hourly_rate")
        status = row.get("status")

        cur.execute ("""
        INSERT INTO assignments (source_id, upload_id, tutor_id, student_id, subject, start_date, hourly_rate, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
    cur.execute("""SELECT tutor_id FROM tutors WHERE tutor_name = %s AND tutor_email = %s""", (tutor_name, tutor_email))
    row = cur.fetchone()
    if row:
        return row[0]
    else:
        cur.execute(
            """INSERT INTO tutors (tutor_name, tutor_email) VALUES (%s, %s) RETURNING tutor_id""",
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
            """INSERT INTO students (student_name, level) VALUES (%s, %s) RETURNING student_id""",
            (student_name, level)
        )
        return cur.fetchone()[0]


def insert_lessons(cur, upload_id, df) -> None:
    for _, row in df.iterrows():
        source_id = row.get("lesson_id")
        assignment_id = row.get("assignment_id")
        date = row.get("date")
        duration = row.get("duration")
        attendance = row.get("attendance")
        notes = row.get("notes")

        cur.execute ("""
        INSERT INTO lessons (source_id, upload_id, assignment_id, date, duration, attendance, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            source_id,
            upload_id,
            assignment_id,
            date,
            duration,
            attendance,
            notes
         )) 

def insert_invoices(cur, upload_id, df) -> None:
    for _, row in df.iterrows():
        source_id = row.get("invoice_id")
        assignment_id = row.get("assignment_id")
        student_id = get_student_id(cur, row.get("student_name"), row.get("level"))
        invoice_date = row.get("invoice_date")
        payment_status = row.get("status")
        payment_date = row.get("payment_date")
        notes = row.get("notes")

        cur.execute ("""
        INSERT INTO invoices (source_id, upload_id, assignment_id, student_id, invoice_date, payment_status, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            source_id,
            upload_id,
            assignment_id,
            student_id,
            invoice_date,
            payment_status,
            payment_date,
            notes
         ))

def get_student_id(cur, student_name, level):
    cur.execute("""SELECT student_id FROM students WHERE student_name = %s AND level = %s""", (student_name, level))
    row = cur.fetchone()
    return row[0] if row else None

def insert_quarantine(cur, upload_id, file_type, quarantine):
    for entry in quarantine:
        cur.execute("""
            INSERT INTO quarantine
                (upload_id, file_type, row_number, reason_code, reason_detail, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            upload_id,
            file_type,
            entry.get("row_number"),
            entry.get("reason_code"),
            entry.get("reason_detail"),
            json.dumps(entry.get("raw_data", {}), default=str),
        ))
