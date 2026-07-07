from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [
    ROOT / "app" / "mneme",
    ROOT / "alembic",
]
SOURCE_FILES = [ROOT / "main.py"]

MOJIBAKE_FRAGMENTS = [
    "\ufffd",
    "\u951f",
    "\u95bf",
    "\u9435",
    "\u6d93",
    "\u6d60",
    "\u6d63",
    "\u677c",
    "\u6753",
    "\u934f",
    "\u9352",
    "\u93c2",
    "\u7d31",
    "\u7f02",
    "\u95c1",
    "\u95bb",
    "\u942e",
    "\u941e",
    "\u6d34",
    "\u6d93\u20ac",
    "\u6d63\u7280",
    "\u7487",
    "\u95b0",
    "\u699b",
    "\u9477",
    "\u9359",
    "\u5e47",
    "\u6fb6",
    "\u74d2",
    "\u6b35",
    "\u7a0b",
    "\u95c6",
    "\u95c3",
]
MOJIBAKE_PATTERN = re.compile("|".join(re.escape(fragment) for fragment in MOJIBAKE_FRAGMENTS))


def iter_source_files():
    for root in SOURCE_ROOTS:
        yield from root.rglob("*.py")
    yield from SOURCE_FILES


def test_python_sources_do_not_contain_common_chinese_mojibake():
    offenders: list[str] = []

    for path in iter_source_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if MOJIBAKE_PATTERN.search(line):
                relative = path.relative_to(ROOT).as_posix()
                offenders.append(f"{relative}:{line_number}: {line.strip()}")

    assert offenders == []
