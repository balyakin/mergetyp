import logging
import os
import tempfile
import typing
from pathlib import Path

from mergetyp.contracts import CollisionPolicy, RenderJob
from mergetyp.exceptions import OutputCollisionError, OutputWriteError
from mergetyp.naming import build_filename

TEMP_SUFFIX = ".tmp"
RENAME_START_INDEX = 2
MAX_RENAME_ATTEMPTS = 100000


def build_render_jobs(
    records: typing.List[typing.Dict[str, typing.Any]],
    output_dir: Path,
    name_pattern: str,
    collision: CollisionPolicy,
    logger: logging.Logger,
    ensure_dir: bool = True,
) -> typing.List[RenderJob]:
    """Build render jobs and resolve output path collisions

    Args:
        records: Records selected for rendering
        output_dir: Output directory
        name_pattern: Filename pattern
        collision: Collision policy
        logger: Application logger
        ensure_dir: Create output directory before planning

    Returns:
        Render jobs with final output paths

    Raises:
        OutputCollisionError: If collisions exist and policy is error
        OutputWriteError: If output directory cannot be created
    """
    if ensure_dir:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OutputWriteError(f"ERROR: cannot create output directory '{output_dir}': {error}") from error

    jobs: typing.List[RenderJob] = []
    record_index = 1
    for record in records:
        filename = build_filename(name_pattern, record, record_index)
        output_path = (output_dir / filename).resolve()
        job = RenderJob(record_index=record_index, record=record, output_path=output_path)
        jobs.append(job)
        record_index = record_index + 1

    return resolve_collisions(jobs, collision, logger)


def resolve_collisions(
    jobs: typing.List[RenderJob],
    collision: CollisionPolicy,
    logger: logging.Logger,
) -> typing.List[RenderJob]:
    """Resolve output filename collisions

    Args:
        jobs: Render jobs
        collision: Collision policy
        logger: Application logger

    Returns:
        Render jobs with resolved output paths

    Raises:
        OutputCollisionError: If collision policy is error and collisions exist
    """
    if collision == "rename":
        return rename_collisions(jobs)

    messages = collect_collision_messages(jobs)
    if not messages:
        return jobs

    if collision == "overwrite":
        for message in messages:
            logger.warning(message)
        return jobs

    details = "\n".join(messages)
    raise OutputCollisionError(f"ERROR: output filename collision detected.\n{details}")


def collect_collision_messages(jobs: typing.List[RenderJob]) -> typing.List[str]:
    """Collect batch and filesystem collision messages

    Args:
        jobs: Render jobs

    Returns:
        Collision messages
    """
    messages: typing.List[str] = []
    seen_paths: typing.Dict[Path, int] = {}

    for job in jobs:
        if job.output_path in seen_paths:
            first_index = seen_paths[job.output_path]
            messages.append(f"record #{job.record_index} collides with record #{first_index}: {job.output_path}")
            continue

        seen_paths[job.output_path] = job.record_index

        if job.output_path.exists():
            messages.append(f"record #{job.record_index} would overwrite existing file: {job.output_path}")

    return messages


def rename_collisions(jobs: typing.List[RenderJob]) -> typing.List[RenderJob]:
    """Rename colliding output paths

    Args:
        jobs: Render jobs

    Returns:
        Render jobs with unique output paths
    """
    resolved_jobs: typing.List[RenderJob] = []
    used_paths: typing.Set[Path] = set()

    for job in jobs:
        output_path = get_unique_output_path(job.output_path, used_paths)
        used_paths.add(output_path)
        resolved_job = RenderJob(record_index=job.record_index, record=job.record, output_path=output_path)
        resolved_jobs.append(resolved_job)

    return resolved_jobs


def get_unique_output_path(output_path: Path, used_paths: typing.Set[Path]) -> Path:
    """Build unique output path by adding numeric suffix

    Args:
        output_path: Requested output path
        used_paths: Paths already assigned in current batch

    Returns:
        Unique output path
    """
    if output_path not in used_paths and not output_path.exists():
        return output_path

    suffix_number = RENAME_START_INDEX
    stem = output_path.stem
    file_suffix = output_path.suffix
    parent = output_path.parent

    for _ in range(MAX_RENAME_ATTEMPTS):
        candidate_name = f"{stem}_{suffix_number}{file_suffix}"
        candidate_path = parent / candidate_name
        if candidate_path not in used_paths and not candidate_path.exists():
            return candidate_path

        suffix_number = suffix_number + 1

    raise OutputWriteError(
        f"ERROR: cannot find unique output path for '{output_path.name}' after {MAX_RENAME_ATTEMPTS} attempts"
    )


def write_pdf_atomic(output_path: Path, pdf_bytes: bytes) -> None:
    """Write PDF bytes atomically

    Args:
        output_path: Target PDF path
        pdf_bytes: PDF file content

    Raises:
        OutputWriteError: If writing fails
    """
    temp_path: typing.Optional[Path] = None

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.",
            suffix=TEMP_SUFFIX,
            dir=str(output_path.parent),
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(pdf_bytes)

        os.replace(str(temp_path), str(output_path))
    except OSError as error:
        raise OutputWriteError(f"ERROR: cannot write output file '{output_path}': {error}") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
