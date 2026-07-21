import re
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"
_SEMANTIC_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not _SEMANTIC_VERSION.fullmatch(version):
        raise RuntimeError(f"VERSION must contain MAJOR.MINOR.PATCH, got {version!r}")
    return version


__version__ = read_version()

__all__ = ["__version__", "read_version"]
