from pydantic import BaseModel, Field


class Neo4jHealthData(BaseModel):
    enabled: bool = Field(..., description="是否启用 Neo4j 图投影")
    backend: str = Field(..., description="当前图后端配置")
    database: str = Field(..., description="Neo4j database 名称")
    uri: str = Field(..., description="Neo4j 连接地址")
    ok: bool = Field(..., description="是否连接成功")
    error: str | None = Field(default=None, description="错误信息")


class GraphProjectionRebuildData(BaseModel):
    scope: str = Field(..., description="回填范围: user / knowledge_base")
    user_id: int = Field(..., description="当前用户 ID")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID")
    knowledge_base_count: int | None = Field(default=None, description="回填的知识库数量")
    document_count: int = Field(..., description="回填的文档数量")
    memory_entry_count: int = Field(..., description="回填的 memory entry 数量")
    status: str = Field(..., description="回填状态")
