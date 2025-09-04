# tests/test_parse.py
# Basic unit tests for parsing normalization utilities and schema.

from app.utils import parse_salary_span, normalize_location, normalize_employment_type


def test_parse_salary_span_year():
    mn, mx, unit = parse_salary_span("$120k-$160k per year")
    assert mn == 120000 and mx == 160000 and unit == "year"


def test_parse_salary_span_hour():
    mn, mx, unit = parse_salary_span("30-45/hr")
    assert mn == 30 and mx == 45 and unit == "hour"


def test_normalize_location_alias():
    assert normalize_location("SF") == "san francisco"
    assert normalize_location("LA") == "los angeles"


def test_normalize_employment_type():
    assert normalize_employment_type("full time") == "full-time"
    assert normalize_employment_type("PT") == "part-time"
