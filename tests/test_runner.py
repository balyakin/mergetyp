import logging
from pathlib import Path

import pytest

from mergetyp.cli import report_results
from mergetyp.contracts import RenderJob, RenderResult, RuntimeSettings
from mergetyp.exceptions import TypstCompileError
from mergetyp.runner import run_batch, run_jobs_parallel


def make_settings(tmp_path: Path, jobs: int, dry_run: bool = False) -> RuntimeSettings:
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    return RuntimeSettings(
        template_path=template_path,
        data_path=data_path,
        output_dir=tmp_path / "out",
        name_pattern="{name}.pdf",
        jobs=jobs,
        dry_run=dry_run,
    )


def test_dry_run_does_not_call_render_record(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=2, dry_run=True)
    logger = logging.getLogger("test-runner")

    def fail_render(*args, **kwargs):
        raise AssertionError("render_record should not be called")

    monkeypatch.setattr("mergetyp.runner.render_record", fail_render)

    # ACT
    results = run_batch(settings, [{"name": "Alice"}], logger)

    # ASSERT
    assert len(results) == 1
    assert results[0].ok is True
    assert not results[0].output_path.exists()
    assert not settings.output_dir.exists()


def test_sequential_mode_processes_all_jobs(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=1)
    logger = logging.getLogger("test-runner")
    written = []
    monkeypatch.setattr("mergetyp.runner.find_typst", lambda: "/bin/typst")
    monkeypatch.setattr("mergetyp.runner.render_record", lambda template, record, typst_bin, timeout: b"%PDF")
    monkeypatch.setattr("mergetyp.runner.write_pdf_atomic", lambda output_path, pdf_bytes: written.append(output_path))

    # ACT
    results = run_batch(settings, [{"name": "Alice"}, {"name": "Bob"}], logger)

    # ASSERT
    assert [result.ok for result in results] == [True, True]
    assert [path.name for path in written] == ["Alice.pdf", "Bob.pdf"]


def test_parallel_mode_processes_all_jobs(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=2)
    logger = logging.getLogger("test-runner")
    written = []
    monkeypatch.setattr("mergetyp.runner.find_typst", lambda: "/bin/typst")
    monkeypatch.setattr("mergetyp.runner.render_record", lambda template, record, typst_bin, timeout: b"%PDF")
    monkeypatch.setattr("mergetyp.runner.write_pdf_atomic", lambda output_path, pdf_bytes: written.append(output_path))

    # ACT
    results = run_batch(settings, [{"name": "Alice"}, {"name": "Bob"}], logger)

    # ASSERT
    assert [result.record_index for result in results] == [1, 2]
    assert [result.ok for result in results] == [True, True]
    assert sorted(path.name for path in written) == ["Alice.pdf", "Bob.pdf"]


def test_failed_job_does_not_hide_other_failures_or_successes(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=1)
    logger = logging.getLogger("test-runner")
    monkeypatch.setattr("mergetyp.runner.find_typst", lambda: "/bin/typst")

    def fake_render(template, record, typst_bin, timeout):
        if record["name"] == "Bad":
            raise TypstCompileError("ERROR: bad record")
        return b"%PDF"

    monkeypatch.setattr("mergetyp.runner.render_record", fake_render)
    monkeypatch.setattr("mergetyp.runner.write_pdf_atomic", lambda output_path, pdf_bytes: None)

    # ACT
    results = run_batch(settings, [{"name": "Alice"}, {"name": "Bad"}, {"name": "Bob"}], logger)

    # ASSERT
    assert [result.ok for result in results] == [True, False, True]
    assert results[1].error_message == "ERROR: bad record"


def test_parallel_failed_job_does_not_hide_other_results(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=2)
    logger = logging.getLogger("test-runner")
    monkeypatch.setattr("mergetyp.runner.find_typst", lambda: "/bin/typst")

    def fake_render(template, record, typst_bin, timeout):
        if record["name"] == "Bad":
            raise TypstCompileError("ERROR: bad record")
        return b"%PDF"

    monkeypatch.setattr("mergetyp.runner.render_record", fake_render)
    monkeypatch.setattr("mergetyp.runner.write_pdf_atomic", lambda output_path, pdf_bytes: None)

    # ACT
    results = run_batch(settings, [{"name": "Alice"}, {"name": "Bad"}, {"name": "Bob"}], logger)

    # ASSERT
    assert [result.record_index for result in results] == [1, 2, 3]
    assert [result.ok for result in results] == [True, False, True]
    assert results[1].error_message == "ERROR: bad record"


def test_parallel_keyboard_interrupt_cancels_submitted_futures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=2)
    logger = logging.getLogger("test-runner")
    jobs = [
        RenderJob(record_index=1, record={"name": "Alice"}, output_path=tmp_path / "Alice.pdf"),
        RenderJob(record_index=2, record={"name": "Bob"}, output_path=tmp_path / "Bob.pdf"),
    ]
    cancelled = []
    shutdown_calls = []

    class FakeFuture:
        def __init__(self, record_index: int) -> None:
            self.record_index = record_index

        def cancel(self) -> bool:
            cancelled.append(self.record_index)
            return True

    class FakeExecutor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> bool:
            shutdown_calls.append({"wait": True, "cancel_futures": False})
            return False

        def submit(self, function, job, settings_arg, typst_bin, logger_arg):
            return FakeFuture(job.record_index)

        def shutdown(self, wait: bool, cancel_futures: bool = False) -> None:
            shutdown_calls.append({"wait": wait, "cancel_futures": cancel_futures})

    def raise_keyboard_interrupt(futures):
        raise KeyboardInterrupt

    monkeypatch.setattr("mergetyp.runner.ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr("mergetyp.runner.as_completed", raise_keyboard_interrupt)

    # ACT
    with pytest.raises(KeyboardInterrupt):
        run_jobs_parallel(jobs, settings, "/bin/typst", logger)

    # ASSERT
    assert cancelled == [1, 2]
    assert shutdown_calls == [{"wait": False, "cancel_futures": True}]


def test_duplicate_overwrite_paths_run_sequentially(tmp_path: Path, monkeypatch) -> None:
    # ARRANGE
    settings = make_settings(tmp_path, jobs=2)
    settings = settings.model_copy(update={"collision": "overwrite"})
    logger = logging.getLogger("test-runner")
    monkeypatch.setattr("mergetyp.runner.find_typst", lambda: "/bin/typst")
    monkeypatch.setattr("mergetyp.runner.render_record", lambda template, record, typst_bin, timeout: b"%PDF")
    monkeypatch.setattr("mergetyp.runner.write_pdf_atomic", lambda output_path, pdf_bytes: None)

    def fail_parallel(*args, **kwargs):
        raise AssertionError("duplicate output paths must not use parallel writes")

    monkeypatch.setattr("mergetyp.runner.run_jobs_parallel", fail_parallel)

    # ACT
    results = run_batch(settings, [{"name": "Alice"}, {"name": "Alice"}], logger)

    # ASSERT
    assert [result.ok for result in results] == [True, True]
    assert results[0].output_path == results[1].output_path


def test_report_results_counts_success_and_errors(caplog) -> None:
    # ARRANGE
    logger = logging.getLogger("test-summary")
    caplog.set_level(logging.INFO, logger="test-summary")
    results = [
        RenderResult(record_index=1, output_path=Path("a.pdf"), ok=True),
        RenderResult(record_index=2, output_path=Path("b.pdf"), ok=False, error_message="ERROR: bad"),
    ]

    # ACT
    exit_code = report_results(results, dry_run=False, logger=logger)

    # ASSERT
    assert exit_code == 1
    assert "ERROR: bad" in caplog.text
    assert "1/2 PDF(s) generated" in caplog.text
