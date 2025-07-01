# tests/test_validator.py
from building_grammar.validator import validate, Severity

def test_fill_warning():
    issues = validate("[A]3-[B]2")    # rigid-only pattern
    assert any(i.severity == Severity.WARNING for i in issues)

def test_clean_pattern():
    issues = validate("<A>[B]2")
    assert issues == []               # no warnings/errors
