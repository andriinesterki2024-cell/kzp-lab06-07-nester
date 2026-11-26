"""Пам'ять словникової (ЛР6) та об'єктної (ЛР7) моделей на великому CSV.

Запуск: ``python tools/measure_models.py [кількість_рядків]`` (типово 200 000).
Словникова модель береться з tests/legacy_v6.
"""

from __future__ import annotations

import sys
import tempfile
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

from legacy_v6 import analysis as old_analysis  # noqa: E402
from legacy_v6 import loader as old_loader  # noqa: E402
from legacy_v6 import reporting as old_reporting  # noqa: E402
from measure_memory import make_csv  # noqa: E402

from kzp_lab06.analysis import build_report  # noqa: E402
from kzp_lab06.loader import load_records  # noqa: E402
from kzp_lab06.reporting import format_report  # noqa: E402


def peak(func):
    """Повертає (результат, пікову пам'ять у МіБ) для функції."""
    tracemalloc.start()
    result = func()
    _, top = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, top / 2**20


def main() -> None:
    """Точка входу скрипта."""
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "big.csv"
        make_csv(path, rows)
        old, old_mib = peak(lambda: old_loader.load_records(path))
        new, new_mib = peak(lambda: load_records(path))
        same = old_reporting.format_report(old_analysis.build_report(old)) == format_report(
            build_report(new)
        )
    print(f"Рядків у CSV: {rows}")
    print(f"Словники (ЛР6):        {old_mib:8.2f} МіБ")
    print(f"Об'єкти __slots__ (ЛР7): {new_mib:8.2f} МіБ")
    print(f"Звіти однакові: {same}")
    print(f"Об'єкти займають у {old_mib / new_mib:.1f} раза менше пам'яті")


if __name__ == "__main__":
    main()
