import argparse
import logging
import typing
from pathlib import Path

from pydantic import ValidationError

from mergetyp import __version__
from mergetyp.contracts import DEFAULT_JOBS, RenderResult, RuntimeSettings
from mergetyp.data import load_data
from mergetyp.exceptions import DataValidationError, InputFileNotFoundError, MergetypError
from mergetyp.log import configure_logging
from mergetyp.runner import run_batch


class _MergetypArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> typing.NoReturn:
        raise DataValidationError(f"ERROR: invalid CLI arguments: {message}")


def positive_int(value: str) -> int:
    """Parse positive integer

    Args:
        value: Raw CLI value

    Returns:
        Parsed positive integer

    Raises:
        ArgumentTypeError: If value is not positive integer
    """
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value}") from error

    if number < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {number}")

    return number


def non_negative_int(value: str) -> int:
    """Parse non-negative integer

    Args:
        value: Raw CLI value

    Returns:
        Parsed non-negative integer

    Raises:
        ArgumentTypeError: If value is negative
    """
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value}") from error

    if number < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {number}")

    return number


def positive_float(value: str) -> float:
    """Parse positive float

    Args:
        value: Raw CLI value

    Returns:
        Parsed positive float

    Raises:
        ArgumentTypeError: If value is not positive float
    """
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be a number, got {value}") from error

    if number <= 0.0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {number}")

    return number


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser

    Returns:
        Configured argument parser
    """
    parser = _MergetypArgumentParser(
        prog="mergetyp",
        description=(
            "Generate one PDF per data record using a Typst template. "
            "The template must export render(record)."
        ),
    )
    parser.add_argument("template", help="Path to the .typ template file.")
    parser.add_argument("data", help="Path to .csv, .json, .yaml or .yml data file.")
    parser.add_argument("-o", "--output", default="out", help="Output directory.")
    parser.add_argument("--name-pattern", default="{index}.pdf", help="Output filename pattern.")
    parser.add_argument("--no-coerce", action="store_true", help="Keep CSV values as strings.")
    parser.add_argument("-j", "--jobs", type=positive_int, default=DEFAULT_JOBS, help="Parallel Typst jobs.")
    parser.add_argument("--compile-timeout", type=positive_float, default=60.0, help="Typst timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Validate plan without generating PDFs.")
    parser.add_argument("--limit", type=positive_int, default=None, help="Maximum number of records to process.")
    parser.add_argument("--offset", type=non_negative_int, default=0, help="Number of records to skip.")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding.")
    parser.add_argument(
        "--collision",
        choices=["error", "overwrite", "rename"],
        default="error",
        help="Output filename collision policy.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--quiet", action="store_true", help="Show only errors.")
    parser.add_argument("--version", action="version", version=f"mergetyp {__version__}")
    return parser


def build_runtime_settings(args: argparse.Namespace) -> RuntimeSettings:
    """Build validated runtime settings from parsed CLI arguments

    Args:
        args: Parsed argparse namespace

    Returns:
        Validated runtime settings

    Raises:
        ValidationError: If settings are invalid
    """
    return RuntimeSettings(
        template_path=Path(args.template).resolve(),
        data_path=Path(args.data).resolve(),
        output_dir=Path(args.output).resolve(),
        name_pattern=args.name_pattern,
        jobs=args.jobs,
        compile_timeout=args.compile_timeout,
        no_coerce=args.no_coerce,
        dry_run=args.dry_run,
        limit=args.limit,
        offset=args.offset,
        encoding=args.encoding,
        collision=args.collision,
        verbose=args.verbose,
        quiet=args.quiet,
    )


def select_records(
    records: typing.List[typing.Dict[str, typing.Any]],
    offset: int,
    limit: typing.Optional[int],
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Apply offset and limit to records

    Args:
        records: Loaded records
        offset: Number of records to skip
        limit: Optional maximum number of records

    Returns:
        Selected records

    Raises:
        DataValidationError: If selection is empty
    """
    selected_records = records[offset:]
    if limit is not None:
        selected_records = selected_records[:limit]

    if not selected_records:
        raise DataValidationError("ERROR: selected record range contains no records.")

    return selected_records


def report_results(results: typing.List[RenderResult], dry_run: bool, logger: logging.Logger) -> int:
    """Report batch results

    Args:
        results: Render results
        dry_run: Whether this was a dry run
        logger: Application logger

    Returns:
        Process exit code
    """
    success_count = 0
    error_count = 0

    for result in results:
        if result.ok:
            success_count = success_count + 1
        else:
            error_count = error_count + 1
            logger.error(result.error_message)

    action = "planned" if dry_run else "generated"
    total_count = len(results)
    logger.info("mergetyp: done. %s/%s PDF(s) %s.", success_count, total_count, action)

    if error_count > 0:
        return 1

    return 0


def run_main(argv: typing.Optional[typing.List[str]]) -> int:
    """Run CLI business flow

    Args:
        argv: Optional command line arguments

    Returns:
        Process exit code

    Raises:
        MergetypError: If expected application error occurs
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logging(args.verbose, args.quiet)
    settings = build_runtime_settings(args)

    if not settings.template_path.is_file():
        raise InputFileNotFoundError(f"ERROR: template not found: {settings.template_path}")

    if not settings.data_path.is_file():
        raise InputFileNotFoundError(f"ERROR: data file not found: {settings.data_path}")

    records = load_data(
        path=settings.data_path,
        coerce=not settings.no_coerce,
        encoding=settings.encoding,
    )
    selected_records = select_records(records, settings.offset, settings.limit)
    results = run_batch(settings, selected_records, logger)
    return report_results(results, settings.dry_run, logger)


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    """Run mergetyp CLI

    Args:
        argv: Optional command line arguments

    Returns:
        Process exit code
    """
    logger = logging.getLogger("mergetyp")

    try:
        return run_main(argv)
    except KeyboardInterrupt:
        logger.error("mergetyp: interrupted by user")
        return 130
    except SystemExit as error:
        if error.code is None:
            return 0

        try:
            return int(error.code)
        except (TypeError, ValueError):
            logger.error("%s", error.code)
            return 1
    except InputFileNotFoundError as error:
        logger.error(error.message)
        return error.exit_code
    except MergetypError as error:
        logger.error(error.message)
        return error.exit_code
    except ValidationError as error:
        logger.error("ERROR: invalid CLI settings: %s", error)
        return 1
    except Exception:
        logger.exception("ERROR: unexpected fatal error")
        return 1
