from pathlib import Path

import pytest
from pydantic import ValidationError

from mergetyp.contracts import RuntimeSettings, validate_record_batch
from mergetyp.exceptions import DataValidationError


def test_runtime_settings_accept_valid_values(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    settings = RuntimeSettings(template_path=template_path, data_path=data_path)

    # ASSERT
    assert settings.template_path == template_path
    assert settings.data_path == data_path
    assert settings.name_pattern == "{index}.pdf"


def test_runtime_settings_forbid_extra_fields(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    with pytest.raises(ValidationError) as error_info:
        RuntimeSettings(template_path=template_path, data_path=data_path, unexpected=True)

    # ASSERT
    assert "Extra inputs are not permitted" in str(error_info.value)


def test_runtime_settings_reject_verbose_and_quiet(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    with pytest.raises(ValidationError) as error_info:
        RuntimeSettings(template_path=template_path, data_path=data_path, verbose=True, quiet=True)

    # ASSERT
    assert "--verbose and --quiet cannot be used together" in str(error_info.value)


def test_runtime_settings_reject_invalid_name_pattern(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    with pytest.raises(ValidationError) as error_info:
        RuntimeSettings(template_path=template_path, data_path=data_path, name_pattern="{index")

    # ASSERT
    assert "invalid name-pattern syntax" in str(error_info.value)


def test_record_batch_rejects_empty_batch() -> None:
    # ARRANGE
    records = []

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        validate_record_batch(records)

    # ASSERT
    assert "data source contains no records" in error_info.value.message


def test_record_batch_rejects_non_string_key() -> None:
    # ARRANGE
    records = [{1: "Alice"}]

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        validate_record_batch(records)

    # ASSERT
    assert "invalid input records" in error_info.value.message


def test_record_batch_rejects_unsupported_object() -> None:
    # ARRANGE
    records = [{"name": object()}]

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        validate_record_batch(records)

    # ASSERT
    assert "unsupported type object" in error_info.value.message


def test_record_batch_accepts_nested_supported_values() -> None:
    # ARRANGE
    records = [
        {
            "name": "Alice",
            "active": True,
            "count": 3,
            "ratio": 1.5,
            "missing": None,
            "items": [{"description": "Work", "qty": 2}],
        }
    ]

    # ACT
    result = validate_record_batch(records)

    # ASSERT
    assert result == records
