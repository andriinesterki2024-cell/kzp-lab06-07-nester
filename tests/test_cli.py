"""Тести командного рядка та кодів завершення."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys

from conftest import DATA, ROOT
from kzp_lab06.cli import EXIT_DATA, EXIT_OK, EXIT_WRITE, main


def test_success(tmp_path, capsys):
    out = tmp_path / "report.txt"
    assert main([str(DATA / "input.csv"), str(out)]) == EXIT_OK
    assert out.read_text(encoding="utf-8") == (ROOT / "reports" / "summary.txt").read_text(
        encoding="utf-8"
    )
    assert "заявок: 7" in capsys.readouterr().out


def test_all_done_file_gives_empty_selection(tmp_path):
    out = tmp_path / "report.txt"
    assert main([str(DATA / "all-done.csv"), str(out)]) == EXIT_OK
    assert "Відкриті заявки (status != done): 0" in out.read_text(encoding="utf-8")


def test_unknown_option_gives_code_2(tmp_path):
    assert main([str(DATA / "input.csv"), str(tmp_path / "r.txt"), "--reference-date", "x"]) == 2


def test_broken_csv_gives_code_2_and_no_report(tmp_path, capsys):
    out = tmp_path / "report.txt"
    assert main([str(DATA / "broken.csv"), str(out)]) == EXIT_DATA
    assert "Помилка даних: Рядок 3: поле cost має бути числом" in capsys.readouterr().err
    assert not out.exists()


def test_missing_input(tmp_path):
    assert main([str(tmp_path / "nope.csv"), str(tmp_path / "r.txt")]) == EXIT_DATA


def test_empty_input_is_success(tmp_path):
    out = tmp_path / "r.txt"
    assert main([str(DATA / "empty.csv"), str(out)]) == EXIT_OK
    assert "Заявок у файлі: 0" in out.read_text(encoding="utf-8")


def test_same_input_and_output_is_refused(tmp_path, capsys):
    src = tmp_path / "in.csv"
    src.write_bytes((DATA / "input.csv").read_bytes())
    before = src.read_bytes()
    assert main([str(src), str(src)]) == EXIT_DATA
    assert src.read_bytes() == before
    assert "збігаються" in capsys.readouterr().err


def test_write_error_gives_code_3(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()
    assert main([str(DATA / "input.csv"), str(directory)]) == EXIT_WRITE


def test_run_as_module_in_subprocess(tmp_path):
    out = tmp_path / "r.txt"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run(
        [sys.executable, "-m", "kzp_lab06", str(DATA / "broken.csv"), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert done.returncode == EXIT_DATA
    assert "Рядок 3" in done.stderr
    assert "Traceback" not in done.stderr


def test_import_does_not_run_cli(capsys):
    importlib.reload(importlib.import_module("kzp_lab06.cli"))
    assert capsys.readouterr().out == ""
