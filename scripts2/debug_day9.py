import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.context_service import build_query_context


async def main():
    packet = await build_query_context(
        query="请总结这个知识库里关于 FastAPI 后端经验的内容",
        top_k=6,
        user_id=1,
        knowledge_base_id="kb_demo_001",
        context_budget=3000,
    )

    print(f"raw_count={packet['raw_count']}")
    print(f"dedup_count={packet['dedup_count']}")
    print(f"merged_count={packet['merged_count']}")
    print(f"final_count={packet['final_count']}")
    print("=" * 60)
    print(packet["context_text"])
    print("=" * 60)
    for item in packet["sources"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())