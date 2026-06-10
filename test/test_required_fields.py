import pandas as pd
import pytest

from utilities.validator import validate_tutor_assignments

class TestRequiredFields:
    def valid_assignment_df(self, overrides: dict = {}) -> pd.DataFrame:
        base_data = {
            "assignment_id": "TAS-001",
            "tutor_name": "T1",
            "student_name": "S1",
            "level": "Primary 1",
            "subject": "Math",
            "hourly_rate": 30.0,
            "start_date": "2026-06-10",
            "status": "Active",
            "contact_email": "t1@example.com"
        }
        base_data.update(overrides)
        return pd.DataFrame([base_data])
    
    def test_valid_assignment(self):
        df = self.valid_assignment_df()
        clean_df, quarantine = validate_tutor_assignments(df)
        assert len(clean_df) == 1
        assert len(quarantine) == 0

    def test_assignment_missing_tutor_name(self):
        df = self.valid_assignment_df({"tutor_name": None})
        clean_df, quarantine = validate_tutor_assignments(df)
        assert len(clean_df) == 0
        assert len(quarantine) == 1
        assert quarantine[0]["reason_code"] == "MISSING_REQUIRED_FIELD"
        assert "tutor name" in quarantine[0]["reason_detail"]
    
    def test_assignment_missing_multiple_fields(self):
        df = self.valid_assignment_df({"tutor_name": None, "student_name": None})
        clean_df, quarantine = validate_tutor_assignments(df)
        assert len(clean_df) == 0
        assert len(quarantine) == 2
        assert quarantine[0]["reason_code"] == "MISSING_REQUIRED_FIELD"
        assert "tutor name" in quarantine[0]["reason_detail"]
        assert "student name" in quarantine[1]["reason_detail"]