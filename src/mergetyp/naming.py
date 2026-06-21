import re
import string
import typing

from mergetyp.exceptions import FilenamePatternError

ILLEGAL_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
PDF_SUFFIX = ".pdf"
DEFAULT_FILENAME = "output"
FORMAT_FIELD_NAME_INDEX = 1
FORMAT_SPEC_INDEX = 2
FORMAT_CONVERSION_INDEX = 3


class StrictFormatDict(typing.Dict[str, str]):
    """Dictionary for strict filename pattern formatting"""

    def __missing__(self, key: str) -> str:
        """Raise a clear error when filename pattern references a missing field

        Args:
            key: Missing format field

        Raises:
            FilenamePatternError: Always raised for missing fields
        """
        available_fields = ", ".join(str(field_name) for field_name in self.keys())
        raise FilenamePatternError(
            f"ERROR: name-pattern references field '{key}' which is not in the record. "
            f"Available fields: {available_fields}"
        )


def validate_pattern_structure(pattern: str) -> None:
    """Validate filename pattern structure before rendering

    Args:
        pattern: User-provided filename pattern

    Raises:
        FilenamePatternError: If pattern uses unsupported Python formatting features
    """
    formatter = string.Formatter()

    try:
        parsed_parts = formatter.parse(pattern)
        for parsed_part in parsed_parts:
            field_name = parsed_part[FORMAT_FIELD_NAME_INDEX]
            format_spec = parsed_part[FORMAT_SPEC_INDEX]
            conversion = parsed_part[FORMAT_CONVERSION_INDEX]
            validate_pattern_field(pattern, field_name, format_spec, conversion)
    except ValueError as error:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': {error}") from error


def validate_pattern_field(
    pattern: str,
    field_name: typing.Optional[str],
    format_spec: str,
    conversion: typing.Optional[str],
) -> None:
    """Validate one filename pattern field

    Args:
        pattern: User-provided filename pattern
        field_name: Format field name
        format_spec: Format specifier
        conversion: Conversion flag

    Raises:
        FilenamePatternError: If field uses unsupported formatting features
    """
    if field_name is None:
        return

    if field_name == "" or field_name.isdigit():
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': positional fields are not supported")

    if "." in field_name or "[" in field_name or "]" in field_name:
        raise FilenamePatternError(
            f"ERROR: invalid name-pattern '{pattern}': nested field references are not supported"
        )

    if format_spec:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': format specifiers are not supported")

    if conversion:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': conversion flags are not supported")


def sanitize_filename(name: str) -> str:
    """Sanitize one filename

    Args:
        name: Raw filename

    Returns:
        Safe filename
    """
    cleaned = ILLEGAL_FILENAME_PATTERN.sub("_", name)
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned

    return DEFAULT_FILENAME


def build_filename(pattern: str, record: typing.Dict[str, typing.Any], record_index: int) -> str:
    """Build output PDF filename for one record

    Args:
        pattern: User-provided filename pattern
        record: Input record
        record_index: One-based record index

    Returns:
        Safe PDF filename

    Raises:
        FilenamePatternError: If pattern references missing field
    """
    validate_pattern_structure(pattern)

    mapping = StrictFormatDict()
    for key in record:
        mapping[str(key)] = str(record[key])

    mapping["index"] = str(record_index)

    try:
        rendered = pattern.format_map(mapping)
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': {error}") from error
    except ValueError as error:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': {error}") from error

    if not rendered.endswith(PDF_SUFFIX):
        rendered = rendered + PDF_SUFFIX

    sanitized = sanitize_filename(rendered)
    if sanitized == PDF_SUFFIX:
        return DEFAULT_FILENAME + PDF_SUFFIX

    return sanitized
