import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from services.query_router_service import route_query


def main():
    questions = [
        "你好，你能做什么？",
        "这篇文档的主要内容是什么？",
        "我之前提到过哪些 FastAPI 项目经验？",
        "根据这些记忆，帮我总结一下我的画像",
        "最近 30 天我的成长卡点是什么？",
        "帮我删除这个知识库里的旧文档",
    ]

    print("开始执行 Day 7 Query Router 调试脚本...", flush=True)
    for question in questions:
        decision = route_query(question)
        print("=" * 60, flush=True)
        print(f"question={question}", flush=True)
        print(f"query_type={decision.query_type}", flush=True)
        print(f"requires_retrieval={decision.requires_retrieval}", flush=True)
        print(f"target_pipeline={decision.target_pipeline}", flush=True)
        print(f"confidence={decision.confidence}", flush=True)
        print(f"reason={decision.reason}", flush=True)


if __name__ == "__main__":
    main()
