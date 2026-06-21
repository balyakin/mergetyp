import logging
import typing
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from mergetyp.contracts import RenderJob, RenderResult, RuntimeSettings
from mergetyp.exceptions import DataValidationError, InputFileNotFoundError, MergetypError
from mergetyp.output import build_render_jobs, write_pdf_atomic
from mergetyp.render import find_typst, render_record


def run_one_job(job: RenderJob, settings: RuntimeSettings, typst_bin: str, logger: logging.Logger) -> RenderResult:
    """Render and write one job

    Args:
        job: Render job
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render result
    """
    try:
        logger.debug("rendering record #%s -> %s", job.record_index, job.output_path)
        pdf_bytes = render_record(settings.template_path, job.record, typst_bin, settings.compile_timeout)
        write_pdf_atomic(job.output_path, pdf_bytes)
    except MergetypError as error:
        return RenderResult(
            record_index=job.record_index,
            output_path=job.output_path,
            ok=False,
            error_message=error.message,
        )
    except Exception as error:
        logger.exception(
            "unexpected error for record_index=%s output_path=%s",
            job.record_index,
            job.output_path,
        )
        return RenderResult(
            record_index=job.record_index,
            output_path=job.output_path,
            ok=False,
            error_message=f"ERROR: unexpected error for record #{job.record_index}: {error}",
        )

    return RenderResult(record_index=job.record_index, output_path=job.output_path, ok=True)


def run_jobs_parallel(
    jobs: typing.List[RenderJob],
    settings: RuntimeSettings,
    typst_bin: str,
    logger: logging.Logger,
) -> typing.List[RenderResult]:
    """Run render jobs in parallel

    Args:
        jobs: Render jobs
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render results
    """
    results: typing.List[RenderResult] = []

    executor = ThreadPoolExecutor(max_workers=settings.jobs)
    futures: typing.List[Future[RenderResult]] = []

    try:
        for job in jobs:
            future = executor.submit(run_one_job, job, settings, typst_bin, logger)
            futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    except KeyboardInterrupt:
        for future in futures:
            future.cancel()

        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)

    return results


def run_jobs_sequential(
    jobs: typing.List[RenderJob],
    settings: RuntimeSettings,
    typst_bin: str,
    logger: logging.Logger,
) -> typing.List[RenderResult]:
    """Run render jobs sequentially

    Args:
        jobs: Render jobs
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render results
    """
    results: typing.List[RenderResult] = []

    for job in jobs:
        result = run_one_job(job, settings, typst_bin, logger)
        results.append(result)

    return results


def run_dry_run(jobs: typing.List[RenderJob], logger: logging.Logger) -> typing.List[RenderResult]:
    """Return planned jobs without rendering PDFs

    Args:
        jobs: Render jobs
        logger: Application logger

    Returns:
        Successful dry-run results
    """
    results: typing.List[RenderResult] = []

    for job in jobs:
        logger.info("dry-run: record #%s -> %s", job.record_index, job.output_path)
        result = RenderResult(record_index=job.record_index, output_path=job.output_path, ok=True)
        results.append(result)

    return results


def run_batch(
    settings: RuntimeSettings,
    records: typing.List[typing.Dict[str, typing.Any]],
    logger: logging.Logger,
) -> typing.List[RenderResult]:
    """Run batch rendering

    Args:
        settings: Runtime settings
        records: Selected records
        logger: Application logger

    Returns:
        Render results

    Raises:
        InputFileNotFoundError: If template or data file is missing
        DataValidationError: If selected record range is empty
    """
    if not settings.template_path.is_file():
        raise InputFileNotFoundError(f"ERROR: template not found: {settings.template_path}")

    if not settings.data_path.is_file():
        raise InputFileNotFoundError(f"ERROR: data file not found: {settings.data_path}")

    jobs = build_render_jobs(
        records=records,
        output_dir=settings.output_dir,
        name_pattern=settings.name_pattern,
        collision=settings.collision,
        logger=logger,
        ensure_dir=not settings.dry_run,
    )

    if not jobs:
        raise DataValidationError("ERROR: selected record range contains no records.")

    if settings.dry_run:
        return run_dry_run(jobs, logger)

    typst_bin = find_typst()

    if settings.jobs == 1 or len(jobs) == 1 or has_duplicate_output_paths(jobs):
        results = run_jobs_sequential(jobs, settings, typst_bin, logger)
    else:
        results = run_jobs_parallel(jobs, settings, typst_bin, logger)

    return sort_results(results)


def has_duplicate_output_paths(jobs: typing.List[RenderJob]) -> bool:
    """Check whether multiple jobs target the same output path

    Args:
        jobs: Render jobs

    Returns:
        True if at least two jobs share an output path
    """
    seen_paths: typing.Set[object] = set()

    for job in jobs:
        if job.output_path in seen_paths:
            return True

        seen_paths.add(job.output_path)

    return False


def sort_results(results: typing.List[RenderResult]) -> typing.List[RenderResult]:
    """Sort render results by record index

    Args:
        results: Render results

    Returns:
        Sorted render results
    """
    return sorted(results, key=lambda result: result.record_index)
