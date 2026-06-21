import argparse
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from mergetyp import cli
from mergetyp.contracts import RuntimeSettings
from mergetyp.exceptions import TypstNotFoundError


def test_missing_template_returns_exit_code_2(tmp_path: Path) -> None:
    # ARRANGE
    data_path = tmp_path / "data.csv"
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    template_path = tmp_path / "missing.typ"

    # ACT
    exit_code = cli.main([str(template_path), str(data_path)])

    # ASSERT
    assert exit_code == 2


def test_missing_data_returns_exit_code_2(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path = tmp_path / "missing.csv"

    # ACT
    exit_code = cli.main([str(template_path), str(data_path)])

    # ASSERT
    assert exit_code == 2


def test_invalid_jobs_returns_exit_code_1(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--jobs", "0"])

    # ASSERT
    assert exit_code == 1


def test_invalid_compile_timeout_returns_exit_code_1(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--compile-timeout", "0"])

    # ASSERT
    assert exit_code == 1


def test_verbose_and_quiet_together_return_1(tmp_path: Path) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    args = argparse.Namespace(
        template=str(template_path),
        data=str(data_path),
        output="out",
        name_pattern="{index}.pdf",
        jobs=1,
        compile_timeout=60.0,
        no_coerce=False,
        dry_run=False,
        limit=None,
        offset=0,
        encoding="utf-8",
        collision="error",
        verbose=True,
        quiet=True,
    )

    # ACT
    with pytest.raises(ValidationError) as error_info:
        cli.build_runtime_settings(args)
    exit_code = cli.main([str(template_path), str(data_path), "--verbose", "--quiet"])

    # ASSERT
    assert "--verbose and --quiet cannot be used together" in str(error_info.value)
    assert exit_code == 1


def test_pydantic_validation_error_on_settings_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    def raise_validation_error(args):
        RuntimeSettings(template_path=Path("template.typ"), data_path=Path("data.csv"), verbose=True, quiet=True)

    monkeypatch.setattr(cli, "build_runtime_settings", raise_validation_error)

    # ACT
    exit_code = cli.main(["template.typ", "data.csv"])

    # ASSERT
    assert exit_code == 1


def test_expected_mergetyp_error_returns_its_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    def raise_error(argv):
        raise TypstNotFoundError("ERROR: typst missing")

    monkeypatch.setattr(cli, "run_main", raise_error)

    # ACT
    exit_code = cli.main(["template.typ", "data.csv"])

    # ASSERT
    assert exit_code == 1


def test_keyboard_interrupt_returns_130(monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    def raise_interrupt(argv):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "run_main", raise_interrupt)

    # ACT
    exit_code = cli.main(["template.typ", "data.csv"])

    # ASSERT
    assert exit_code == 130


def test_unexpected_exception_returns_1_and_logs_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # ARRANGE
    logging.getLogger("mergetyp").propagate = True

    def raise_runtime_error(argv):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "run_main", raise_runtime_error)
    caplog.set_level(logging.ERROR, logger="mergetyp")

    # ACT
    exit_code = cli.main(["template.typ", "data.csv"])

    # ASSERT
    assert exit_code == 1
    assert "unexpected fatal error" in caplog.text


def test_version_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    # ARRANGE
    argv = ["--version"]

    # ACT
    exit_code = cli.main(argv)
    captured = capsys.readouterr()

    # ASSERT
    assert exit_code == 0
    assert "mergetyp 0.1.0" in captured.out


def test_offset_beyond_records_returns_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_data", lambda path, coerce, encoding: [{"name": "Alice"}])

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--offset", "2"])

    # ASSERT
    assert exit_code == 1


def test_limit_and_offset_empty_selection_returns_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_data", lambda path, coerce, encoding: [{"name": "Alice"}])

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--offset", "1", "--limit", "1"])

    # ASSERT
    assert exit_code == 1


def test_no_coerce_passes_false_to_load_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    calls = []

    def fake_load_data(path, coerce, encoding):
        calls.append((path, coerce, encoding))
        return [{"name": "Alice"}]

    monkeypatch.setattr(cli, "load_data", fake_load_data)
    monkeypatch.setattr(cli, "run_batch", lambda settings, records, logger: [])

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--no-coerce"])

    # ASSERT
    assert exit_code == 0
    assert calls[0][1] is False


def test_successful_flow_loads_data_runs_batch_and_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    data_path = tmp_path / "data.csv"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    data_path.write_text("name\nAlice\n", encoding="utf-8")
    calls = []

    def fake_run_batch(settings: RuntimeSettings, records, logger):
        calls.append((settings, records))
        return []

    monkeypatch.setattr(cli, "load_data", lambda path, coerce, encoding: [{"name": "Alice"}])
    monkeypatch.setattr(cli, "run_batch", fake_run_batch)

    # ACT
    exit_code = cli.main([str(template_path), str(data_path), "--dry-run"])

    # ASSERT
    assert exit_code == 0
    assert calls[0][1] == [{"name": "Alice"}]
