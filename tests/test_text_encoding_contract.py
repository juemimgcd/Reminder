from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [
    ROOT / "app" / "mneme",
    ROOT / "alembic",
]
SOURCE_FILES = [
    ROOT / "main.py",
    ROOT / "README.md",
]

MOJIBAKE_FRAGMENTS = [
    "\ufffd",
    "\u951f",
    "\u920e",
    "\u9241",
    "\u9242",
    "\u95b3",
    "\u6d93\u20ac",
    "\u6d63\u7280",
    "\u95c1\u95c2",
    "\u942e\u95b4",
]
MOJIBAKE_PATTERN = re.compile(
    "|".join(re.escape(fragment) for fragment in MOJIBAKE_FRAGMENTS)
    + r"|[\ue000-\uf8ff]"
)


def iter_text_files():
    for root in SOURCE_ROOTS:
        yield from root.rglob("*.py")
    yield from SOURCE_FILES


def test_text_sources_do_not_contain_common_chinese_mojibake():
    offenders: list[str] = []

    for path in iter_text_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if MOJIBAKE_PATTERN.search(line):
                relative = path.relative_to(ROOT).as_posix()
                offenders.append(f"{relative}:{line_number}: {line.strip()}")

    assert offenders == []


def test_readme_does_not_contain_empty_fenced_code_blocks():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    empty_fence_pattern = re.compile(r"```[^\n]*\n\s*```")

    assert empty_fence_pattern.search(readme) is None
