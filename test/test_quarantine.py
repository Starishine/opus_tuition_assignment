import pandas as pd
import pytest

from utilities.validator import validate_tutor_assignments

class TestQuarantineWithReasonSpecificity:

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

    def test_missing_field_detail_names_the_field(self):
        df = self.valid_assignment_df({"tutor_name": None})
        clean_df, quarantine = validate_tutor_assignments(df)
        assert "MISSING_REQUIRED_FIELD" in quarantine[0]["reason_code"]
        assert "Field 'tutor name' is blank or null (row 2)" in quarantine[0]["reason_detail"]
    
    def test_invalid_status_includes_received_and_expected_values(self):
        df = self.valid_assignment_df({"status": "UnknownStatus"})
        clean_df, quarantine = validate_tutor_assignments(df)
        assert "INVALID_STATUS" in quarantine[0]["reason_code"]
        assert "received \"UnknownStatus\"" in quarantine[0]["reason_detail"]
        assert "expected one of [\'active\', \'inactive\', \'pending\'] (row 2)" in quarantine[0]["reason_detail"]

    def test_invalid_numeric_detail_includes_field_and_raw_value(self):
        df = self.valid_assignment_df({"hourly_rate": "Thirty"})
        clean_df, quarantine = validate_tutor_assignments(df)
        assert "INVALID_NUMERIC" in quarantine[0]["reason_code"]
        assert "Field \'hourly rate\': could not parse \"Thirty\" as a number (row 2)" in quarantine[0]["reason_detail"]
    
    def test_multiple_issues(self):
        df = self.valid_assignment_df({
            "tutor_name": None,
            "status": "UnknownStatus",
            "hourly_rate": "Thirty"
        })
        clean_df, quarantine = validate_tutor_assignments(df)
        assert len(quarantine) == 1
        assert quarantine[0]["reason_code"] == "MULTIPLE_ISSUES"
        assert "Field 'tutor name' is blank or null (row 2)" in quarantine[0]["reason_detail"]
        assert "Field \'hourly rate\': could not parse \"Thirty\" as a number (row 2)" in quarantine[0]["reason_detail"]
        assert "received \"UnknownStatus\"" in quarantine[0]["reason_detail"]
        assert "expected one of [\'active\', \'inactive\', \'pending\'] (row 2)" in quarantine[0]["reason_detail"]