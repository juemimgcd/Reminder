import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.domains.retrieval.query_router import route_query


def main():
    questions = [
        "浣犲ソ锛屼綘鑳藉仛浠€涔堬紵",
        "杩欑瘒鏂囨。鐨勪富瑕佸唴瀹规槸浠€涔堬紵",
        "What FastAPI project experience did I mention before?",
        "Summarize my profile from these memories.",
        "鏈€杩?30 澶╂垜鐨勬垚闀垮崱鐐规槸浠€涔堬紵",
        "甯垜鍒犻櫎杩欎釜鐭ヨ瘑搴撻噷鐨勬棫鏂囨。",
    ]

    print("寮€濮嬫墽琛?Day 7 Query Router 璋冭瘯鑴氭湰...", flush=True)
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
