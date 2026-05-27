from langchain_core.prompts import ChatPromptTemplate


# ```python
# from langchain_core.prompts import ChatPromptTemplate
#
# template = ChatPromptTemplate(
#     [
#         ("system", "You are a helpful AI bot. Your name is {name}."),
#         ("human", "Hello, how are you doing?"),
#         ("ai", "I'm doing well, thanks!"),
#         ("human", "{user_input}"),
#     ]
# )
#
# prompt_value = template.invoke(
#     {
#         "name": "Bob",
#         "user_input": "What is your name?",
#     }
# )
# # Output:
# # ChatPromptValue(
# #    messages=[
# #        SystemMessage(content='You are a helpful AI bot. Your name is Bob.'),
# #        HumanMessage(content='Hello, how are you doing?'),
# #        AIMessage(content="I'm doing well, thanks!"),
# #        HumanMessage(content='What is your name?')
# #    ]
# # )
# ```



def get_evidence_rag_prompt(format_instructions: str):
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个基于知识库证据回答问题的助手。"
                "你必须只依据给定 context 回答。"
                "每条 citation 只能引用 context 中提供的 source_id。"
                "如果证据不足，请在 uncertainty 中明确说明。"
                f"请严格按下面格式输出：\n{format_instructions}",
            ),
            (
                "human",
                "已检索内容如下：\n{context}\n\n用户问题：\n{question}",
            ),
        ]
    )


def get_general_chat_prompt() -> ChatPromptTemplate:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是 Mneme 的通用智能助手。"
                "当用户的问题与其已上传资料无关时，直接基于通用能力回答，不需要引用知识库。"
                "请简洁、明确、自然地回答。"
                "如果用户询问你是谁、你能做什么、如何使用系统，优先介绍你的定位、能力边界和可提供的帮助。"
                "不要假装看过用户未上传的资料，也不要虚构其知识库内容。",
            ),
            (
                "human",
                "{question}",
            ),
        ]
    )

    return prompt












