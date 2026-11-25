"""Спільні фікстури тестів."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEADER = "ticket,client,device,received,completed,price"


@pytest.fixture
def write_csv(tmp_path: Path):
    """Записує CSV у тимчасовий файл і повертає шлях."""

    def _write(text: str, name: str = "input.csv", encoding: str = "utf-8") -> Path:
        path = tmp_path / name
        path.write_bytes(text.encode(encoding))
        return path

    return _write
