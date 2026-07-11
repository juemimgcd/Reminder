from langchain_core.prompts import ChatPromptTemplate


def get_growth_report_prompt(format_instructions: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个个人成长阶段分析助手。"
                "你会基于长期画像、较早阶段内容和最近阶段内容，"
                "提炼主题变化、亮点、卡点和下一步建议。"
                "你只能基于输入内容做判断，不能编造经历，不能给出过度绝对的结论。"
                "输出必须严格遵守格式要求。",
            ),
            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "growth_input_text=\n{growth_input_text}\n\n"
                "{format_instructions}",
            ),
        ]
    ).partial(format_instructions=format_instructions)
