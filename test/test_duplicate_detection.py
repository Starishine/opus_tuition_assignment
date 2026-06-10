import pandas as pd
import pytest

from utilities.deduplicator import detect_duplicates

class TestDuplicateDetection:
    def make_df(self, rows: list[dict]) -> pd.DataFrame:
        records = []
        for i, r in enumerate(rows):
            r["row_number"] = i + 2
            r["raw_data"] = dict(r)
            records.append(r)
        return pd.DataFrame(records)
    
    def test_assignments_no_duplicates(self):
        df = self.make_df([
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"},
            {"assignment_id": "TAS-002", "tutor_name": "T2", "student_name": "S2", "level": "Primary 2", "subject": "English", "contact_email" : "t2@example.com"}
        ])
        clean_df, quarantine = detect_duplicates(df, "tutor_assignments")
        assert len(clean_df) == 2
        assert len(quarantine) == 0
    
    # Two records with exact same row
    def test_assignments_with_duplicates(self):
        df = self.make_df([
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"},
            {"assignment_id": "TAS-002", "tutor_name": "T2", "student_name": "S2", "level": "Primary 2", "subject": "English", "contact_email" : "t2@example.com"},
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"}
        ])
        clean_df, quarantine = detect_duplicates(df, "tutor_assignments")
        assert len(clean_df) == 2
        assert len(quarantine) == 1
        assert quarantine[0]["reason_code"] == "DUPLICATE_RECORD"

    # Keeps the first occurrence and marks subsequent ones as duplicates
    def test_assignments_keeps_first_occurrence(self):
        df = self.make_df([
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"},
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"}
        ])
        clean_df, quarantine = detect_duplicates(df, "tutor_assignments")
        assert len(clean_df) == 1
        assert clean_df.iloc[0]["row_number"] == 2
        assert len(quarantine) == 1
    
    # 1st and 3rd rows are the same, 2nd and 4th rows are the same although they have different assignment_id. We should detect both as duplicates and keep the first occurrence of each.
    def test_assignments_with_mutiple_duplicates(self):
        df = self.make_df([
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"},
            {"assignment_id": "TAS-002", "tutor_name": "T2", "student_name": "S2", "level": "Primary 2", "subject": "English", "contact_email" : "t2@example.com"},
            {"assignment_id": "TAS-001", "tutor_name": "T1", "student_name": "S1", "level": "Primary 1", "subject": "Math", "contact_email" : "t1@example.com"},
            {"assignment_id": "TAS-003", "tutor_name": "T2", "student_name": "S2", "level": "Primary 2", "subject": "English", "contact_email" : "t2@example.com"},
        ])
        clean_df, quarantine = detect_duplicates(df, "tutor_assignments")
        assert len(clean_df) == 2
        assert len(quarantine) == 2
        assert quarantine[0]["reason_code"] == "DUPLICATE_RECORD"
        assert quarantine[1]["reason_code"] == "DUPLICATE_RECORD"
        assert quarantine[0]["alias_id"] == "TAS-001"
        assert quarantine[0]["canonical_id"] == "TAS-001"
        assert quarantine[1]["alias_id"] == "TAS-003"
        assert quarantine[1]["canonical_id"] == "TAS-002"

    def test_invoice_no_duplicates(self):
        df = self.make_df([
            {"invoice_id": "INV-001", "assignment_id": "TAS-001", "student_name": "S1", "invoice_date": "2026-06-10", "payment_date": "2026-06-10", "amount": 100.0, "status": "paid"},
            {"invoice_id": "INV-002", "assignment_id": "TAS-002", "student_name": "S2", "invoice_date": "2026-06-11", "payment_date": "2026-06-11", "amount": 150.0, "status": "pending"}
        ])
        clean_df, quarantine = detect_duplicates(df, "invoice")
        assert len(clean_df) == 2
        assert len(quarantine) == 0

    def test_invoice_with_multiple_duplicates(self):
        df = self.make_df([
            {"invoice_id": "INV-001", "assignment_id": "TAS-001", "student_name": "S1", "invoice_date": "2026-06-10", "payment_date": "2026-06-10", "amount": 100.0, "status": "paid"},
            {"invoice_id": "INV-002", "assignment_id": "TAS-002", "student_name": "S2", "invoice_date": "2026-06-11", "payment_date": "2026-06-11", "amount": 150.0, "status": "pending"},
            {"invoice_id": "INV-001", "assignment_id": "TAS-001", "student_name": "S1", "invoice_date": "2026-06-10", "payment_date": "2026-06-10", "amount": 100.0, "status": "paid"},
            {"invoice_id": "INV-003", "assignment_id": "TAS-002", "student_name": "S2", "invoice_date": "2026-06-11", "payment_date": "2026-06-11", "amount": 150.0, "status": "pending"}
        ])
        clean_df, quarantine = detect_duplicates(df, "invoice")
        assert len(clean_df) == 2
        assert len(quarantine) == 2
        assert quarantine[0]["reason_code"] == "DUPLICATE_RECORD"
        assert quarantine[1]["reason_code"] == "DUPLICATE_RECORD"
        assert quarantine[0]["alias_id"] == "INV-001"
        assert quarantine[0]["canonical_id"] == "INV-001"
        assert quarantine[1]["alias_id"] == "INV-003"
        assert quarantine[1]["canonical_id"] == "INV-002"