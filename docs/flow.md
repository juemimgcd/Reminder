# Agentic RAG 数据流

```mermaid
flowchart TD
    A[上传文件] --> B[保存原始文件]
    B --> C[写入 documents 表]
    C --> D[解析文件]
    D --> E[切分 chunks]
    E --> F[向量化]
    F --> G[写入向量库]
    H[用户提问] --> I[Retriever 检索]
    I --> J[拼接上下文]
    J --> K[LLM 生成答案]
    K --> L[返回 answer 和 sources]