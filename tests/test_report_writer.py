"""Тести контекстного менеджера ReportWriter (завдання із зірочкою)."""

from __future__ import annotations

import pytest

from kzp_lab06.reporting import ReportWriter


def test_success_replaces_report_and_leaves_no_temp(tmp_path):
    target = tmp_path / "report.txt"
    with ReportWriter(target) as stream:
        stream.write("Звіт\n")
    assert target.read_bytes() == "Звіт\n".encode()
    assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]


def test_exception_closes_file_and_keeps_old_report(tmp_path):
    target = tmp_path / "report.txt"
    target.write_text("старий звіт\n", encoding="utf-8")
    writer = ReportWriter(target)
    with pytest.raises(RuntimeError, match="збій"):
        with writer as stream:
            stream.write("недописаний")
            raise RuntimeError("збій")
    assert writer.closed
    assert target.read_text(encoding="utf-8") == "старий звіт\n"
    assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]


def test_exception_is_not_suppressed(tmp_path):
    writer = ReportWriter(tmp_path / "r.txt")
    writer.__enter__()
    assert writer.__exit__(ValueError, ValueError("x"), None) is False


def test_replace_failure_removes_temp(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()
    with pytest.raises(OSError):
        with ReportWriter(directory) as stream:
            stream.write("x")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dir"]
