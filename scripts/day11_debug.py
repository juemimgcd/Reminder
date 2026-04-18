import asyncio
from datetime import datetime

from services.growth_service import build_growth_report
from services.profile_service import build_personal_profile


memory_library = {
    "timeline": [
        {
            "entry_id": "entry_001",
            "entry_name": "Java 后端开发",
            "entry_type": "ability",
            "summary": "早期主要在 Java 后端方向积累经验",
            "created_at": datetime(2026, 2, 1, 10, 0, 0),
        },
        {
            "entry_id": "entry_002",
            "entry_name": "个人成长记录",
            "entry_type": "theme",
            "summary": "持续进行成长复盘与阶段总结",
            "created_at": datetime(2026, 2, 15, 10, 0, 0),
        },
        {
            "entry_id": "entry_003",
            "entry_name": "FastAPI 后端开发",
            "entry_type": "ability",
            "summary": "最近开始深入使用 FastAPI 构建 AI 后端",
            "created_at": datetime(2026, 3, 25, 10, 0, 0),
        },
        {
            "entry_id": "entry_004",
            "entry_name": "Agentic RAG",
            "entry_type": "theme",
            "summary": "最近持续关注 Agentic RAG 与记忆系统",
            "created_at": datetime(2026, 4, 2, 10, 0, 0),
        },
    ],
    "by_type": {
        "ability": ["Java 后端开发", "FastAPI 后端开发"],
        "theme": ["个人成长记录", "Agentic RAG"],
    },
    "by_theme": [
        {
            "theme_name": "个人成长记录",
            "entries": ["持续进行成长复盘与阶段总结"],
            "count": 1,
        },
        {
            "theme_name": "Agentic RAG",
            "entries": ["最近持续关注 Agentic RAG 与记忆系统"],
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