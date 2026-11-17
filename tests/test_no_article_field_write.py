"""Fail if any module writes the problem field that walks every incident."""

from __future__ import annotations

import re
from pathlib import Path

FIELD = "primary_known_error_article"
_WRITE = re.compile(rf"""['\"]{FIELD}['\"]\s*:""")
_ASSIGN = re.compile(rf"""(?<![A-Za-z0-9_]){FIELD}\s*=""")


def test_no_module_writes_the_forbidden_article_field() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts or path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if _WRITE.search(text) or _ASSIGN.search(text):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
