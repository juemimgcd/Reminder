import asyncio
from datetime import datetime

from app.mneme.services.profile_service import build_personal_profile


memory_library = {
    "timeline": [
        {
            "entry_id": "entry_001",
        "entry_name": "FastAPI backend development",
            "entry_type": "ability",
        "summary": "Has FastAPI backend development experience",
            "created_at": datetime(2026, 4, 1, 10, 0, 0),
        },
        {
            "entry_id": "entry_002",
            "entry_name": "涓汉鎴愰暱璁板綍",
            "entry_type": "theme",
            "summary": "闀挎湡鍏虫敞鎴愰暱銆佸鐩樹笌璁板綍",
            "created_at": datetime(2026, 4, 2, 10, 0, 0),
        },
        {
            "entry_id": "entry_003",
            "entry_name": "鐭ヨ瘑绠＄悊",
            "entry_type": "theme",
        "summary": "Wants to turn personal content into reusable long-term memory",
            "created_at": datetime(2026, 4, 3, 10, 0, 0),
        },
    ],
    "by_type": {
        "ability": ["FastAPI backend development"],
        "theme": ["涓汉鎴愰暱璁板綍", "鐭ヨ瘑绠＄悊"],
    },
    "by_theme": [
        {
            "theme_name": "涓汉鎴愰暱璁板綍",
            "entries": ["闀挎湡鍏虫敞鎴愰暱銆佸鐩樹笌璁板綍"],
            "count": 1,
        },
        {
            "theme_name": "鐭ヨ瘑绠＄悊",
        "entries": ["Wants to turn personal content into reusable long-term memory"],
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
