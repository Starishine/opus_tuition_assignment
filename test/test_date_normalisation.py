import pytest

from utilities.cleaner import parse_date

class TestDateNormalisation:
    
    def test_iso_8601(self):
        # %Y-%m-%d — already ISO, must pass through unchanged
        assert parse_date("2024-01-15") == "2024-01-15"
 
    def test_uk_slash(self):
        # %d/%m/%Y — common UK/SG format
        assert parse_date("15/01/2024") == "2024-01-15"
 
    def test_us_slash(self):
        # %m/%d/%Y — US format, month first
        assert parse_date("01/15/2024") == "2024-01-15"
 
    def test_uk_dash(self):
        # %d-%m-%Y
        assert parse_date("15-01-2024") == "2024-01-15"
 
    def test_day_abbreviated_month_year(self):
        # %d %b %Y — e.g. 15 Jan 2024
        assert parse_date("15 Jan 2024") == "2024-01-15"
 
    def test_day_full_month_year(self):
        # %d %B %Y — e.g. 15 January 2024
        assert parse_date("15 January 2024") == "2024-01-15"
 
    def test_abbreviated_month_day_year(self):
        # %b %d, %Y — e.g. Jan 15, 2024
        assert parse_date("Jan 15, 2024") == "2024-01-15"
 
    def test_full_month_day_year(self):
        # %B %d, %Y — e.g. January 15, 2024
        assert parse_date("January 15, 2024") == "2024-01-15"
 
    def test_two_digit_year_slash(self):
        # %d/%m/%y — two-digit year as in lesson_logs_messy.xlsx
        assert parse_date("15/01/24") == "2024-01-15"
 
    def test_day_abbreviated_month_dash_year(self):
        # %d-%b-%Y — e.g. 15-Jan-2024
        assert parse_date("15-Jan-2024") == "2024-01-15"
 
    def test_trailing_whitespace_stripped(self):
        # Whitespace around the date string must not cause failure
        assert parse_date("  2024-01-15  ") == "2024-01-15"
 
    def test_missing_sentinel_returns_none(self):
        # Values like N/A, TBC are treated as missing, not invalid
        assert parse_date("N/A") is None
        assert parse_date("TBC") is None
 
    def test_unparseable_returns_none(self):
        # A string that matches no format must return None, not raise
        assert parse_date("not-a-date") is None
 
    def test_none_input_returns_none(self):
        assert parse_date(None) is None
 
    def test_nan_input_returns_none(self):
        assert parse_date(float("nan")) is None