import asyncio
from datetime import datetime

from services.profile_service import build_personal_profile


memory_library = {
    "timeline": [
        {
            "entry_id": "entry_001",
            "entry_name": "FastAPI 后端开发",
            "entry_type": "ability",
            "summary": "有 FastAPI 后端开发经验",
            "created_at": datetime(2026, 4, 1, 10, 0, 0),
        },
        {
            "entry_id": "entry_002",
            "entry_name": "个人成长记录",
            "entry_type": "theme",
            "summary": "长期关注成长、复盘与记录",
            "created_at": datetime(2026, 4, 2, 10, 0, 0),
        },
        {
            "entry_id": "entry_003",
            "entry_name": "知识管理",
            "entry_type": "theme",
            "summary": "希望把个人内容沉淀为长期可用的记忆库",
            "created_at": datetime(2026, 4, 3, 10, 0, 0),
        },
    ],
    "by_type": {
        "ability": ["FastAPI 后端开发"],
        "theme": ["个人成长记录", "知识管理"],
    },
    "by_theme": [
        {
            "theme_name": "个人成长记录",
            "entries": ["长期关注成长、复盘与记录"],
            "count": 1,
        },
        {
            "theme_name": "知识管理",
            "entries": ["希望把个人内容沉淀为长期可用的记忆库"],
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

    print("profile_summary")
    print(profile["profile_summary"])
    print()

    print("main_themes")
    for item in profile["main_themes"]:
        print(item)
    print()

    print("ability_tags")
    for item in profile["ability_tags"]:
        print(item)
    print()

    print("growth_focus")
    print(profile["growth_focus"])


if __name__ == "__main__":
    asyncio.run(main())