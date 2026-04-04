import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conf.config import settings
from utils.rag_service import generate_rag_answer


async def main():
    question = "我这个文档的主要内容是什么，简要概括"

    print("开始执行 Day 7 调试脚本...", flush=True)
    print(f"question={question}", flush=True)

    if not settings.DASHSCOPE_API_KEY:
        print("未检测到 DASHSCOPE_API_KEY，暂时无法调用千问模型。", flush=True)
        print("先在终端里配置阿里百炼 key，再重新运行这个脚本。", flush=True)
        return

    response = await generate_rag_answer(question, top_k=4)

    answer = response.get("answer")
    sources = response.get("sources", [])

    print("=" * 60, flush=True)
    print("answer:", flush=True)
    print(answer, flush=True)
    print("=" * 60, flush=True)
    print(f"source_count={len(sources)}", flush=True)

    for source in sources[:2]:
        print("-" * 40, flush=True)
        print(
            source.get("document_id"),
            source.get("chunk_id"),
            source.get("page_no"),
            flush=True,
        )
        print(source.get("text", "")[:120], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
