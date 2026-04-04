import asyncio
import sys
from pathlib import Path

from langchain_core.documents import Document as LCDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from utils.entry_extractor import extract_entries_from_chunk


async def main():
    doc = LCDocument(
        page_content=(
            "我在安徽理工大学学习计算机相关课程，"
            "曾使用 FastAPI、JWT、Docker 完成一个后端项目，"
            "最近对后端架构和个人成长记录非常感兴趣。"
        ),
        metadata={
            "document_id": "doc_demo_001",
            "chunk_id": "chunk_demo_001",
            "page_no": 1,
        },
    )

    entries = await extract_entries_from_chunk(doc)

    print(f"entry_count={len(entries)}")
    for item in entries:
        print("=" * 60)
        print(item["entry_name"])
        print(item["entry_type"])
        print(item["summary"])
        print(item["evidence_text"])


if __name__ == "__main__":
    asyncio.run(main())
