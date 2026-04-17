import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from services.context_service import retrieve_documents_with_scores


async def main():
    query = "Agentic RAG 私有知识助手的核心目标是什么？"
    results = await retrieve_documents_with_scores(query, top_k=4)

    print(f"query={query}")
    print(f"result_count={len(results)}")

    for index, (doc, score) in enumerate(results, start=1):
        print("=" * 60)
        print(f"rank={index}")
        print(f"score={score}")
        print(f"metadata={doc.metadata}")
        print(f"content_preview={doc.page_content[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
