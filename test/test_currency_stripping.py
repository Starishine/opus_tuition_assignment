import pytest
from utilities.cleaner import parse_numeric


class TestCurrencyStripping:
    def test_sgd_prefix_with_space(self):
        # Exact format from invoice_export_q1.xlsx: "SGD 165.00"
        assert parse_numeric("SGD 165.00") == 165.0
 
    def test_sgd_prefix_no_space(self):
        assert parse_numeric("SGD165.00") == 165.0
 
    def test_dollar_symbol(self):
        assert parse_numeric("$45.00") == 45.0
 
    def test_pound_symbol(self):
        assert parse_numeric("£55.50") == 55.5
 
    def test_euro_symbol(self):
        assert parse_numeric("€120.00") == 120.0
 
    def test_comma_thousands_separator(self):
        assert parse_numeric("1,200.00") == 1200.0
 
    def test_plain_integer_string(self):
        assert parse_numeric("75") == 75.0
 
    def test_zero_string_is_valid(self):
        # "0" must not be treated as missing — it is a valid zero fee
        assert parse_numeric("0") == 0.0
 
    def test_string_zero_is_valid(self):
        assert parse_numeric("0.00") == 0.0
 
    def test_missing_sentinel_returns_none(self):
        assert parse_numeric("N/A") is None
        assert parse_numeric("TBC") is None
 
    def test_non_numeric_returns_none(self):
        assert parse_numeric("not-a-number") is None
 
    def test_none_returns_none(self):
        assert parse_numeric(None) is None