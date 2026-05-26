import asyncio
from datetime import datetime

from app.mneme.services.growth_service import build_growth_report
from app.mneme.services.profile_service import build_personal_profile


memory_library = {
    "timeline": [
        {
            "entry_id": "entry_001",
        "entry_name": "Java backend development",
            "entry_type": "ability",
            "summary": "鏃╂湡涓昏鍦?Java 鍚庣鏂瑰悜绉疮缁忛獙",
            "created_at": datetime(2026, 2, 1, 10, 0, 0),
        },
        {
            "entry_id": "entry_002",
            "entry_name": "涓汉鎴愰暱璁板綍",
            "entry_type": "theme",
            "summary": "鎸佺画杩涜鎴愰暱澶嶇洏涓庨樁娈垫€荤粨",
            "created_at": datetime(2026, 2, 15, 10, 0, 0),
        },
        {
            "entry_id": "entry_003",
        "entry_name": "FastAPI backend development",
            "entry_type": "ability",
            "summary": "鏈€杩戝紑濮嬫繁鍏ヤ娇鐢?FastAPI 鏋勫缓 AI 鍚庣",
            "created_at": datetime(2026, 3, 25, 10, 0, 0),
        },
        {
            "entry_id": "entry_004",
            "entry_name": "Agentic RAG",
            "entry_type": "theme",
        "summary": "Recently focusing on Agentic RAG and memory systems",
            "created_at": datetime(2026, 4, 2, 10, 0, 0),
        },
    ],
    "by_type": {
        "ability": ["Java backend development", "FastAPI backend development"],
        "theme": ["涓汉鎴愰暱璁板綍", "Agentic RAG"],
    },
    "by_theme": [
        {
            "theme_name": "涓汉鎴愰暱璁板綍",
            "entries": ["鎸佺画杩涜鎴愰暱澶嶇洏涓庨樁娈垫€荤粨"],
            "count": 1,
        },
        {
            "theme_name": "Agentic RAG",
        "entries": ["Recently focusing on Agentic RAG and memory systems"],
            "count": 1,
        },
    ],
}


async def main():
    profile = await build_personal_profile(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        memory_library=memory_library,
    )
    report = await build_growth_report(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        memory_library=memory_library,
        profile=profile,
        recent_days=30,
    )

    print("analysis_window")
    print(report["analysis_window"])
    print()

    print("stage_summary")
    print(report["stage_summary"])
    print()

    print("theme_changes")
    for item in report["theme_changes"]:
        print(item)
    print()

    print("highlights")
    for item in report["highlights"]:
        print(item)
    print()

    print("next_actions")
    for item in report["next_actions"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
