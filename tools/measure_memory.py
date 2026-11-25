"""Порівняння пам'яті та часу: список (load_records) проти генератора (iter_records).

Запуск: ``python tools/measure_memory.py [кількість_рядків]`` (типово 200 000).
Створює тимчасовий CSV, рахує ті самі показники двома способами й друкує пікову пам'ять
за ``tracemalloc``. tracemalloc враховує лише об'єкти Python і сповільнює виконання,
тому час орієнтовний.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import time
import tracemalloc
from datetime import date, timedelta
from pathlib import Path

from kzp_lab06.analysis import build_report, stream_summary
from kzp_lab06.loader import iter_records, load_records

REF = date(2026, 1, 3)
DEVICES = ("Ноутбук", "Смартфон", "Планшет", "Пральна машина", "Холодильник")


def make_csv(path: Path, rows: int) -> None:
    """Створює CSV із ``rows`` синтетичними ремонтами."""
    start = date(2025, 1, 1)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["ticket", "client", "device", "received", "completed", "price"])
        for i in range(1, rows + 1):
            received = start + timedelta(days=i % 400)
            completed = received + timedelta(days=1 + i % 14)
            client = f"Клієнт {i % 5000}"
            writer.writerow([i, client, DEVICES[i % 5], received, completed, f"{100 + i % 900}.00"])


def measure(label: str, func):
    """Виконує функцію під tracemalloc і повертає (результат, піку МіБ, секунди)."""
    tracemalloc.start()
    began = time.perf_counter()
    result = func()
    seconds = time.perf_counter() - began
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"{label:<28} пік {peak / 2**20:8.2f} МіБ   час {seconds:6.2f} с")
    return result, peak


def main() -> None:
    """Точка входу скрипта."""
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "big.csv"
        make_csv(path, rows)
        print(f"Рядків у CSV: {rows}")
        full, peak_list = measure(
            "список (load_records)", lambda: build_report(load_records(path), REF)
        )
        streamed, peak_gen = measure(
            "генератор (iter_records)", lambda: stream_summary(iter_records(path), REF)
        )
    same = (
        full["count"] == streamed["count"]
        and len(full["in_work"]) == streamed["in_work"]
        and len(full["clients"]) == streamed["clients"]
        and full["total_days"] == streamed["total_days"]
        and abs(full["total_price"] - streamed["total_price"]) < 1e-6
        and full["longest"]["ticket"] == streamed["longest_ticket"]
    )
    print(f"Результати однакові: {same}")
    print(f"Генератор зменшив пікову пам'ять у {peak_list / peak_gen:.1f} разів")


if __name__ == "__main__":
    main()
