# Ремонтна майстерня — Python (КЗП, ЛР6–7, варіант 16)

Автор: Нестер А.В., група КІ-303.

Пакет `kzp_lab06` читає CSV із квитанціями ремонтної майстерні, перетворює поля на типізовані
значення, відбирає ремонти, що перебувають у роботі на задану дату, рахує ремонти за типом
пристрою, клієнтів без повторів, завантаження майстерні й найдовший ремонт і записує
детермінований текстовий звіт.

## Формат CSV

UTF-8, заголовок `ticket,client,device,received,completed,price`, порядок стовпців довільний.

| Поле | Після перетворення | Правило |
|------|--------------------|---------|
| ticket | int | більше нуля |
| client | str | непорожнє; зайві пробіли прибираються |
| device | str | тип пристрою, непорожнє |
| received | datetime.date | ISO YYYY-MM-DD |
| completed | datetime.date | ISO, пізніше за received |
| price | float | скінченне, не від'ємне; нуль дозволено (гарантійний ремонт) |

Похідне поле `days = completed − received`. Ремонт «у роботі» на дату `d`, якщо
`received <= d < completed`. Типова дата відбору — `2026-01-03` (`--reference-date`).

## Структура

```text
src/kzp_lab06/
├── __init__.py    # мінімальний публічний API
├── __main__.py    # python -m kzp_lab06
├── errors.py      # DataError
├── loader.py      # csv.DictReader, перетворення полів, генератор iter_records
├── analysis.py    # відбір, словник, множина, завантаження, найдовший ремонт, make_summary
├── reporting.py   # текст звіту і запис файла
└── cli.py         # аргументи та коди завершення
```

## Команди

```text
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate — Linux/macOS
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
ruff format --check .
python -m build
kzp-lab06 data/input.csv out/summary.txt --reference-date 2026-01-03
python tools/measure_memory.py    # ★ список проти генератора, tracemalloc
```

Коди завершення: `0` — звіт записано; `2` — помилка вхідних даних або аргументів
(повідомлення «Помилка даних: …» у stderr, звіт не створюється); `3` — звіт не вдалося записати.

## Приклад звіту

Див. `reports/summary.txt` (для `data/input.csv`, дата 2026-01-03).

## Об'єктна модель (версія 7.0.0, лабораторна робота № 7)

| Клас | Призначення |
|------|-------------|
| `Repair` | базовий клас: `__slots__`, властивості з перевіркою (`ticket`, `client`, `device`, `price`), лише для читання (`received`, `completed`, `days`, `tier`, `sort_key`), `__str__`, `__repr__`, `__eq__` |
| `GadgetRepair` | `total_price() = price × 1.05` (гарантійний збір) |
| `ApplianceRepair` | `total_price() = price + 200 + 20 × days` (виклик майстра і дні ремонту) |
| `create_repair` | фабрика: побутова техніка за типом пристрою → `ApplianceRepair`, інше → `GadgetRepair` |
| `Priced` | `Protocol`: `days`, `tier`, `total_price()` |
| `Workload`, `ReportSummary` | `@dataclass(frozen=True)` |
| `ReportWriter` ★ | контекстний менеджер: тимчасовий файл → `os.replace`, за винятку файл видаляється |

Формат CSV і текст звіту не змінилися (тест `test_equivalence.py` порівнює з копією моделі ЛР6 у
`tests/legacy_v6`). Додаткова опція `--details` друкує ціни з надбавками за рівнями:

```text
kzp-lab06 data/input.csv out/summary.txt --details
python tools/measure_models.py      # пам'ять словників і об'єктів
```
