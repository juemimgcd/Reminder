import asyncio

from utils.companion_builder import build_companion_response


rag_result = {
    "answer": "你现在最值得优先做的，是把知识库级画像、阶段分析和聊天回答整成一个统一输出层。",
    "sources": [
        {
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "page_no": 1,
            "text": "最近持续在做记忆库、画像与阶段分析能力的串联。",
            "knowledge_base_id": "kb_demo_001",
        }
    ],
}

profile = {
    "knowledge_base_id": "kb_demo_001",
    "entry_count": 8,
    "profile_summary": "长期关注个人成长、知识管理和 AI 后端系统构建。",
    "main_themes": [
        {
            "theme_name": "知识管理",
            "reason": "多条词条都围绕记忆沉淀与长期复用展开",
            "evidence_entries": ["知识管理", "个人成长记录"],
        }
    ],
    "ability_tags": [
        {
            "ability_name": "FastAPI 后端开发",
            "reason": "持续围绕接口、鉴权和数据流转进行实现",
            "evidence_entries": ["FastAPI 后端开发"],
        }
    ],
    "expression_style": "偏结构化、复盘式表达",
    "growth_focus": ["把系统能力整成产品闭环"],
}

growth_report = {
    "knowledge_base_id": "kb_demo_001",
    "analysis_window": "最近 30 天 vs 更早阶段",
    "stage_summary": "最近明显从底层能力实现，转向产品化组合输出。",
    "recent_focus": ["陪伴式输出", "统一结果页"],
    "theme_changes": [
        {
            "theme_name": "产品化输出",
            "change_type": "stronger",
            "reason": "最近多条内容都在强调把画像、阶段分析和问答整合起来",
            "evidence_entries": ["统一输出层", "陪伴式回答"],
        }
    ],
    "highlights": ["开始形成产品视角，而不是只停留在接口能力"],
    "blockers": ["结果还没有统一输出结构"],
    "next_actions": ["先做 companion response schema 和路由"],
}


async def main():
    result = await build_companion_response(
        user_id=1,
        knowledge_base_id="kb_demo_001",
        question="我现在最该优先补哪一层？",
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