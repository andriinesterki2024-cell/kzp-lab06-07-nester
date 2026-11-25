"""Тести читання CSV і перетворення полів."""

from __future__ import annotations

from datetime import date

import pytest

from conftest import DATA, HEADER
from kzp_lab06.errors import DataError
from kzp_lab06.loader import iter_records, load_records, parse_row
from kzp_lab06.models import ApplianceRepair, GadgetRepair


def test_control_file_has_seven_records():
    records = load_records(DATA / "input.csv")
    assert len(records) == 7
    assert [r.ticket for r in records] == [1, 2, 3, 4, 5, 6, 7]


def test_field_types_and_derived_days():
    first = load_records(DATA / "input.csv")[0]
    assert first == GadgetRepair(
        1, "Іваненко, Петро", "Ноутбук", date(2026, 1, 1), date(2026, 1, 4), 650.0
    )
    assert first.days == 3
    assert isinstance(first.ticket, int)
    assert isinstance(first.price, float)


def test_loader_creates_subtypes():
    kinds = [type(r) for r in load_records(DATA / "input.csv")]
    assert kinds.count(ApplianceRepair) == 2
    assert kinds.count(GadgetRepair) == 5


def test_comma_and_doubled_quotes_in_field():
    records = load_records(DATA / "input.csv")
    assert records[6].client == 'О\'Коннор, "Шон"'


def test_zero_price_is_allowed():
    assert load_records(DATA / "input.csv")[6].price == 0.0


def test_whitespace_is_normalized(write_csv):
    path = write_csv(f"{HEADER}\n 8 ,  Коваль   Оксана ,Планшет , 2026-01-01 ,2026-01-02, 10 \n")
    record = load_records(path)[0]
    assert record.ticket == 8
    assert record.client == "Коваль Оксана"
    assert record.device == "Планшет"
    assert record.price == 10.0


def test_column_order_does_not_matter(write_csv):
    path = write_csv(
        "price,completed,received,device,client,ticket\n100,2026-01-03,2026-01-01,Ноутбук,Іван,5\n"
    )
    record = load_records(path)[0]
    assert (record.ticket, record.days, record.price) == (5, 2, 100.0)


def test_crlf_line_endings(write_csv):
    path = write_csv(
        f"{HEADER}\r\n1,А,Б,2026-01-01,2026-01-02,1\r\n2,В,Г,2026-01-01,2026-01-03,2\r\n"
    )
    assert [r.days for r in load_records(path)] == [1, 2]


def test_multiline_quoted_field(write_csv):
    path = write_csv(f'{HEADER}\n1,"Бондар\nМарія",Ноутбук,2026-01-01,2026-01-02,1\n')
    assert load_records(path)[0].client == "Бондар Марія"


def test_header_only_is_empty_input():
    assert load_records(DATA / "empty.csv") == []


def test_zero_byte_file_is_rejected(write_csv):
    with pytest.raises(DataError, match="немає рядка заголовка"):
        load_records(write_csv(""))


def test_missing_column(write_csv):
    path = write_csv("ticket,client,device,received,completed\n1,А,Б,2026-01-01,2026-01-02\n")
    with pytest.raises(DataError, match="У заголовку немає стовпців: price"):
        load_records(path)


def test_missing_value_in_row(write_csv):
    path = write_csv(f"{HEADER}\n1,А,Б,2026-01-01,2026-01-02,1\n2,А,Б,2026-01-01,,1\n")
    with pytest.raises(DataError, match="Рядок 3: немає значення поля completed"):
        load_records(path)


def test_short_row(write_csv):
    path = write_csv(f"{HEADER}\n1,А,Б\n")
    with pytest.raises(DataError, match="Рядок 2: немає значення поля received"):
        load_records(path)


def test_unquoted_comma_gives_too_many_values(write_csv):
    path = write_csv(f"{HEADER}\n1,Іваненко, Петро,Ноутбук,2026-01-01,2026-01-02,1\n")
    with pytest.raises(DataError, match="Рядок 2: забагато значень"):
        load_records(path)


def test_broken_number_keeps_cause():
    with pytest.raises(DataError, match="Рядок 3: поле price має бути числом") as info:
        load_records(DATA / "broken.csv")
    assert isinstance(info.value.__cause__, ValueError)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_price(write_csv, value):
    path = write_csv(f"{HEADER}\n1,А,Б,2026-01-01,2026-01-02,{value}\n")
    with pytest.raises(DataError, match="price"):
        load_records(path)


def test_negative_price(write_csv):
    path = write_csv(f"{HEADER}\n1,А,Б,2026-01-01,2026-01-02,-5\n")
    with pytest.raises(DataError, match="Рядок 2: поле price не може бути від'ємним"):
        load_records(path)


@pytest.mark.parametrize("value", ["abc", "1.5", "0", "-3"])
def test_bad_ticket(write_csv, value):
    path = write_csv(f"{HEADER}\n{value},А,Б,2026-01-01,2026-01-02,1\n")
    with pytest.raises(DataError, match="Рядок 2: поле ticket"):
        load_records(path)


def test_bad_date_keeps_cause(write_csv):
    path = write_csv(f"{HEADER}\n1,А,Б,01.01.2026,2026-01-02,1\n")
    with pytest.raises(DataError, match="Рядок 2: поле received має бути датою") as info:
        load_records(path)
    assert isinstance(info.value.__cause__, ValueError)


@pytest.mark.parametrize("completed", ["2026-01-01", "2025-12-31"])
def test_completed_must_be_after_received(write_csv, completed):
    path = write_csv(f"{HEADER}\n1,А,Б,2026-01-01,{completed},1\n")
    with pytest.raises(DataError, match="completed має бути пізніше"):
        load_records(path)


def test_unclosed_quote_is_reported(write_csv):
    path = write_csv(f'{HEADER}\n1,"А,Б,2026-01-01,2026-01-02,1\n')
    with pytest.raises(DataError):
        load_records(path)


def test_missing_file_keeps_os_error(tmp_path):
    with pytest.raises(DataError, match="Не вдалося прочитати файл") as info:
        load_records(tmp_path / "nope.csv")
    assert isinstance(info.value.__cause__, OSError)


def test_not_utf8_file(write_csv):
    path = write_csv(f"{HEADER}\n1,Іван,Б,2026-01-01,2026-01-02,1\n", encoding="cp1251")
    with pytest.raises(DataError, match="Не вдалося прочитати файл") as info:
        load_records(path)
    assert isinstance(info.value.__cause__, UnicodeDecodeError)


def test_iter_records_is_lazy(write_csv):
    path = write_csv(f"{HEADER}\n1,А,Б,2026-01-01,2026-01-02,1\n2,А,Б,2026-01-01,2026-01-02,x\n")
    records = iter_records(path)
    assert next(records).ticket == 1  # хибний другий рядок ще не прочитано
    with pytest.raises(DataError):
        next(records)


def test_parse_row_directly():
    row = {
        "ticket": "3",
        "client": "Б",
        "device": "В",
        "received": "2026-01-01",
        "completed": "2026-01-11",
        "price": "1.5",
    }
    assert parse_row(row, 9).days == 10
