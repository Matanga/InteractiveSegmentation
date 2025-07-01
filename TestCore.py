# tests/test_roundtrip.py
from building_grammar import core
import pytest

def test_roundtrip_simple():
    pattern = "<A-B>-[C]2\n<D>"
    model = core.parse(pattern)
    assert model.to_string() == pattern  # exact match

def test_invalid_token():
    bad = "<A--B>"
    with pytest.raises(core.GrammarError):
        core.parse(bad)

def test_multiline():
    pattern= """<Wall00>
<Window00-Wall00-Window01-Wall00-Window00>
<Window00-Wall00-Door00-Wall00-Window00>
<Wall00>"""

    model = core.parse(pattern)
    assert model.to_string() == pattern  # exact match
