DROP TABLE assignments; 
DROP TABLE invoices; 
DROP TABLE lessons; 
DROP TABLE quarantine; 
DROP TABLE students; 
DROP TABLE tutors; 
DROP TABLE uploads;


CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    upload_id TEXT UNIQUE NOT NULL,
    file_name TEXT,
    file_type TEXT,
    file_hash TEXT UNIQUE NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    rows_received INT,
    rows_accepted INT,
    rows_quarantined INT
);

CREATE TABLE IF NOT EXISTS tutors (
    tutor_id SERIAL PRIMARY KEY,
    tutor_name TEXT NOT NULL,
    tutor_email TEXT,
    UNIQUE(tutor_name, tutor_email)
);

CREATE TABLE IF NOT EXISTS students (
    student_id SERIAL PRIMARY KEY,
    student_name TEXT NOT NULL,
    level TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    assignment_id SERIAL PRIMARY KEY, -- internal db id key
    source_id TEXT UNIQUE NOT NULL, -- excel key
    upload_id TEXT NOT NULL REFERENCES uploads(upload_id),
    tutor_id INTEGER NOT NULL REFERENCES tutors(tutor_id),
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    subject TEXT NOT NULL, 
    start_date DATE NOT NULL,
    hourly_rate FLOAT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE(tutor_id, student_id, subject, start_date)
);

CREATE TABLE IF NOT EXISTS lessons (
    lesson_id SERIAL PRIMARY KEY,
    source_id TEXT UNIQUE NOT NULL,
    upload_id TEXT NOT NULL REFERENCES uploads(upload_id),
    assignment_id TEXT NOT NULL REFERENCES assignments(source_id),
    date DATE NOT NULL,
    duration FLOAT NOT NULL, 
    attendance TEXT NOT NULL, 
    notes TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id SERIAL PRIMARY KEY,
    source_id TEXT UNIQUE NOT NULL,
    upload_id TEXT NOT NULL REFERENCES uploads(upload_id),
    assignment_id TEXT NOT NULL REFERENCES assignments(source_id),
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    invoice_date DATE NOT NULL,
    payment_status TEXT NOT NULL,
    payment_date DATE, 
    notes TEXT
);

CREATE TABLE IF NOT EXISTS quarantine (
    id SERIAL PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(upload_id),
    file_type TEXT NOT NULL,
    row_number INT NOT NULL,
    reason_code TEXT NOT NULL,
    reason_detail TEXT NOT NULL,
    raw_data JSONB 
);