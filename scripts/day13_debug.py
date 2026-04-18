import asyncio

from services.advice_service import build_growth_advice


profile = {
    "knowledge_base_id": "kb_demo_001",
    "entry_count": 8,
    "profile_summary": "长期关注个人成长、知识管理和 AI 后端系统构建。",
    "main_themes": [
        {
            "theme_name": "知识管理",
            "reason": "多条内容围绕长期沉淀和复用展开",
            "evidence_entries": ["知识管理", "个人成长记录"],
        }
    ],
    "ability_tags": [
        {
            "ability_name": "FastAPI 后端开发",
            "reason": "持续在做接口和业务能力实现",
            "evidence_entries": ["FastAPI 后端开发"],
        }
    ],
    "expression_style": "偏结构化、复盘式表达",
    "growth_focus": ["把系统能力沉淀成产品闭环"],
}

growth_report = {
    "knowledge_base_id": "kb_demo_001",
    "analysis_window": "最近 30 天 vs 更早阶段",
    "stage_summary": "最近明显从底层实现，转向产品化组合与可展示输出。",
    "recent_focus": ["陪伴式输出", "成长建议"],
    "theme_changes": [
        {
            "theme_name": "产品化输出",
            "change_type": "stronger",
            "reason": "最近内容多次强调统一结果页和行动导向",
            "evidence_entries": ["统一输出层", "成长建议"],
        }
    ],
    "highlights": ["已经从单功能实现开始转向完整产品闭环"],
    "blockers": ["建议层还不够可执行"],
    "next_actions": ["做建议 schema、建议 prompt 和建议路由"],
}


async def main():
    result = await build_growth_advice(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        profile=profile,
        growth_report=growth_report,
        focus_goal="优先把项目做成更完整的可演示产品",
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