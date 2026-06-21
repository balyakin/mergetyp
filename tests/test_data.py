from pathlib import Path

import pytest

from mergetyp.data import coerce_csv_value, detect_format, load_data
from mergetyp.exceptions import DataValidationError


def test_coerce_csv_value_handles_empty_cell() -> None:
    # ARRANGE
    raw = ""

    # ACT
    result = coerce_csv_value(raw)

    # ASSERT
    assert result is None


def test_coerce_csv_value_handles_bool_case_insensitive() -> None:
    # ARRANGE
    true_raw = "true"
    false_raw = "FALSE"

    # ACT
    true_result = coerce_csv_value(true_raw)
    false_result = coerce_csv_value(false_raw)

    # ASSERT
    assert true_result is True
    assert false_result is False


def test_coerce_csv_value_handles_int_values() -> None:
    # ARRANGE
    values = ["42", "-7", "0"]

    # ACT
    results = [coerce_csv_value(value) for value in values]

    # ASSERT
    assert results == [42, -7, 0]


def test_coerce_csv_value_keeps_leading_zero_string() -> None:
    # ARRANGE
    raw = "01234"

    # ACT
    result = coerce_csv_value(raw)

    # ASSERT
    assert result == "01234"


def test_coerce_csv_value_handles_float() -> None:
    # ARRANGE
    raw = "3.5"

    # ACT
    result = coerce_csv_value(raw)

    # ASSERT
    assert result == 3.5


def test_coerce_csv_value_keeps_scientific_notation_string() -> None:
    # ARRANGE
    raw = "1e-5"

    # ACT
    result = coerce_csv_value(raw)

    # ASSERT
    assert result == "1e-5"


def test_load_csv_coerces_values(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.csv"
    path.write_text("name,empty,active,count,ratio,zip,scientific\nAlice,,FALSE,-7,3.5,01234,1e-5\n", encoding="utf-8")

    # ACT
    records = load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert records == [
        {
            "name": "Alice",
            "empty": None,
            "active": False,
            "count": -7,
            "ratio": 3.5,
            "zip": "01234",
            "scientific": "1e-5",
        }
    ]


def test_load_csv_no_coerce_keeps_strings(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.csv"
    path.write_text("name,empty,count\nAlice,,42\n", encoding="utf-8")

    # ACT
    records = load_data(path, coerce=False, encoding="utf-8")

    # ASSERT
    assert records == [{"name": "Alice", "empty": "", "count": "42"}]


def test_load_csv_rejects_extra_cells(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.csv"
    path.write_text("name\nAlice,extra\n", encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "contains more cells than headers" in error_info.value.message


def test_load_csv_rejects_unknown_encoding(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.csv"
    path.write_text("name\nAlice\n", encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-42")

    # ASSERT
    assert "unknown encoding 'utf-42'" in error_info.value.message


def test_load_json_single_object_becomes_one_record(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.json"
    path.write_text('{"name": "Alice"}', encoding="utf-8")

    # ACT
    records = load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert records == [{"name": "Alice"}]


def test_load_json_array_of_objects(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.json"
    path.write_text('[{"name": "Alice"}, {"name": "Bob"}]', encoding="utf-8")

    # ACT
    records = load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert records == [{"name": "Alice"}, {"name": "Bob"}]


def test_load_json_scalar_fails(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.json"
    path.write_text('"Alice"', encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "JSON must be an object or array of objects" in error_info.value.message


def test_load_json_invalid_fails(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.json"
    path.write_text('{"name": ', encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "invalid JSON" in error_info.value.message


def test_load_json_decode_error_fails_as_data_validation_error(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.json"
    path.write_bytes('{"name": "é"}'.encode("latin-1"))

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "cannot decode JSON file" in error_info.value.message


def test_load_yaml_single_mapping(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.yaml"
    path.write_text("name: Alice\n", encoding="utf-8")

    # ACT
    records = load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert records == [{"name": "Alice"}]


def test_load_yaml_sequence_of_mappings(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.yml"
    path.write_text("- name: Alice\n- name: Bob\n", encoding="utf-8")

    # ACT
    records = load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert records == [{"name": "Alice"}, {"name": "Bob"}]


def test_load_yaml_invalid_fails(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.yaml"
    path.write_text("name: [", encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "invalid YAML" in error_info.value.message


def test_load_yaml_decode_error_fails_as_data_validation_error(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.yaml"
    path.write_bytes("name: é\n".encode("latin-1"))

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "cannot decode YAML file" in error_info.value.message


def test_load_yaml_scalar_fails(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.yaml"
    path.write_text("Alice", encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "YAML must be an object or array of objects" in error_info.value.message


def test_detect_format_rejects_unsupported_extension(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.toml"

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        detect_format(path)

    # ASSERT
    assert "unsupported data file" in error_info.value.message


def test_load_empty_records_fails(tmp_path: Path) -> None:
    # ARRANGE
    path = tmp_path / "data.csv"
    path.write_text("name\n", encoding="utf-8")

    # ACT
    with pytest.raises(DataValidationError) as error_info:
        load_data(path, coerce=True, encoding="utf-8")

    # ASSERT
    assert "data source contains no records" in error_info.value.message
