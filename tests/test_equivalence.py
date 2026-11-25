"""Еквівалентність словникової моделі ЛР6 (tests/legacy_v6) і об'єктної моделі ЛР7."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from conftest import DATA, HEADER
from kzp_lab06.analysis import build_report
from kzp_lab06.errors import DataError
from kzp_lab06.loader import load_records
from kzp_lab06.reporting import format_report
from legacy_v6 import analysis as old_analysis
from legacy_v6 import loader as old_loader
from legacy_v6 import reporting as old_reporting
from legacy_v6.errors import DataError as OldDataError

DAYS = [date(2025, 12, 25) + timedelta(days=i) for i in range(22)]  # 2025-12-25 … 2026-01-15
FILES = ["input.csv", "input-lab07.csv", "empty.csv"]


@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("day", DAYS, ids=lambda d: d.isoformat())
def test_reports_are_identical_for_every_day(name, day):
    path = DATA / name
    old = old_reporting.format_report(old_analysis.build_report(old_loader.load_records(path), day))
    new = format_report(build_report(load_records(path), day))
    assert new == old


def test_same_values_through_dict_and_attributes():
    old = old_loader.load_records(DATA / "input.csv")
    new = load_records(DATA / "input.csv")
    for record, repair in zip(old, new, strict=True):
        for field in ("ticket", "client", "device", "received", "completed", "price", "days"):
            assert record[field] == getattr(repair, field)


BROKEN_ROWS = [
    "abc,А,Б,2026-01-01,2026-01-02,1",
    "0,А,Б,2026-01-01,2026-01-02,1",
    "1,,Б,2026-01-01,2026-01-02,1",
    "1,А,Б,01.01.2026,2026-01-02,1",
    "1,А,Б,2026-01-03,2026-01-02,1",
    "1,А,Б,2026-01-01,2026-01-02,abc",
    "1,А,Б,2026-01-01,2026-01-02,-5",
    "1,А,Б,2026-01-01,2026-01-02,nan",
    "1,Іваненко, Петро,Б,2026-01-01,2026-01-02,1",
    "1,А,Б",
]


@pytest.mark.parametrize("row", BROKEN_ROWS)
def test_error_messages_are_unchanged(write_csv, row):
    path = write_csv(f"{HEADER}\n{row}\n")
    with pytest.raises(OldDataError) as old:
        old_loader.load_records(path)
    with pytest.raises(DataError) as new:
        load_records(path)
    assert str(new.value) == str(old.value)


def test_duplicated_row_gives_equal_objects():
    repairs = load_records(DATA / "input-lab07.csv")
    duplicates = [r for r in repairs if r.ticket == 3]
    assert len(duplicates) == 2
    assert duplicates[0] == duplicates[1]
    assert duplicates[0] is not duplicates[1]
