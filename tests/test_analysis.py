"""Тести обчислень варіанта 16."""

from __future__ import annotations

from datetime import date

import pytest

from conftest import DATA
from kzp_lab06.analysis import (
    build_report,
    cost_by_fault,
    make_summary,
    most_expensive,
    open_orders,
    preview,
    stream_summary,
    uk_key,
    unique_devices,
)
from kzp_lab06.loader import iter_records, load_records


@pytest.fixture
def records():
    return load_records(DATA / "input.csv")


def test_is_open_means_status_not_done(records):
    assert [r.is_open for r in records] == [False, True, True, True, True, False, False]


def test_open_orders_sorted_by_date(records):
    opened = open_orders(records)
    assert [(r.date.isoformat(), r.customer) for r in opened] == [
        ("2026-01-02", "Шевчук Андрій"),
        ("2026-01-03", "Бондар Марія"),
        ("2026-01-08", "Коваль Оксана"),
        ("2026-01-10", "Коваль Оксана"),
    ]


def test_open_orders_empty_when_all_done():
    assert open_orders(load_records(DATA / "all-done.csv")) == []


def test_cost_by_fault_sums_and_orders_keys(records):
    totals = cost_by_fault(records)
    assert totals == {
        "Гарантія: заміна підшипника": 2750.0,
        "Діагностика": 0.0,
        "Заміна екрана": 6400.0,
        "Заміна компресора": 5400.0,
        "Заміна термопасти": 1750.0,
    }
    assert list(totals) == sorted(totals, key=uk_key)


def test_unique_devices_removes_duplicates(records):
    devices = unique_devices(records)
    assert isinstance(devices, set)
    assert devices == {"Ноутбук", "Планшет", "Пральна машина", "Смартфон", "Холодильник"}


def test_most_expensive(records):
    assert most_expensive(records).customer == "Шевчук Андрій"


def test_most_expensive_tie_takes_earlier_date(records):
    pair = [r for r in records if r.cost == 3200.0]
    assert most_expensive(list(reversed(pair))).date == date(2026, 1, 6)


def test_ukrainian_order():
    names = ["Яковенко", "Іваненко", "Ґудзь", "Гончар", "Єременко", "Андрієнко", "Їжак"]
    assert sorted(names, key=uk_key) == [
        "Андрієнко",
        "Гончар",
        "Ґудзь",
        "Єременко",
        "Іваненко",
        "Їжак",
        "Яковенко",
    ]


def test_make_summary_with_args_and_labels(records):
    assert make_summary(records, "new", "in_progress", new="Нові", in_progress="У роботі") == {
        "count": 4,
        "Нові": 2750.0,
        "У роботі": 8600.0,
    }


def test_make_summary_defaults(records):
    assert make_summary(records) == {"count": 0}
    assert make_summary(records, "done") == {"count": 3, "done": 4950.0}


def test_make_summary_minimum_cost(records):
    assert make_summary(records, "new", minimum_cost=100) == {"count": 1, "new": 2750.0}
    assert make_summary(records, "done", minimum_cost=10_000) == {"count": 0, "done": 0}


def test_make_summary_errors(records):
    with pytest.raises(ValueError, match="Невідомі стани: closed"):
        make_summary(records, "closed")
    with pytest.raises(ValueError, match="Підписи для невибраних станів: done"):
        make_summary(records, "new", done="Готові")


def test_empty_input_everywhere():
    assert open_orders([]) == []
    assert cost_by_fault([]) == {}
    assert unique_devices([]) == set()
    assert most_expensive([]) is None
    assert make_summary([], "new") == {"count": 0, "new": 0}


def test_build_report(records):
    report = build_report(records)
    assert report.count == 7
    assert len(report.open_orders) == 4
    assert report.open_cost == 11350.0
    assert report.total_cost == 16300.0
    assert report.devices[0] == "Ноутбук"
    assert report.most_expensive.cost == 5400.0


def test_build_report_does_not_modify_input(records):
    copy = [repr(r) for r in records]
    build_report(records)
    assert [repr(r) for r in records] == copy


def test_preview_reads_only_first_records():
    gen = iter_records(DATA / "input.csv")
    assert [r.customer for r in preview(gen, 2)] == ["Іваненко, Петро", "Коваль Оксана"]
    assert next(gen).customer == "Бондар Марія"


def test_stream_summary_equals_list_based(records):
    streamed = stream_summary(iter_records(DATA / "input.csv"))
    report = build_report(records)
    assert streamed["count"] == report.count
    assert streamed["open_orders"] == len(report.open_orders)
    assert streamed["open_cost"] == report.open_cost
    assert streamed["devices"] == len(report.devices)
    assert tuple(streamed["cost_by_fault"].items()) == report.cost_by_fault
    assert streamed["most_expensive_cost"] == report.most_expensive.cost
    assert streamed["total_cost"] == report.total_cost


def test_stream_summary_empty():
    assert stream_summary(iter([]))["most_expensive_cost"] is None
