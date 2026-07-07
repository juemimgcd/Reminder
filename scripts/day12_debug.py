import asyncio

from app.mneme.domains.companion.service import build_companion_response


rag_result = {
        "answer": "Use one unified output layer for profile, stage analysis, and chat answers.",
    "sources": [
        {
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "page_no": 1,
            "text": "Recently working on memory library, profile, and stage analysis capabilities.",
            "knowledge_base_id": "kb_demo_001",
        }
    ],
}

profile = {
    "knowledge_base_id": "kb_demo_001",
    "entry_count": 8,
        "profile_summary": "Long-term focus on personal growth, knowledge management, and AI backend systems",
    "main_themes": [
        {
            "theme_name": "鐭ヨ瘑绠＄悊",
            "reason": "澶氭潯璇嶆潯閮藉洿缁曡蹇嗘矇娣€涓庨暱鏈熷鐢ㄥ睍寮€",
            "evidence_entries": ["鐭ヨ瘑绠＄悊", "涓汉鎴愰暱璁板綍"],
        }
    ],
    "ability_tags": [
        {
            "ability_name": "FastAPI backend development",
            "reason": "鎸佺画鍥寸粫鎺ュ彛銆侀壌鏉冨拰鏁版嵁娴佽浆杩涜瀹炵幇",
            "evidence_entries": ["FastAPI backend development"],
        }
    ],
    "expression_style": "鍋忕粨鏋勫寲銆佸鐩樺紡琛ㄨ揪",
        "growth_focus": ["Turn system capabilities into a product loop"],
}

growth_report = {
    "knowledge_base_id": "kb_demo_001",
    "analysis_window": "鏈€杩?30 澶?vs 鏇存棭闃舵",
        "stage_summary": "Recently moved from low-level capability work to productized output.",
        "recent_focus": ["stage output", "unified result page"],
    "theme_changes": [
        {
                "theme_name": "productized output",
            "change_type": "stronger",
            "reason": "鏈€杩戝鏉″唴瀹归兘鍦ㄥ己璋冩妸鐢诲儚銆侀樁娈靛垎鏋愬拰闂瓟鏁村悎璧锋潵",
                "evidence_entries": ["unified output layer", "stage answer"],
        }
    ],
        "highlights": ["Started forming a product perspective instead of only API capability work"],
    "blockers": ["缁撴灉杩樻病鏈夌粺涓€杈撳嚭缁撴瀯"],
        "next_actions": ["Implement companion response schema and routing"],
}


async def main():
    result = await build_companion_response(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        question="鎴戠幇鍦ㄦ渶璇ヤ紭鍏堣ˉ鍝竴灞傦紵",
        rag_result=rag_result,
        profile=profile,
        growth_report=growth_report,
    )

    print("direct_answer")
    print(result["direct_answer"])
    print()

    print("profile_snapshot")
    print(result["profile_snapshot"])
    print()

    print("growth_snapshot")
    print(result["growth_snapshot"])
    print()

    print("next_step_hint")
    print(result["next_step_hint"])
    print()

    print("follow_up_questions")
    for item in result["follow_up_questions"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
