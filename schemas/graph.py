from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GraphNodeData(BaseModel):
    id: str = Field(..., description="图节点 ID")
    entity_id: str = Field(..., description="业务实体 ID")
    node_type: str = Field(
        ...,
        description="节点类型: user / knowledge_base / document / memory_entry",
    )
    label: str = Field(..., description="节点显示名称")
    parent_id: str | None = Field(default=None, description="父节点 ID")
    depth: int = Field(..., description="树层级，从 0 开始")
    metadata: dict[str, Any] = Field(default_factory=dict, description="前端可直接使用的扩展信息")


class GraphEdgeData(BaseModel):
    id: str = Field(..., description="图边 ID")
    source: str = Field(..., description="起点节点 ID")
    target: str = Field(..., description="终点节点 ID")
    edge_type: str = Field(..., description="边类型: owns / contains / extracts / related")
    metadata: dict[str, Any] = Field(default_factory=dict, description="前端可直接使用的扩展信息")


class GraphData(BaseModel):
    scope: str = Field(..., description="图范围: user / knowledge_base / document")
    generated_at: datetime = Field(..., description="生成时间")
    root_node_id: str = Field(..., description="根节点 ID")
    include_memory: bool = Field(default=False, description="是否包含 memory_entry 节点")
    include_relationships: bool = Field(default=False, description="是否包含文档关联边")
    relationship_strategy: str | None = Field(default=None, description="文档关联边生成策略")
    relationship_scope: str | None = Field(default=None, description="文档关联边搜索范围")
    min_shared_memory_count: int | None = Field(default=None, description="保留关系边所需的最小共享 memory 数")
    min_relationship_score: float | None = Field(default=None, description="保留关系边所需的最小关联分数")
    max_related_edges: int | None = Field(default=None, description="返回的最大关联边数量")
    nodes: list[GraphNodeData] = Field(default_factory=list)
    edges: list[GraphEdgeData] = Field(default_factory=list)
    node_count: int = Field(..., description="节点总数")
    edge_count: int = Field(..., description="边总数")
    node_type_counts: dict[str, int] = Field(default_factory=dict, description="按节点类型统计数量")
    edge_type_counts: dict[str, int] = Field(default_factory=dict, description="按边类型统计数量")
