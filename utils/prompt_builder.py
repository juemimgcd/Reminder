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












