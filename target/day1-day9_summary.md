file_loader 负责把文件变成 Document
text_splitter 负责把 Document 变成 chunk
vector_store + embeddings 负责把 chunk 变成可检索向量
retriever 负责把问题变成相关 chunk
prompt_builder + llm 负责把 chunk 变成最终答案
index_service / rag_service 则分别负责把这些底层能力串成“建索引”和“问答”两条完整业务链
