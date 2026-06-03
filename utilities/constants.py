# Constants for the pipeline and data validation

EXPECTED_COLUMNS: dict[str, list[str]] = {
    "tutor_assignments": [
        "assignment id", "tutor name", "student name", "subject", "level", 
        "hourly rate","start date","status","contact email" 
    ], 

    "lessons": [
        "lesson id", "assignment id", "date", "duration",
        "attendance", "notes", "fee"
    ], 

    "invoice" : [
        "invoice id", "tutor id", "student name", "invoice date",
        "amount", "payment status", "payment date", "notes"
    ]
}

STATUS_COLUMNS: dict[str, list[str]] = {
    "tutor_assignments": ["active", "inactive", "pending"],
    "lessons": ["present", "absent", "late"],
    "invoice": ["paid", "unpaid", "pending"]
}

DATE_FORMATS: list[str] = [
    "%Y-%m-%d",   # ISO 8601        — 2024-01-15
    "%d/%m/%Y",   # UK slash        — 15/01/2024
    "%m/%d/%Y",   # US slash        — 01/15/2024
    "%d-%m-%Y",   # UK dash         — 15-01-2024
    "%d %b %Y",   # Day-Mon-Year    — 15 Jan 2024
    "%d %B %Y",   # Day-Month-Year  — 15 January 2024
    "%b %d, %Y",  # Mon Day, Year   — Jan 15, 2024
    "%d/%m/%y",   # Two-digit year  — 15/01/24
]



