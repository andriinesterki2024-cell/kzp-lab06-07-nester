# Ремонтна майстерня — Python (КЗП, ЛР6–7, варіант 16)

Автор: Нестер А.В., група КІ-303.

Пакет `kzp_lab06` читає CSV із заявками ремонтної майстерні, перетворює поля на типізовані значення
й записує детермінований текстовий звіт. Обчислення взято з таблиці варіантів ЛР6 (варіант 16):

| Що | Варіант 16 |
|----|------------|
| Поля CSV | `customer,device,fault,date,cost,status` |
| Відбір (список) | `status != "done"` — відкриті заявки |
| Словник | сума вартості (`cost`) за несправністю (`fault`) |
| Множина | пристрої (`device`) |
| Звіт | відкриті заявки й найдорожчий ремонт |

## Формат CSV

UTF-8, заголовок `customer,device,fault,date,cost,status`, порядок стовпців довільний.

| Поле | Після перетворення | Правило |
|------|--------------------|---------|
| customer | str | непорожнє; зайві пробіли прибираються |
| device | str | непорожнє |
| fault | str | непорожнє |
| date | datetime.date | ISO YYYY-MM-DD |
| cost | float | скінченне, не від'ємне; нуль дозволено |
| status | str | `new`, `in_progress` або `done` (регістр нормалізується) |

Порогу (threshold) і дати відбору (reference_date) варіант не використовує: відбір задано станом заявки.

## Структура

```text
src/kzp_lab06/
├── __init__.py    # мінімальний публічний API
├── __main__.py    # python -m kzp_lab06
├── errors.py      # DataError
├── loader.py      # csv.DictReader, перетворення полів, генератор iter_records
├── analysis.py    # відбір, словник, множина, найдорожчий ремонт, make_summary, stream_summary
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
kzp-lab06 data/input.csv out/summary.txt
python tools/measure_memory.py    # ★ список проти генератора, tracemalloc
```

Коди завершення: `0` — звіт записано; `2` — помилка вхідних даних або аргументів
(повідомлення «Помилка даних: …» у stderr, звіт не створюється); `3` — звіт не вдалося записати.

## Приклад звіту

Див. `reports/summary.txt` (для `data/input.csv`). `data/all-done.csv` — набір, де всі заявки виконані
(порожній відбір), `data/empty.csv` — лише заголовок, `data/broken.csv` — хибне число в рядку 3.
