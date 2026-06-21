import math

import pytest

from mergetyp.exceptions import DataValidationError
from mergetyp.typst_value import is_typst_identifier, to_typst


def test_scalar_values_convert_to_typst_literals() -> None:
    # ARRANGE
    values = [None, True, False, 42]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == ["none", "true", "false", "42"]


def test_float_values_convert_without_scientific_notation() -> None:
    # ARRANGE
    values = [3.5, 0.00001, 159.9, 1758.9, 0.1 + 0.2]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == ["3.5", "0.00001", "159.9", "1758.9", "0.30000000000000004"]


def test_small_float_values_convert_without_data_loss() -> None:
    # ARRANGE
    values = [0.00000000000000000001, -0.00000000000000000005]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == ["0.00000000000000000001", "-0.00000000000000000005"]


def test_non_finite_float_values_convert_to_none() -> None:
    # ARRANGE
    values = [math.nan, math.inf, -math.inf]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == ["none", "none", "none"]


def test_strings_are_escaped() -> None:
    # ARRANGE
    value = 'a"b\\c\n\t'

    # ACT
    result = to_typst(value)

    # ASSERT
    assert result == '"a\\"b\\\\c\\n\\t"'


def test_control_characters_are_escaped() -> None:
    # ARRANGE
    value = "a\x00b\x7fc"

    # ACT
    result = to_typst(value)

    # ASSERT
    assert result == '"a\\u{0000}b\\u{007F}c"'


def test_lists_and_tuples_convert_to_typst_arrays() -> None:
    # ARRANGE
    values = [[], [1], [1, [2]], (1, 2)]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == ["()", "(1,)", "(1, (2,),)", "(1, 2,)"]


def test_dicts_convert_to_typst_dictionaries() -> None:
    # ARRANGE
    values = [
        {},
        {"name": "Alice"},
        {"имя": "Alice"},
        {"invoice-id": "INV-001"},
        {"client": {"name": "Alice"}},
    ]

    # ACT
    results = [to_typst(value) for value in values]

    # ASSERT
    assert results == [
        "(:)",
        '(name: "Alice",)',
        '("имя": "Alice",)',
        '("invoice-id": "INV-001",)',
        '(client: (name: "Alice",),)',
    ]


def test_identifier_check_accepts_only_safe_ascii_keys() -> None:
    # ARRANGE
    values = ["name", "_id", "name1", "имя", "invoice-id", "1name"]

    # ACT
    results = [is_typst_identifier(value) for value in values]

    # ASSERT
    assert results == [True, True, True, False, False, False]


def test_unsupported_object_raises_data_validation_error() -> None:
    # ARRANGE
    value = object()

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        to_typst(value)

    # ASSERT
    assert "unsupported value type" in error_info.value.message
