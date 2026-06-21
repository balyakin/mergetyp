import contextlib
import os
import shutil
import subprocess
import tempfile
import typing
from pathlib import Path

from mergetyp.exceptions import OutputWriteError, TypstCompileError, TypstNotFoundError, TypstTimeoutError
from mergetyp.typst_value import escape_string, to_typst


def find_typst() -> str:
    """Find Typst CLI binary

    Returns:
        Absolute path to Typst binary

    Raises:
        TypstNotFoundError: If Typst CLI is not available on PATH
    """
    typst_bin = shutil.which("typst")
    if typst_bin is None:
        raise TypstNotFoundError(
            "ERROR: 'typst' CLI not found on PATH. Install it from official Typst releases."
        )

    return typst_bin


def _close_descriptor(descriptor_number: int) -> None:
    with contextlib.suppress(OSError):
        os.close(descriptor_number)


def render_record(
    template_path: Path,
    record: typing.Dict[str, typing.Any],
    typst_bin: str,
    compile_timeout: float,
) -> bytes:
    """Render one record into PDF bytes

    Args:
        template_path: Typst template path
        record: Input record
        typst_bin: Typst CLI binary path
        compile_timeout: Per-record compilation timeout in seconds

    Returns:
        PDF bytes

    Raises:
        OutputWriteError: If temporary Typst file cannot be created
        TypstCompileError: If Typst exits with non-zero code
        TypstTimeoutError: If Typst compilation exceeds timeout
    """
    root = template_path.parent
    template_name = template_path.name
    escaped_template_name = escape_string(template_name)
    source = f'#import "{escaped_template_name}": render\n#render({to_typst(record)})\n'

    try:
        file_descriptor = tempfile.mkstemp(prefix=".mergetyp_gen_", suffix=".typ", dir=str(root))
    except PermissionError as error:
        raise OutputWriteError(
            f"ERROR: cannot write temporary Typst file to template directory '{root}'. Check write permissions."
        ) from error
    except OSError as error:
        raise OutputWriteError(
            f"ERROR: cannot write temporary Typst file to template directory '{root}': {error}"
        ) from error

    descriptor_number = file_descriptor[0]
    temporary_name = file_descriptor[1]
    temporary_path = Path(temporary_name)
    descriptor_open = True

    try:
        with os.fdopen(descriptor_number, "w", encoding="utf-8") as temporary_file:
            descriptor_open = False
            temporary_file.write(source)

        result = subprocess.run(
            [
                typst_bin,
                "compile",
                "--root",
                str(root),
                "--format",
                "pdf",
                str(temporary_path),
                "-",
            ],
            capture_output=True,
            check=False,
            timeout=compile_timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise TypstTimeoutError(
            f"ERROR: typst timed out after {compile_timeout}s for template '{template_name}'"
        ) from error
    except OSError as error:
        if descriptor_open:
            _close_descriptor(descriptor_number)
            descriptor_open = False

        raise OutputWriteError(f"ERROR: cannot execute typst for template '{template_name}': {error}") from error
    finally:
        if descriptor_open:
            _close_descriptor(descriptor_number)

        temporary_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        raise TypstCompileError(
            f"ERROR: typst failed to compile record with template '{template_name}'.\n"
            f"--- typst stderr ---\n{stderr_text}"
        )

    return result.stdout
