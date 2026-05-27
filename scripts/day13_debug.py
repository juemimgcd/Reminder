import asyncio

from app.mneme.services.advice_service import build_growth_advice


profile = {
    "knowledge_base_id": "kb_demo_001",
    "entry_count": 8,
        "profile_summary": "Long-term focus on personal growth, knowledge management, and AI backend systems.",
    "main_themes": [
        {
            "theme_name": "鐭ヨ瘑绠＄悊",
            "reason": "澶氭潯鍐呭鍥寸粫闀挎湡娌夋穩鍜屽鐢ㄥ睍寮€",
            "evidence_entries": ["鐭ヨ瘑绠＄悊", "涓汉鎴愰暱璁板綍"],
        }
    ],
    "ability_tags": [
        {
            "ability_name": "FastAPI backend development",
            "reason": "Continuously implementing API and business capabilities",
            "evidence_entries": ["FastAPI backend development"],
        }
    ],
    "expression_style": "鍋忕粨鏋勫寲銆佸鐩樺紡琛ㄨ揪",
        "growth_focus": ["Turn system capabilities into a product loop"],
}

growth_report = {
    "knowledge_base_id": "kb_demo_001",
    "analysis_window": "鏈€杩?30 澶?vs 鏇存棭闃舵",
        "stage_summary": "Recently moved from low-level implementation to productized composition and presentable output.",
        "recent_focus": ["closed-loop output", "growth advice"],
    "theme_changes": [
        {
                "theme_name": "productized output",
            "change_type": "stronger",
            "reason": "鏈€杩戝唴瀹瑰娆″己璋冪粺涓€缁撴灉椤靛拰琛屽姩瀵煎悜",
                "evidence_entries": ["unified output layer", "growth advice"],
        }
    ],
        "highlights": ["Moved from single-feature implementation toward a product loop"],
        "blockers": ["Advice layer is not executable enough"],
        "next_actions": ["Implement advice schema, advice prompt, and advice routing"],
}


async def main():
    result = await build_growth_advice(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        profile=profile,
        growth_report=growth_report,
        focus_goal="浼樺厛鎶婇」鐩仛鎴愭洿瀹屾暣鐨勫彲婕旂ず浜у搧",
    )

    print("advice_summary")
    print(result["advice_summary"])
    print()

    print("current_priorities")
    for item in result["current_priorities"]:
        print(item)
    print()

    print("action_suggestions")
    for item in result["action_suggestions"]:
        print(item)
    print()

    print("one_week_plan")
    for item in result["one_week_plan"]:
        print(item)
    print()

    print("reflection_questions")
    for item in result["reflection_questions"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
