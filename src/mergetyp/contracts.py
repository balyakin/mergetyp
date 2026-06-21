import os
import typing
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from mergetyp.exceptions import DataValidationError

CollisionPolicy = typing.Literal["error", "overwrite", "rename"]
DEFAULT_JOBS = min(8, os.cpu_count() or 4)


class RuntimeSettings(BaseModel):
    """Validated application settings built from CLI arguments

    Args:
        template_path: Path to Typst template
        data_path: Path to CSV, JSON, YAML, or YML data file
        output_dir: Directory where PDFs will be written
        name_pattern: Output filename pattern
        jobs: Number of parallel Typst jobs
        compile_timeout: Timeout for a single Typst compilation
        no_coerce: Keep CSV values as strings
        dry_run: Validate plan without generating PDFs
        limit: Optional maximum number of records to process
        offset: Number of records to skip before processing
        encoding: CSV file encoding
        collision: Output collision policy
        verbose: Enable debug logs
        quiet: Show only errors

    Raises:
        ValidationError: If settings are invalid
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    template_path: Path = Field(description="Path to Typst template")
    data_path: Path = Field(description="Path to input data file")
    output_dir: Path = Field(default=Path("out"), description="Output directory")
    name_pattern: str = Field(default="{index}.pdf", min_length=1)
    jobs: int = Field(default=DEFAULT_JOBS, ge=1, le=64)
    compile_timeout: float = Field(default=60.0, gt=0.0, le=3600.0)
    no_coerce: bool = Field(default=False)
    dry_run: bool = Field(default=False)
    limit: typing.Optional[int] = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)
    encoding: str = Field(default="utf-8", min_length=1)
    collision: CollisionPolicy = Field(default="error")
    verbose: bool = Field(default=False)
    quiet: bool = Field(default=False)

    @field_validator("name_pattern")
    @classmethod
    def validate_name_pattern(cls, value: str) -> str:
        """Validate filename pattern syntax

        Args:
            value: User-provided filename pattern

        Returns:
            Validated filename pattern

        Raises:
            ValueError: If Python format string is invalid
        """
        try:
            value.format_map({"index": "1"})
        except KeyError:
            return value
        except ValueError as error:
            raise ValueError(f"invalid name-pattern syntax: {value}") from error

        return value

    @field_validator("quiet")
    @classmethod
    def validate_logging_flags(cls, value: bool, info: ValidationInfo) -> bool:
        """Validate mutually exclusive logging flags

        Args:
            value: Quiet flag
            info: Pydantic validation info

        Returns:
            Validated quiet flag

        Raises:
            ValueError: If verbose and quiet are both enabled
        """
        verbose = info.data.get("verbose")
        if value and verbose:
            raise ValueError("--verbose and --quiet cannot be used together")

        return value


class RecordBatchModel(BaseModel):
    """Validated batch of input records

    Args:
        records: Input records after loading

    Raises:
        ValidationError: If records contain unsupported values
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=False)

    records: typing.List[typing.Dict[str, typing.Any]] = Field(min_length=1)

    @field_validator("records")
    @classmethod
    def validate_records(
        cls,
        value: typing.List[typing.Dict[str, typing.Any]],
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Validate all records recursively

        Args:
            value: Loaded records

        Returns:
            Validated records

        Raises:
            ValueError: If a record contains unsupported values
        """
        record_index = 1
        for record in value:
            cls.validate_record(record, record_index)
            record_index = record_index + 1

        return value

    @classmethod
    def validate_record(cls, record: typing.Dict[str, typing.Any], record_index: int) -> None:
        """Validate one record

        Args:
            record: Loaded record
            record_index: One-based record index

        Raises:
            ValueError: If a key or value is unsupported
        """
        for key in record:
            if not isinstance(key, str):
                raise ValueError(f"record #{record_index} contains non-string key")

            field_value = record[key]
            cls.validate_value(field_value, record_index, key)

    @classmethod
    def validate_value(cls, value: typing.Any, record_index: int, field_path: str) -> None:
        """Validate one record value recursively

        Args:
            value: Field value
            record_index: One-based record index
            field_path: Human-readable field path

        Raises:
            ValueError: If value type is unsupported
        """
        if value is None:
            return

        if isinstance(value, str):
            return

        if isinstance(value, bool):
            return

        if isinstance(value, int):
            return

        if isinstance(value, float):
            return

        if isinstance(value, list):
            item_index = 1
            for item in value:
                item_path = f"{field_path}[{item_index}]"
                cls.validate_value(item, record_index, item_path)
                item_index = item_index + 1
            return

        if isinstance(value, dict):
            for child_key in value:
                if not isinstance(child_key, str):
                    raise ValueError(f"record #{record_index} field '{field_path}' contains non-string key")

                child_value = value[child_key]
                child_path = f"{field_path}.{child_key}"
                cls.validate_value(child_value, record_index, child_path)
            return

        value_type = type(value).__name__
        raise ValueError(f"record #{record_index} field '{field_path}' has unsupported type {value_type}")


@dataclass(frozen=True)
class RenderJob:
    """Single render job

    Args:
        record_index: One-based record index
        record: Input record
        output_path: Absolute output PDF path
    """

    record_index: int
    record: typing.Dict[str, typing.Any]
    output_path: Path


@dataclass(frozen=True)
class RenderResult:
    """Result of one render job

    Args:
        record_index: One-based record index
        output_path: Absolute output PDF path
        ok: Whether rendering succeeded
        error_message: Optional human-readable error
    """

    record_index: int
    output_path: Path
    ok: bool
    error_message: typing.Optional[str] = None


def validate_record_batch(
    records: typing.List[typing.Dict[str, typing.Any]],
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Validate records using Pydantic

    Args:
        records: Loaded records

    Returns:
        Validated records

    Raises:
        DataValidationError: If Pydantic rejects records
    """
    if not records:
        raise DataValidationError("ERROR: data source contains no records.")

    try:
        batch = RecordBatchModel(records=records)
    except ValidationError as error:
        raise DataValidationError(f"ERROR: invalid input records: {error}") from error

    return batch.records
