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



def get_rag_prompt() -> ChatPromptTemplate:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个基于知识库回答问题的助手。"
                "请优先依据提供的 context 回答。"
                "如果 context 里没有足够信息，请明确说“我无法从已检索内容中确定答案”，不要编造。",
            ),
            (
                "human",
                "已检索内容如下：\n{context}\n\n用户问题：\n{question}",
            ),
        ]
    )

    return prompt


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












