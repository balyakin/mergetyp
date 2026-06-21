import datetime
import math
import re
import typing

from mergetyp.exceptions import DataValidationError

TYPST_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_FLOAT_DECIMAL_PRECISION = 341
CONTROL_CHARACTER_LIMIT = 0x1F
DELETE_CHARACTER_CODE = 0x7F


def is_typst_identifier(key: str) -> bool:
    """Check whether a key can be emitted as an unquoted Typst dictionary key

    Args:
        key: Dictionary key

    Returns:
        True if key is safe as an unquoted Typst key
    """
    return TYPST_IDENTIFIER_PATTERN.match(key) is not None


def format_float(value: float) -> str:
    """Format float as Typst-compatible decimal literal

    Args:
        value: Python float

    Returns:
        Typst decimal literal or none
    """
    if not math.isfinite(value):
        return "none"

    if value == 0.0:
        return "0.0"

    for precision in range(1, MAX_FLOAT_DECIMAL_PRECISION + 1):
        value_text = f"{value:.{precision}f}"
        if float(value_text) == value:
            if value_text == "-0.0":
                return "0.0"

            return value_text

    raise DataValidationError(f"ERROR: cannot represent float {value!r} as Typst decimal literal without loss")


def escape_string(value: str) -> str:
    """Escape string for Typst source literal

    Args:
        value: Raw Python string

    Returns:
        Escaped string without surrounding quotes
    """
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")
    result_parts: typing.List[str] = []

    for character in escaped:
        character_code = ord(character)
        is_control_character = character_code <= CONTROL_CHARACTER_LIMIT or character_code == DELETE_CHARACTER_CODE
        if is_control_character:
            result_parts.append(f"\\u{{{character_code:04X}}}")
        else:
            result_parts.append(character)

    return "".join(result_parts)


def quote_string(value: str) -> str:
    """Quote string for Typst source literal

    Args:
        value: Raw Python string

    Returns:
        Quoted Typst string literal
    """
    return '"' + escape_string(value) + '"'


def to_typst(value: typing.Any) -> str:
    """Convert Python value to Typst source literal

    Args:
        value: Python value

    Returns:
        Typst source literal

    Raises:
        DataValidationError: If value type is unsupported
    """
    if value is None:
        return "none"

    if isinstance(value, bool):
        if value:
            return "true"

        return "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return format_float(value)

    if isinstance(value, str):
        return quote_string(value)

    if isinstance(value, list):
        return to_typst_array(value)

    if isinstance(value, tuple):
        return to_typst_array(list(value))

    if isinstance(value, dict):
        return to_typst_dict(value)

    if isinstance(value, datetime.datetime):
        return quote_string(value.isoformat())

    if isinstance(value, datetime.date):
        return quote_string(value.isoformat())

    value_type = type(value).__name__
    raise DataValidationError(f"ERROR: unsupported value type for Typst literal: {value_type}")


def to_typst_array(values: typing.List[typing.Any]) -> str:
    """Convert Python list to Typst array literal

    Args:
        values: Python list

    Returns:
        Typst array literal
    """
    if not values:
        return "()"

    item_literals: typing.List[str] = []
    for item in values:
        item_literal = to_typst(item)
        item_literals.append(item_literal)

    return "(" + ", ".join(item_literals) + ",)"


def to_typst_dict(values: typing.Dict[typing.Any, typing.Any]) -> str:
    """Convert Python dictionary to Typst dictionary literal

    Args:
        values: Python dictionary

    Returns:
        Typst dictionary literal
    """
    if not values:
        return "(:)"

    pair_literals: typing.List[str] = []
    for raw_key in values:
        key = str(raw_key)
        value = values[raw_key]
        value_literal = to_typst(value)
        if is_typst_identifier(key):
            pair_literals.append(f"{key}: {value_literal}")
        else:
            key_literal = quote_string(key)
            pair_literals.append(f"{key_literal}: {value_literal}")

    return "(" + ", ".join(pair_literals) + ",)"
