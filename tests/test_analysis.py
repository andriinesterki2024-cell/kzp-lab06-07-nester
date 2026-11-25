"""Тести обчислень."""

from __future__ import annotations

from datetime import date

import pytest

from conftest import DATA
from kzp_lab06.analysis import (
    build_report,
    count_by_device,
    in_work,
    longest_repair,
    make_summary,
    preview,
    select_in_work,
    stream_summary,
    uk_key,
    unique_clients,
    workload,
)
from kzp_lab06.loader import iter_records, load_records

REF = date(2026, 1, 3)


@pytest.fixture
def records():
    return load_records(DATA / "input.csv")


def test_in_work_boundaries(records):
    by_ticket = {r["ticket"]: r for r in records}
    assert in_work(by_ticket[2], REF)  # прийнято саме цього дня
    assert not in_work(by_ticket[3], REF)  # завершено саме цього дня
    assert in_work(by_ticket[1], REF)  # останній день перед завершенням
    assert not in_work(by_ticket[5], REF)  # ще не прийнято


def test_select_in_work(records):
    assert [r["ticket"] for r in select_in_work(records, REF)] == [1, 2, 4, 6]


def test_select_in_work_empty_result(records):
    assert select_in_work(records, date(2026, 2, 1)) == []


def test_count_by_device(records):
    assert count_by_device(records) == {
        "Ноутбук": 2,
        "Планшет": 1,
        "Пральна машина": 1,
        "Смартфон": 2,
        "Холодильник": 1,
    }
    assert list(count_by_device(records)) == sorted(count_by_device(records), key=uk_key)


def test_unique_clients_removes_duplicates(records):
    clients = unique_clients(records)
    assert isinstance(clients, set)
    assert len(clients) == 6
    assert "Коваль Оксана" in clients


def test_workload(records):
    assert workload(records, REF) == {"in_work": 4, "total": 7, "percent": pytest.approx(57.142857)}


def test_workload_counts_ticket_once(records):
    twice = records + [dict(records[0])]
    assert workload(twice, REF)["total"] == 7


def test_longest_repair(records):
    assert longest_repair(records)["ticket"] == 4


def test_longest_repair_tie_takes_smaller_ticket(records):
    six_days = [r for r in records if r["days"] == 6]
    assert [r["ticket"] for r in six_days] == [3, 6]
    assert longest_repair(list(reversed(six_days)))["ticket"] == 3


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
    assert make_summary(records, "days", "price", days="Днів", price="Виторг") == {
        "count": 7,
        "Днів": 30.0,
        "Виторг": 13400.0,
    }


def test_make_summary_defaults(records):
    assert make_summary(records) == {"count": 7}
    assert make_summary(records, "price") == {"count": 7, "price": 13400.0}


def test_make_summary_minimum_days(records):
    assert make_summary(records, "days", minimum_days=6) == {"count": 3, "days": 22.0}
    assert make_summary(records, "price", minimum_days=100) == {"count": 0, "price": 0.0}


def test_make_summary_errors(records):
    with pytest.raises(ValueError, match="Невідомі метрики: weight"):
        make_summary(records, "weight")
    with pytest.raises(ValueError, match="Підписи для невибраних метрик: price"):
        make_summary(records, "days", price="Виторг")


def test_empty_input_everywhere():
    assert select_in_work([], REF) == []
    assert count_by_device([]) == {}
    assert unique_clients([]) == set()
    assert workload([], REF) == {"in_work": 0, "total": 0, "percent": 0.0}
    assert longest_repair([]) is None
    assert make_summary([], "days") == {"count": 0, "days": 0.0}


def test_build_report(records):
    report = build_report(records, REF)
    assert report["count"] == 7
    assert report["total_days"] == 30
    assert report["total_price"] == 13400.0
    assert report["clients"][0] == "Бондар Марія"
    assert report["longest"]["ticket"] == 4


def test_build_report_does_not_modify_input(records):
    copy = [dict(r) for r in records]
    build_report(records, REF)
    assert records == copy


def test_preview_reads_only_first_records():
    gen = iter_records(DATA / "input.csv")
    assert [r["ticket"] for r in preview(gen, 2)] == [1, 2]
    assert next(gen)["ticket"] == 3  # генератор продовжує з третього запису


def test_stream_summary_equals_list_based(records):
    streamed = stream_summary(iter_records(DATA / "input.csv"), REF)
    report = build_report(records, REF)
    assert streamed["count"] == report["count"]
    assert streamed["in_work"] == len(report["in_work"])
    assert streamed["clients"] == len(report["clients"])
    assert streamed["count_by_device"] == report["count_by_device"]
    assert streamed["longest_ticket"] == report["longest"]["ticket"]
    assert streamed["total_days"] == report["total_days"]
    assert streamed["total_price"] == report["total_price"]


def test_stream_summary_empty():
    assert stream_summary(iter([]), REF)["longest_ticket"] is None
