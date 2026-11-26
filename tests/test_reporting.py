"""Тести тексту звіту та запису файла."""

from __future__ import annotations

import random
from conftest import ROOT
from kzp_lab06.analysis import build_report
from kzp_lab06.loader import load_records
from kzp_lab06.reporting import format_report, write_report


def _text(records):
    return format_report(build_report(records))


def test_report_matches_saved_example():
    records = load_records(ROOT / "data" / "input.csv")
    expected = (ROOT / "reports" / "summary.txt").read_text(encoding="utf-8")
    assert _text(records) == expected


def test_report_does_not_depend_on_record_order():
    records = load_records(ROOT / "data" / "input.csv")
    shuffled = records[:]
    random.Random(16).shuffle(shuffled)
    assert _text(shuffled) == _text(records)


def test_empty_report():
    text = _text([])
    assert "Заявок у файлі: 0" in text
    assert "Найдорожчий ремонт: немає" in text
    assert "Загальна вартість заявок: 0.00 грн" in text


def test_write_report_creates_dirs_utf8_and_lf(tmp_path):
    target = tmp_path / "a" / "b" / "report.txt"
    write_report(target, "Звіт\nрядок\n")
    assert target.read_bytes() == "Звіт\nрядок\n".encode()


def test_write_report_overwrites_longer_file(tmp_path):
    target = tmp_path / "report.txt"
    target.write_text("довгий старий вміст\n" * 10, encoding="utf-8")
    write_report(target, "новий\n")
    assert target.read_text(encoding="utf-8") == "новий\n"


def test_numbers_have_two_decimals():
    records = load_records(ROOT / "data" / "input.csv")
    assert "Вартість відкритих заявок: 11350.00 грн" in _text(records)
    assert "  Діагностика: 0.00 грн" in _text(records)
