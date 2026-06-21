import pytest

from mergetyp.exceptions import FilenamePatternError
from mergetyp.naming import build_filename, sanitize_filename


def test_default_index_pattern_builds_pdf_name() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    result = build_filename("{index}.pdf", record, 3)

    # ASSERT
    assert result == "3.pdf"


def test_field_pattern_builds_pdf_name() -> None:
    # ARRANGE
    record = {"invoice_id": "INV-001"}

    # ACT
    result = build_filename("{invoice_id}.pdf", record, 1)

    # ASSERT
    assert result == "INV-001.pdf"


def test_missing_field_raises_filename_pattern_error() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    with pytest.raises(FilenamePatternError) as error_info:
        build_filename("{invoice_id}.pdf", record, 1)

    # ASSERT
    assert "references field 'invoice_id'" in error_info.value.message


def test_nested_format_pattern_raises_filename_pattern_error() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    with pytest.raises(FilenamePatternError) as error_info:
        build_filename("{name.real}.pdf", record, 1)

    # ASSERT
    assert "invalid name-pattern" in error_info.value.message


def test_format_specifier_pattern_raises_filename_pattern_error() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    with pytest.raises(FilenamePatternError) as error_info:
        build_filename("{name:0>10}.pdf", record, 1)

    # ASSERT
    assert "format specifiers" in error_info.value.message


def test_positional_pattern_raises_filename_pattern_error() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    with pytest.raises(FilenamePatternError) as error_info:
        build_filename("{0}.pdf", record, 1)

    # ASSERT
    assert "positional" in error_info.value.message


def test_filename_without_pdf_suffix_appends_suffix() -> None:
    # ARRANGE
    record = {"name": "Alice"}

    # ACT
    result = build_filename("{name}", record, 1)

    # ASSERT
    assert result == "Alice.pdf"


def test_illegal_filename_chars_are_replaced() -> None:
    # ARRANGE
    record = {"name": '<A:l*i?c"e|>'}

    # ACT
    result = build_filename("{name}.pdf", record, 1)

    # ASSERT
    assert result == "_A_l_i_c_e__.pdf"


def test_slash_and_backslash_are_replaced() -> None:
    # ARRANGE
    record = {"department": "sales/west\\team"}

    # ACT
    result = build_filename("{department}.pdf", record, 1)

    # ASSERT
    assert result == "sales_west_team.pdf"


def test_empty_sanitized_name_uses_output_pdf() -> None:
    # ARRANGE
    record = {}

    # ACT
    result = build_filename("   ", record, 1)

    # ASSERT
    assert result == "output.pdf"


def test_sanitize_empty_name_uses_output() -> None:
    # ARRANGE
    name = "   "

    # ACT
    result = sanitize_filename(name)

    # ASSERT
    assert result == "output"
