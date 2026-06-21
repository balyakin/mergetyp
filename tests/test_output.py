import logging
import os
from pathlib import Path

import pytest

from mergetyp.contracts import RenderJob
from mergetyp.exceptions import OutputCollisionError, OutputWriteError
from mergetyp.output import build_render_jobs, get_unique_output_path, resolve_collisions, write_pdf_atomic


def test_write_pdf_atomic_writes_target_file(tmp_path: Path) -> None:
    # ARRANGE
    output_path = tmp_path / "out.pdf"

    # ACT
    write_pdf_atomic(output_path, b"%PDF")

    # ASSERT
    assert output_path.read_bytes() == b"%PDF"


def test_write_pdf_atomic_removes_temp_after_success(tmp_path: Path) -> None:
    # ARRANGE
    output_path = tmp_path / "out.pdf"
    temp_path = tmp_path / "out.pdf.tmp"

    # ACT
    write_pdf_atomic(output_path, b"%PDF")

    # ASSERT
    assert not temp_path.exists()


def test_write_pdf_atomic_removes_temp_after_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    output_path = tmp_path / "out.pdf"
    temp_path = tmp_path / "out.pdf.tmp"

    def raise_os_error(source: str, destination: str) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", raise_os_error)

    # ACT
    with pytest.raises(OutputWriteError) as error_info:
        write_pdf_atomic(output_path, b"%PDF")

    # ASSERT
    assert "cannot write output file" in error_info.value.message
    assert not temp_path.exists()


def test_write_pdf_atomic_does_not_remove_existing_tmp_named_file(tmp_path: Path) -> None:
    # ARRANGE
    output_path = tmp_path / "out.pdf"
    existing_tmp_path = tmp_path / "out.pdf.tmp"
    existing_tmp_path.write_bytes(b"existing")

    # ACT
    write_pdf_atomic(output_path, b"%PDF")

    # ASSERT
    assert output_path.read_bytes() == b"%PDF"
    assert existing_tmp_path.read_bytes() == b"existing"


def test_collision_error_fails_on_duplicate_generated_names(tmp_path: Path) -> None:
    # ARRANGE
    logger = logging.getLogger("test")
    records = [{"name": "Alice"}, {"name": "Alice"}]

    # ACT
    with pytest.raises(OutputCollisionError) as error_info:
        build_render_jobs(records, tmp_path, "{name}.pdf", "error", logger)

    # ASSERT
    assert "collides with record #1" in error_info.value.message


def test_collision_error_fails_on_existing_file(tmp_path: Path) -> None:
    # ARRANGE
    logger = logging.getLogger("test")
    output_path = tmp_path / "Alice.pdf"
    output_path.write_bytes(b"existing")
    records = [{"name": "Alice"}]

    # ACT
    with pytest.raises(OutputCollisionError) as error_info:
        build_render_jobs(records, tmp_path, "{name}.pdf", "error", logger)

    # ASSERT
    assert "would overwrite existing file" in error_info.value.message


def test_collision_error_reports_duplicate_and_existing_file(tmp_path: Path) -> None:
    # ARRANGE
    logger = logging.getLogger("test")
    output_path = tmp_path / "Alice.pdf"
    output_path.write_bytes(b"existing")
    records = [{"name": "Alice"}, {"name": "Alice"}]

    # ACT
    with pytest.raises(OutputCollisionError) as error_info:
        build_render_jobs(records, tmp_path, "{name}.pdf", "error", logger)

    # ASSERT
    assert error_info.value.message.count("would overwrite existing file") == 1
    assert error_info.value.message.count("collides with record #1") == 1


def test_collision_rename_has_max_attempts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    output_path = tmp_path / "Alice.pdf"
    suffix_path = tmp_path / "Alice_2.pdf"
    output_path.write_bytes(b"existing")
    suffix_path.write_bytes(b"existing")
    monkeypatch.setattr("mergetyp.output.MAX_RENAME_ATTEMPTS", 1, raising=False)

    # ACT
    with pytest.raises(OutputWriteError) as error_info:
        get_unique_output_path(output_path, set())

    # ASSERT
    assert "cannot find unique output path" in error_info.value.message


def test_collision_rename_generates_suffixes(tmp_path: Path) -> None:
    # ARRANGE
    logger = logging.getLogger("test")
    output_path = tmp_path / "Alice.pdf"
    output_path.write_bytes(b"existing")
    records = [{"name": "Alice"}, {"name": "Alice"}]

    # ACT
    jobs = build_render_jobs(records, tmp_path, "{name}.pdf", "rename", logger)

    # ASSERT
    assert [job.output_path.name for job in jobs] == ["Alice_2.pdf", "Alice_3.pdf"]


def test_collision_overwrite_keeps_original_path_and_logs_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # ARRANGE
    logger = logging.getLogger("test-output")
    caplog.set_level(logging.WARNING, logger="test-output")
    output_path = tmp_path / "Alice.pdf"
    output_path.write_bytes(b"existing")
    jobs = [RenderJob(record_index=1, record={"name": "Alice"}, output_path=output_path)]

    # ACT
    resolved_jobs = resolve_collisions(jobs, "overwrite", logger)

    # ASSERT
    assert resolved_jobs[0].output_path == output_path
    assert "would overwrite existing file" in caplog.text
