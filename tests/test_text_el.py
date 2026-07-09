"""Tests for text_el() SVG <text> generation."""
from mystarhistory import text_el


def test_minimal_text():
    out = text_el(10, 20, "hello", "Handlee, cursive")
    assert out.startswith("<text ")
    assert 'x="10"' in out
    assert 'y="20"' in out
    assert '>hello</text>' in out


def test_defaults_bold_black_16():
    out = text_el(0, 0, "x", "Handlee, cursive")
    assert 'font-size="16"' in out
    assert 'font-weight="bold"' in out
    assert 'fill="#000"' in out


def test_custom_size_weight_fill():
    out = text_el(5, 5, "x", "Handlee, cursive", size=24, weight="normal", fill="#ff0000")
    assert 'font-size="24"' in out
    assert 'font-weight="normal"' in out
    assert 'fill="#ff0000"' in out


def test_anchor_attribute_emitted_when_provided():
    out = text_el(5, 5, "x", "Handlee, cursive", anchor="middle")
    assert 'text-anchor="middle"' in out


def test_anchor_attribute_omitted_when_not_provided():
    out = text_el(5, 5, "x", "Handlee, cursive")
    assert "text-anchor" not in out


def test_transform_attribute_emitted_when_provided():
    out = text_el(5, 5, "x", "Handlee, cursive", transform="rotate(-90, 5, 5)")
    assert 'transform="rotate(-90, 5, 5)"' in out


def test_transform_attribute_omitted_when_not_provided():
    out = text_el(5, 5, "x", "Handlee, cursive")
    assert "transform" not in out


def test_special_chars_not_escaped():
    """text_el() does no HTML/XML escaping. Document the current contract so
    future changes are deliberate."""
    out = text_el(0, 0, "a&b<c>", "Handlee, cursive")
    assert ">a&b<c></text>" in out
