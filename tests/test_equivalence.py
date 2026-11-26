"""Еквівалентність словникової моделі ЛР6 (tests/legacy_v6) і об'єктної моделі ЛР7."""

from __future__ import annotations

import random

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

FILES = ["input.csv", "input-lab07.csv", "empty.csv", "all-done.csv"]


@pytest.mark.parametrize("name", FILES)
def test_reports_are_identical(name):
    path = DATA / name
    old = old_reporting.format_report(old_analysis.build_report(old_loader.load_records(path)))
    new = format_report(build_report(load_records(path)))
    assert new == old


@pytest.mark.parametrize("seed", range(10))
def test_reports_are_identical_for_shuffled_subsets(write_csv, seed):
    lines = (DATA / "input-lab07.csv").read_text(encoding="utf-8").splitlines()[1:]
    lines += (DATA / "input.csv").read_text(encoding="utf-8").splitlines()[1:]
    rng = random.Random(seed)
    sample = rng.sample(lines, rng.randint(0, len(lines)))
    path = write_csv(HEADER + "\n" + "\n".join(sample) + ("\n" if sample else ""))
    old = old_reporting.format_report(old_analysis.build_report(old_loader.load_records(path)))
    new = format_report(build_report(load_records(path)))
    assert new == old


def test_same_values_through_dict_and_attributes():
    old = old_loader.load_records(DATA / "input.csv")
    new = load_records(DATA / "input.csv")
    for record, order in zip(old, new, strict=True):
        for field in ("customer", "device", "fault", "date", "cost", "status"):
            assert record[field] == getattr(order, field)


BROKEN_ROWS = [
    ",Ноутбук,Ремонт,2026-01-01,1,new",
    "Іван,,Ремонт,2026-01-01,1,new",
    "Іван,Ноутбук,Ремонт,01.01.2026,1,new",
    "Іван,Ноутбук,Ремонт,2026-01-01,abc,new",
    "Іван,Ноутбук,Ремонт,2026-01-01,-5,new",
    "Іван,Ноутбук,Ремонт,2026-01-01,nan,new",
    "Іван,Ноутбук,Ремонт,2026-01-01,1,closed",
    "Іван,Ноутбук,Ремонт,2026-01-01,1,",
    "Іваненко, Петро,Ноутбук,Ремонт,2026-01-01,1,new",
    "Іван,Ноутбук,Ремонт",
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
    orders = load_records(DATA / "input-lab07.csv")
    duplicates = [o for o in orders if o.customer == "Бондар Марія"]
    assert len(duplicates) == 2
    assert duplicates[0] == duplicates[1]
    assert duplicates[0] is not duplicates[1]
