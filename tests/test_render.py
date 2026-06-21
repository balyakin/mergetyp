import os
import subprocess
from pathlib import Path

import pytest

from mergetyp.exceptions import OutputWriteError, TypstCompileError, TypstNotFoundError, TypstTimeoutError
from mergetyp.render import find_typst, render_record


def test_find_typst_returns_path_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    monkeypatch.setattr("mergetyp.render.shutil.which", lambda name: "/usr/local/bin/typst")

    # ACT
    result = find_typst()

    # ASSERT
    assert result == "/usr/local/bin/typst"


def test_find_typst_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # ARRANGE
    monkeypatch.setattr("mergetyp.render.shutil.which", lambda name: None)

    # ACT
    with pytest.raises(TypstNotFoundError) as error_info:
        find_typst()

    # ASSERT
    assert "'typst' CLI not found" in error_info.value.message


def test_render_record_calls_subprocess_with_root_and_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    calls = []

    def fake_run(args, capture_output, check, timeout):
        calls.append(
            {
                "args": args,
                "capture_output": capture_output,
                "check": check,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"%PDF", stderr=b"")

    monkeypatch.setattr("mergetyp.render.subprocess.run", fake_run)

    # ACT
    result = render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert result == b"%PDF"
    assert calls[0]["args"][0:5] == ["/bin/typst", "compile", "--root", str(tmp_path), "--format"]
    assert calls[0]["args"][-1] == "-"
    assert calls[0]["timeout"] == 12.5
    assert calls[0]["capture_output"] is True
    assert calls[0]["check"] is False


def test_render_record_escapes_template_name_in_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / 'my"template\\name.typ'
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    sources = []

    def fake_run(args, capture_output, check, timeout):
        temporary_path = Path(args[-2])
        sources.append(temporary_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"%PDF", stderr=b"")

    monkeypatch.setattr("mergetyp.render.subprocess.run", fake_run)

    # ACT
    render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert sources == ['#import "my\\"template\\\\name.typ": render\n#render((name: "Alice",))\n']


def test_render_record_closes_descriptor_when_fdopen_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")
    temporary_path = tmp_path / ".mergetyp_gen_test.typ"
    descriptor_number = os.open(str(temporary_path), os.O_CREAT | os.O_RDWR)
    closed_descriptors = []
    original_close = os.close

    def fake_mkstemp(prefix, suffix, dir):
        return descriptor_number, str(temporary_path)

    def fake_fdopen(descriptor, mode, encoding):
        raise OSError("fdopen failed")

    def fake_close(descriptor):
        closed_descriptors.append(descriptor)
        original_close(descriptor)

    monkeypatch.setattr("mergetyp.render.tempfile.mkstemp", fake_mkstemp)
    monkeypatch.setattr("mergetyp.render.os.fdopen", fake_fdopen)
    monkeypatch.setattr("mergetyp.render.os.close", fake_close)

    # ACT
    with pytest.raises(OutputWriteError) as error_info:
        render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert "cannot execute typst" in error_info.value.message
    assert closed_descriptors == [descriptor_number]


def test_render_record_non_zero_raises_typst_compile_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")

    def fake_run(args, capture_output, check, timeout):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout=b"", stderr=b"bad typst")

    monkeypatch.setattr("mergetyp.render.subprocess.run", fake_run)

    # ACT
    with pytest.raises(TypstCompileError) as error_info:
        render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert "bad typst" in error_info.value.message
    assert not list(tmp_path.glob(".mergetyp_gen_*.typ"))


def test_render_record_timeout_raises_typst_timeout_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")

    def fake_run(args, capture_output, check, timeout):
        raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)

    monkeypatch.setattr("mergetyp.render.subprocess.run", fake_run)

    # ACT
    with pytest.raises(TypstTimeoutError) as error_info:
        render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert "timed out" in error_info.value.message
    assert not list(tmp_path.glob(".mergetyp_gen_*.typ"))


def test_render_record_removes_temporary_file_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")

    def fake_run(args, capture_output, check, timeout):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"%PDF", stderr=b"")

    monkeypatch.setattr("mergetyp.render.subprocess.run", fake_run)

    # ACT
    render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert not list(tmp_path.glob(".mergetyp_gen_*.typ"))


def test_render_record_permission_error_raises_output_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ARRANGE
    template_path = tmp_path / "template.typ"
    template_path.write_text("#let render(record) = []", encoding="utf-8")

    def raise_permission_error(prefix, suffix, dir):
        raise PermissionError("denied")

    monkeypatch.setattr("mergetyp.render.tempfile.mkstemp", raise_permission_error)

    # ACT
    with pytest.raises(OutputWriteError) as error_info:
        render_record(template_path, {"name": "Alice"}, "/bin/typst", 12.5)

    # ASSERT
    assert "cannot write temporary Typst file" in error_info.value.message
