import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from utils.memory_organizer import build_memory_library


def main():
    now = datetime.now()
    entries = [
        {
            "id": "entry_001",
            "entry_name": "FastAPI 后端开发",
            "entry_type": "ability",
            "summary": "有 FastAPI 项目开发经验",
            "created_at": now - timedelta(days=3),
        },
        {
            "id": "entry_002",
            "entry_name": "安徽理工大学",
            "entry_type": "stage",
            "summary": "当前教育阶段与学校背景",
            "created_at": now - timedelta(days=2),
        },
        {
            "id": "entry_003",
            "entry_name": "个人成长记录",
            "entry_type": "theme",
            "summary": "长期关注成长、复盘与记录",
            "created_at": now - timedelta(days=1),
        },
    ]

    library = build_memory_library(entries)

    print("=" * 60)
    print("timeline")
    print(library["timeline"])
    print("=" * 60)
    print("by_type")
    print(library["by_type"])
    print("=" * 60)
    print("by_theme")
    print(library["by_theme"])


if __name__ == "__main__":
    main()
