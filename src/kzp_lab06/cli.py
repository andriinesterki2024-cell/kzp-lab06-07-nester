"""Командний рядок: ``kzp-lab06 INPUT OUTPUT [--details]``.

Коди завершення: 0 — звіт записано; 2 — помилка вхідних даних або аргументів;
3 — звіт не вдалося записати.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kzp_lab06 import __version__
from kzp_lab06.analysis import build_report
from kzp_lab06.errors import DataError
from kzp_lab06.loader import load_records
from kzp_lab06.reporting import format_details, format_report, write_report

EXIT_OK = 0
EXIT_DATA = 2
EXIT_WRITE = 3


def build_parser() -> argparse.ArgumentParser:
    """Створює розбирач аргументів."""
    parser = argparse.ArgumentParser(
        prog="kzp-lab06", description="Звіт ремонтної майстерні з CSV (варіант 16)."
    )
    parser.add_argument("input", type=Path, help="вхідний CSV-файл")
    parser.add_argument("output", type=Path, help="файл звіту")
    parser.add_argument(
        "--details",
        action="store_true",
        help="надрукувати підсумок за несправностями й остаточну вартість",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _print(message: str, stream) -> None:
    """Друкує повідомлення в UTF-8 (консоль Windows може мати інше кодування)."""
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
    print(message, file=stream)


def _error(message: str) -> None:
    """Повідомлення про помилку в stderr без traceback."""
    _print(message, sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Точка входу CLI; повертає код завершення."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as stop:  # argparse завершує роботу сам (--help, --version, помилка)
        return int(stop.code or 0) if stop.code in (0, None) else EXIT_DATA
    if args.input.resolve() == args.output.resolve():
        _error("Помилка даних: вхідний і вихідний файли збігаються")
        return EXIT_DATA
    try:
        records = load_records(args.input)
    except DataError as error:
        _error(f"Помилка даних: {error}")
        return EXIT_DATA
    text = format_report(build_report(records))
    try:
        write_report(args.output, text)
    except OSError as error:
        _error(f"Помилка запису звіту: {args.output} ({error.strerror or error})")
        return EXIT_WRITE
    _print(f"Звіт записано: {args.output} (заявок: {len(records)})", sys.stdout)
    if args.details:
        _print(format_details(records).rstrip(), sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
