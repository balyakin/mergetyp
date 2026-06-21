import csv
import json
import re
import typing
from pathlib import Path

import yaml

from mergetyp.contracts import validate_record_batch
from mergetyp.exceptions import DataValidationError

CSV_FORMAT = "csv"
JSON_FORMAT = "json"
YAML_FORMAT = "yaml"
CsvValue = typing.Optional[typing.Union[str, int, float, bool]]
INT_PATTERN = re.compile(r"^(0|-?[1-9]\d*)$")
FLOAT_PATTERN = re.compile(r"^-?(0|[1-9]\d*)\.\d+$")
TRUE_VALUE = "true"
FALSE_VALUE = "false"
DEFAULT_TEXT_ENCODING = "utf-8"


def detect_format(path: Path) -> str:
    """Detect data file format from path suffix

    Args:
        path: Data file path

    Returns:
        Data format name

    Raises:
        DataValidationError: If suffix is unsupported
    """
    suffix = path.suffix.lower()
    suffix = suffix.lstrip(".")

    if suffix == CSV_FORMAT:
        return CSV_FORMAT

    if suffix == JSON_FORMAT:
        return JSON_FORMAT

    if suffix == YAML_FORMAT or suffix == "yml":
        return YAML_FORMAT

    raise DataValidationError(f"ERROR: unsupported data file '{path}'. Use .csv, .json, .yaml or .yml")


def coerce_csv_value(raw: str) -> CsvValue:
    """Coerce one CSV string value into a supported Python value

    Args:
        raw: Raw CSV cell value

    Returns:
        Coerced value
    """
    if raw == "":
        return None

    lowered = raw.lower()
    if lowered == TRUE_VALUE:
        return True

    if lowered == FALSE_VALUE:
        return False

    if INT_PATTERN.match(raw):
        return int(raw)

    if FLOAT_PATTERN.match(raw):
        return float(raw)

    return raw


def load_data(path: Path, coerce: bool, encoding: str) -> typing.List[typing.Dict[str, typing.Any]]:
    """Load records from supported data file

    Args:
        path: Data file path
        coerce: Coerce CSV values
        encoding: CSV encoding

    Returns:
        Validated records

    Raises:
        DataValidationError: If data cannot be loaded or validated
    """
    data_format = detect_format(path)

    if data_format == CSV_FORMAT:
        return load_csv(path, coerce, encoding)

    if data_format == JSON_FORMAT:
        return load_json(path)

    return load_yaml(path)


def load_csv(path: Path, coerce: bool, encoding: str) -> typing.List[typing.Dict[str, typing.Any]]:
    """Load records from CSV file

    Args:
        path: CSV data file path
        coerce: Coerce CSV values
        encoding: CSV encoding

    Returns:
        Validated records

    Raises:
        DataValidationError: If CSV cannot be read or validated
    """
    records: typing.List[typing.Dict[str, typing.Any]] = []

    try:
        with path.open(newline="", encoding=encoding) as data_file:
            reader = csv.DictReader(data_file)
            row_index = 1
            for row in reader:
                record = build_csv_record(dict(row), coerce, row_index)
                records.append(record)
                row_index = row_index + 1
    except LookupError as error:
        raise DataValidationError(f"ERROR: unknown encoding '{encoding}': {error}") from error
    except UnicodeError as error:
        raise DataValidationError(f"ERROR: cannot decode CSV file '{path}' with encoding '{encoding}'") from error
    except csv.Error as error:
        raise DataValidationError(f"ERROR: invalid CSV in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return validate_record_batch(records)


def build_csv_record(
    row: typing.Dict[typing.Optional[str], typing.Any],
    coerce: bool,
    row_index: int,
) -> typing.Dict[str, typing.Any]:
    """Build one record from CSV row

    Args:
        row: CSV row
        coerce: Coerce CSV values
        row_index: One-based CSV row index

    Returns:
        Record dictionary

    Raises:
        DataValidationError: If CSV row contains extra unnamed columns
    """
    record: typing.Dict[str, typing.Any] = {}

    for key in row:
        if key is None:
            raise DataValidationError(f"ERROR: CSV row #{row_index} contains more cells than headers")

        raw_value = row[key]
        if raw_value is None:
            raw_value = ""

        if coerce:
            record[key] = coerce_csv_value(raw_value)
        else:
            record[key] = raw_value

    return record


def load_json(path: Path) -> typing.List[typing.Dict[str, typing.Any]]:
    """Load records from JSON file

    Args:
        path: JSON data file path

    Returns:
        Validated records

    Raises:
        DataValidationError: If JSON cannot be parsed or validated
    """
    try:
        with path.open(encoding=DEFAULT_TEXT_ENCODING) as data_file:
            data = json.load(data_file)
    except UnicodeError as error:
        raise DataValidationError(
            f"ERROR: cannot decode JSON file '{path}' with encoding '{DEFAULT_TEXT_ENCODING}'"
        ) from error
    except json.JSONDecodeError as error:
        raise DataValidationError(f"ERROR: invalid JSON in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return normalize_loaded_records(data, "JSON")


def load_yaml(path: Path) -> typing.List[typing.Dict[str, typing.Any]]:
    """Load records from YAML file

    Args:
        path: YAML data file path

    Returns:
        Validated records

    Raises:
        DataValidationError: If YAML cannot be parsed or validated
    """
    try:
        with path.open(encoding=DEFAULT_TEXT_ENCODING) as data_file:
            data = yaml.safe_load(data_file)
    except UnicodeError as error:
        raise DataValidationError(
            f"ERROR: cannot decode YAML file '{path}' with encoding '{DEFAULT_TEXT_ENCODING}'"
        ) from error
    except yaml.YAMLError as error:
        raise DataValidationError(f"ERROR: invalid YAML in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return normalize_loaded_records(data, "YAML")


def normalize_loaded_records(data: typing.Any, format_name: str) -> typing.List[typing.Dict[str, typing.Any]]:
    """Normalize loaded JSON or YAML data to records

    Args:
        data: Loaded data
        format_name: Human-readable format name

    Returns:
        Validated records

    Raises:
        DataValidationError: If loaded data is not object or array of objects
    """
    if data is None:
        raise DataValidationError("ERROR: data source contains no records.")

    if isinstance(data, dict):
        records = [data]
        return validate_record_batch(records)

    if isinstance(data, list):
        return validate_loaded_list(data, format_name)

    data_type = type(data).__name__
    raise DataValidationError(f"ERROR: {format_name} must be an object or array of objects, got {data_type}")


def validate_loaded_list(
    data: typing.List[typing.Any],
    format_name: str,
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Validate loaded JSON or YAML list

    Args:
        data: Loaded list
        format_name: Human-readable format name

    Returns:
        Validated records

    Raises:
        DataValidationError: If any item is not an object
    """
    records: typing.List[typing.Dict[str, typing.Any]] = []
    record_index = 1

    for item in data:
        if not isinstance(item, dict):
            item_type = type(item).__name__
            raise DataValidationError(f"ERROR: record #{record_index} is not an object, got {item_type}")

        records.append(item)
        record_index = record_index + 1

    return validate_record_batch(records)
