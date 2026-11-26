"""Тести читання CSV і перетворення полів."""

from __future__ import annotations

from datetime import date

import pytest

from conftest import DATA, HEADER
from kzp_lab06.errors import DataError
from kzp_lab06.loader import iter_records, load_records, parse_row
from kzp_lab06.models import PaidRepair, WarrantyRepair


def test_control_file_has_seven_records():
    records = load_records(DATA / "input.csv")
    assert len(records) == 7
    assert [r.customer for r in records][:2] == ["Іваненко, Петро", "Коваль Оксана"]


def test_field_types_after_conversion():
    first = load_records(DATA / "input.csv")[0]
    assert first == PaidRepair(
        "Іваненко, Петро", "Ноутбук", "Заміна термопасти", date(2026, 1, 5), 650.0, "done"
    )
    assert isinstance(first.date, date)
    assert isinstance(first.cost, float)


def test_loader_creates_subtypes():
    kinds = [type(r) for r in load_records(DATA / "input.csv")]
    assert kinds.count(WarrantyRepair) == 1
    assert kinds.count(PaidRepair) == 6


def test_comma_in_quoted_field():
    assert load_records(DATA / "input.csv")[0].customer == "Іваненко, Петро"


def test_zero_cost_is_allowed():
    assert load_records(DATA / "input.csv")[4].cost == 0.0


def test_whitespace_and_status_case_are_normalized(write_csv):
    path = write_csv(
        f"{HEADER}\n  Коваль   Оксана ,Планшет , Діагностика ,2026-01-10, 10 , IN_PROGRESS \n"
    )
    record = load_records(path)[0]
    assert record.customer == "Коваль Оксана"
    assert record.device == "Планшет"
    assert record.status == "in_progress"
    assert record.cost == 10.0


def test_column_order_does_not_matter(write_csv):
    path = write_csv(
        "status,cost,date,fault,device,customer\nnew,100,2026-01-01,Ремонт,Ноутбук,Іван\n"
    )
    record = load_records(path)[0]
    assert (record.customer, record.cost, record.status) == ("Іван", 100.0, "new")


def test_crlf_line_endings(write_csv):
    path = write_csv(f"{HEADER}\r\nА,Б,В,2026-01-01,1,new\r\nГ,Д,Е,2026-01-02,2,done\r\n")
    assert [r.cost for r in load_records(path)] == [1.0, 2.0]


def test_multiline_quoted_field(write_csv):
    path = write_csv(f'{HEADER}\n"Бондар\nМарія",Ноутбук,Ремонт,2026-01-01,1,new\n')
    assert load_records(path)[0].customer == "Бондар Марія"


def test_header_only_is_empty_input():
    assert load_records(DATA / "empty.csv") == []


def test_zero_byte_file_is_rejected(write_csv):
    with pytest.raises(DataError, match="немає рядка заголовка"):
        load_records(write_csv(""))


def test_missing_column(write_csv):
    path = write_csv("customer,device,fault,date,cost\nА,Б,В,2026-01-01,1\n")
    with pytest.raises(DataError, match="У заголовку немає стовпців: status"):
        load_records(path)


def test_missing_value_in_row(write_csv):
    path = write_csv(f"{HEADER}\nА,Б,В,2026-01-01,1,new\nА,Б,В,,1,new\n")
    with pytest.raises(DataError, match="Рядок 3: немає значення поля date"):
        load_records(path)


def test_short_row(write_csv):
    path = write_csv(f"{HEADER}\nА,Б,В\n")
    with pytest.raises(DataError, match="Рядок 2: немає значення поля date"):
        load_records(path)


def test_unquoted_comma_gives_too_many_values(write_csv):
    path = write_csv(f"{HEADER}\nІваненко, Петро,Ноутбук,Ремонт,2026-01-01,1,new\n")
    with pytest.raises(DataError, match="Рядок 2: забагато значень"):
        load_records(path)


def test_broken_number_keeps_cause():
    with pytest.raises(DataError, match="Рядок 3: поле cost має бути числом") as info:
        load_records(DATA / "broken.csv")
    assert isinstance(info.value.__cause__, ValueError)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_cost(write_csv, value):
    path = write_csv(f"{HEADER}\nА,Б,В,2026-01-01,{value},new\n")
    with pytest.raises(DataError, match="cost"):
        load_records(path)


def test_negative_cost(write_csv):
    path = write_csv(f"{HEADER}\nА,Б,В,2026-01-01,-5,new\n")
    with pytest.raises(DataError, match="Рядок 2: поле cost не може бути від'ємним"):
        load_records(path)


def test_bad_date_keeps_cause(write_csv):
    path = write_csv(f"{HEADER}\nА,Б,В,01.01.2026,1,new\n")
    with pytest.raises(DataError, match="Рядок 2: поле date має бути датою") as info:
        load_records(path)
    assert isinstance(info.value.__cause__, ValueError)


@pytest.mark.parametrize("status", ["closed", "готово", "doneX"])
def test_unknown_status(write_csv, status):
    path = write_csv(f"{HEADER}\nА,Б,В,2026-01-01,1,{status}\n")
    with pytest.raises(DataError, match="Рядок 2: поле status має бути одним із"):
        load_records(path)


def test_unclosed_quote_is_reported(write_csv):
    path = write_csv(f'{HEADER}\n"А,Б,В,2026-01-01,1,new\n')
    with pytest.raises(DataError):
        load_records(path)


def test_missing_file_keeps_os_error(tmp_path):
    with pytest.raises(DataError, match="Не вдалося прочитати файл") as info:
        load_records(tmp_path / "nope.csv")
    assert isinstance(info.value.__cause__, OSError)


def test_not_utf8_file(write_csv):
    path = write_csv(f"{HEADER}\nІван,Б,В,2026-01-01,1,new\n", encoding="cp1251")
    with pytest.raises(DataError, match="Не вдалося прочитати файл") as info:
        load_records(path)
    assert isinstance(info.value.__cause__, UnicodeDecodeError)


def test_iter_records_is_lazy(write_csv):
    path = write_csv(f"{HEADER}\nА,Б,В,2026-01-01,1,new\nА,Б,В,2026-01-01,x,new\n")
    records = iter_records(path)
    assert next(records).cost == 1.0  # хибний другий рядок ще не прочитано
    with pytest.raises(DataError):
        next(records)


def test_parse_row_directly():
    row = {
        "customer": "Б",
        "device": "В",
        "fault": "Г",
        "date": "2026-01-11",
        "cost": "1.5",
        "status": "done",
    }
    assert parse_row(row, 9).cost == 1.5
