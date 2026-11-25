"""Обробка CSV ремонтної майстерні (КЗП, варіант 16).

Публічний мінімальний API: завантаження записів, побудова й запис звіту.
"""

from kzp_lab06.analysis import build_report, make_summary
from kzp_lab06.errors import DataError
from kzp_lab06.loader import iter_records, load_records
from kzp_lab06.reporting import format_report, write_report

__version__ = "6.0.0"

__all__ = [
    "DataError",
    "build_report",
    "format_report",
    "iter_records",
    "load_records",
    "make_summary",
    "write_report",
    "__version__",
]
