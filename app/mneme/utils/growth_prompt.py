from langchain_core.prompts import ChatPromptTemplate


def get_growth_report_prompt(format_instructions: str) -> ChatPromptTemplate:
    # 你要做的事：
    # 1. 用 ChatPromptTemplate.from_messages(...)
    # 2. 准备一个 system 消息
    # 3. 明确告诉模型：输入包含长期画像、较早阶段、最近阶段
    # 4. 明确告诉模型：重点看变化，不要只做重复总结
    # 5. 明确告诉模型：不能编造经历，不能下过重结论
    # 6. 在 human 消息里至少包含 user_id、knowledge_base_id、growth_input_text
    # 7. 把 format_instructions 拼进去，约束输出结构
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个个人成长阶段分析助手。"
                "你会基于长期画像、较早阶段内容和最近阶段内容，提炼主题变化、亮点、卡点和下一步建议。"
                "你只能基于输入内容做判断，不能编造经历，不能给出过度绝对的结论。"
                "输出必须严格遵守格式要求。"

            ),

            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "growth_input_text=\n{growth_input_text}\n\n"
                "{format_instructions}"
            )




        ]
    ).partial(format_instructions=format_instructions)










