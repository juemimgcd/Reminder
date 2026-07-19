from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.mneme.clients.neo4j_client import fetch_neo4j_records, should_use_neo4j_graph_backend
from app.mneme.conf.logging import app_logger
from app.mneme.domains.graph.service import (
    _build_graph_type_counts,
    build_document_node,
    build_edge,
    build_knowledge_base_node,
    build_memory_node,
    build_user_node,
)


def _parse_datetime(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value


def _hydrate_record(payload: dict[str, Any]) -> SimpleNamespace:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized[key] = _parse_datetime(value)
    return SimpleNamespace(**normalized)


def _build_related_edge(
        *,
        source_document_id: str,
        target_document_id: str,
        metadata: dict[str, Any],
) -> dict[str, Any]:
    return build_edge(
        source=f"document:{source_document_id}",
        target=f"document:{target_document_id}",
        edge_type="related",
        metadata=metadata,
    )


def _filter_related_edges(
        *,
        edges: list[dict[str, Any]],
        min_shared_memory_count: int,
        min_relationship_score: float,
        max_related_edges: int | None,
) -> list[dict[str, Any]]:
    filtered = [
        edge
        for edge in edges
        if edge["metadata"].get("shared_memory_count", 0) >= min_shared_memory_count
        and edge["metadata"].get("relationship_score", 0.0) >= min_relationship_score
    ]
    if max_related_edges is not None:
        return filtered[:max_related_edges]
    return filtered


async def _fetch_user_graph_records(*, user_id: int) -> dict[str, list[SimpleNamespace] | SimpleNamespace | None]:
    user_rows = await fetch_neo4j_records(
        """
        MATCH (u:User {id: $user_id})
        RETURN properties(u) AS user
        """,
        {"user_id": user_id},
    )
    if not user_rows:
        return {"user": None, "knowledge_bases": [], "documents": [], "memory_entries": []}

    knowledge_base_rows = await fetch_neo4j_records(
        """
        MATCH (:User {id: $user_id})-[:OWNS]->(kb:KnowledgeBase)
        RETURN properties(kb) AS knowledge_base
        ORDER BY kb.created_at ASC, kb.id ASC
        """,
        {"user_id": user_id},
    )
    document_rows = await fetch_neo4j_records(
        """
        MATCH (:User {id: $user_id})-[:OWNS]->(:KnowledgeBase)-[:CONTAINS]->(d:Document)
        RETURN properties(d) AS document
        ORDER BY d.created_at ASC, d.id ASC
        """,
        {"user_id": user_id},
    )
    memory_rows = await fetch_neo4j_records(
        """
        MATCH (:User {id: $user_id})-[:OWNS]->(:KnowledgeBase)-[:CONTAINS]->(:Document)-[:EXTRACTS]->(m:MemoryEntry)
        RETURN properties(m) AS memory_entry
        ORDER BY m.created_at ASC, m.id ASC
        """,
        {"user_id": user_id},
    )
    return {
        "user": _hydrate_record(user_rows[0]["user"]),
        "knowledge_bases": [_hydrate_record(row["knowledge_base"]) for row in knowledge_base_rows],
        "documents": [_hydrate_record(row["document"]) for row in document_rows],
        "memory_entries": [_hydrate_record(row["memory_entry"]) for row in memory_rows],
    }


async def _fetch_related_edges_for_user(*, user_id: int) -> list[dict[str, Any]]:
    rows = await fetch_neo4j_records(
        """
        MATCH (:User {id: $user_id})-[:OWNS]->(:KnowledgeBase)
              -[:CONTAINS]->(source:Document)-[r:RELATED]->(target:Document)
        MATCH (:User {id: $user_id})-[:OWNS]->(:KnowledgeBase)-[:CONTAINS]->(target)
        RETURN source.id AS source_document_id, target.id AS target_document_id, properties(r) AS metadata
        ORDER BY r.relationship_score DESC, r.shared_memory_count DESC,
                 r.jaccard_similarity DESC, source.id ASC, target.id ASC
        """,
        {"user_id": user_id},
    )
    return [
        _build_related_edge(
            source_document_id=row["source_document_id"],
            target_document_id=row["target_document_id"],
            metadata=row["metadata"],
        )
        for row in rows
    ]


def _finalize_payload(
        *,
        scope: str,
        root_node_id: str,
        include_memory: bool,
        include_relationships: bool,
        relationship_scope: str | None,
        min_shared_memory_count: int | None,
        min_relationship_score: float | None,
        max_related_edges: int | None,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "generated_at": datetime.now(),
        "root_node_id": root_node_id,
        "include_memory": include_memory,
        "include_relationships": include_relationships,
        "relationship_strategy": "shared_memory_entries" if include_relationships else None,
        "relationship_scope": relationship_scope if include_relationships else None,
        "min_shared_memory_count": min_shared_memory_count if include_relationships else None,
        "min_relationship_score": min_relationship_score if include_relationships else None,
        "max_related_edges": max_related_edges if include_relationships else None,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": _build_graph_type_counts(items=nodes, key="node_type"),
        "edge_type_counts": _build_graph_type_counts(items=edges, key="edge_type"),
    }


async def build_user_graph_payload_from_neo4j(
        *,
        current_user,
        include_memory: bool,
        include_relationships: bool,
        min_shared_memory_count: int,
        min_relationship_score: float,
        max_related_edges: int,
) -> dict[str, Any] | None:
    if not should_use_neo4j_graph_backend():
        return None

    try:
        records = await _fetch_user_graph_records(user_id=current_user.id)
        user = records["user"]
        if user is None:
            return None

        knowledge_bases = records["knowledge_bases"]
        documents = records["documents"]
        memory_entries = records["memory_entries"]
        documents_by_knowledge_base_id: dict[str, list] = {}
        for document in documents:
            documents_by_knowledge_base_id.setdefault(document.knowledge_base_id, []).append(document)

        memory_entries_by_document_id: dict[str, list] = {}
        for memory_entry in memory_entries:
            memory_entries_by_document_id.setdefault(memory_entry.document_id, []).append(memory_entry)

        user_node = build_user_node(user=user)
        nodes = [user_node]
        edges: list[dict[str, Any]] = []

        for knowledge_base in knowledge_bases:
            kb_documents = documents_by_knowledge_base_id.get(knowledge_base.id, [])
            kb_node = build_knowledge_base_node(
                knowledge_base=knowledge_base,
                parent_id=user_node["id"],
                document_count=len(kb_documents),
            )
            nodes.append(kb_node)
            edges.append(
                build_edge(
                    source=user_node["id"],
                    target=kb_node["id"],
                    edge_type="owns",
                )
            )
            for document in kb_documents:
                document_node = build_document_node(
                    document=document,
                    parent_id=kb_node["id"],
                )
                nodes.append(document_node)
                edges.append(
                    build_edge(
                        source=kb_node["id"],
                        target=document_node["id"],
                        edge_type="contains",
                    )
                )
                if include_memory:
                    for memory_entry in memory_entries_by_document_id.get(document.id, []):
                        memory_node = build_memory_node(
                            memory_entry=memory_entry,
                            parent_id=document_node["id"],
                        )
                        nodes.append(memory_node)
                        edges.append(
                            build_edge(
                                source=document_node["id"],
                                target=memory_node["id"],
                                edge_type="extracts",
                            )
                        )

        if include_relationships:
            related_edges = await _fetch_related_edges_for_user(user_id=current_user.id)
            edges.extend(
                _filter_related_edges(
                    edges=related_edges,
                    min_shared_memory_count=min_shared_memory_count,
                    min_relationship_score=min_relationship_score,
                    max_related_edges=max_related_edges,
                )
            )

        return _finalize_payload(
            scope="user",
            root_node_id=user_node["id"],
            include_memory=include_memory,
            include_relationships=include_relationships,
            relationship_scope="user",
            min_shared_memory_count=min_shared_memory_count,
            min_relationship_score=min_relationship_score,
            max_related_edges=max_related_edges,
            nodes=nodes,
            edges=edges,
        )
    except Exception as exc:  # pragma: no cover - depends on external service
        app_logger.bind(module="graph_query").exception(
            f"neo4j user graph read failed error_type={type(exc).__name__} error={exc}"
        )
        return None


async def build_knowledge_base_graph_payload_from_neo4j(
        *,
        current_user,
        knowledge_base,
        include_memory: bool,
        include_relationships: bool,
        min_shared_memory_count: int,
        min_relationship_score: float,
        max_related_edges: int,
) -> dict[str, Any] | None:
    if not should_use_neo4j_graph_backend():
        return None

    try:
        user_rows = await fetch_neo4j_records(
            """
            MATCH (u:User {id: $user_id}) RETURN properties(u) AS user
            """,
            {"user_id": current_user.id},
        )
        kb_rows = await fetch_neo4j_records(
            """
            MATCH (kb:KnowledgeBase {id: $knowledge_base_id}) RETURN properties(kb) AS knowledge_base
            """,
            {"knowledge_base_id": knowledge_base.id},
        )
        if not user_rows or not kb_rows:
            return None

        document_rows = await fetch_neo4j_records(
            """
            MATCH (:KnowledgeBase {id: $knowledge_base_id})-[:CONTAINS]->(d:Document)
            RETURN properties(d) AS document
            ORDER BY d.created_at ASC, d.id ASC
            """,
            {"knowledge_base_id": knowledge_base.id},
        )
        memory_rows = await fetch_neo4j_records(
            """
            MATCH (:KnowledgeBase {id: $knowledge_base_id})-[:CONTAINS]->(:Document)-[:EXTRACTS]->(m:MemoryEntry)
            RETURN properties(m) AS memory_entry
            ORDER BY m.created_at ASC, m.id ASC
            """,
            {"knowledge_base_id": knowledge_base.id},
        )
        related_rows: list[dict[str, Any]] = []
        if include_relationships:
            related_rows = await fetch_neo4j_records(
                """
                MATCH (:KnowledgeBase {id: $knowledge_base_id})
                      -[:CONTAINS]->(source:Document)-[r:RELATED]->(target:Document)
                MATCH (:KnowledgeBase {id: $knowledge_base_id})-[:CONTAINS]->(target)
                RETURN source.id AS source_document_id, target.id AS target_document_id, properties(r) AS metadata
                ORDER BY r.relationship_score DESC, r.shared_memory_count DESC,
                         r.jaccard_similarity DESC, source.id ASC, target.id ASC
                """,
                {"knowledge_base_id": knowledge_base.id},
            )

        user = _hydrate_record(user_rows[0]["user"])
        knowledge_base_record = _hydrate_record(kb_rows[0]["knowledge_base"])
        documents = [_hydrate_record(row["document"]) for row in document_rows]
        memory_entries = [_hydrate_record(row["memory_entry"]) for row in memory_rows]
        memory_entries_by_document_id: dict[str, list] = {}
        for memory_entry in memory_entries:
            memory_entries_by_document_id.setdefault(memory_entry.document_id, []).append(memory_entry)

        user_node = build_user_node(user=user)
        kb_node = build_knowledge_base_node(
            knowledge_base=knowledge_base_record,
            parent_id=user_node["id"],
            document_count=len(documents),
        )
        nodes = [user_node, kb_node]
        edges = [
            build_edge(
                source=user_node["id"],
                target=kb_node["id"],
                edge_type="owns",
            )
        ]

        for document in documents:
            document_node = build_document_node(
                document=document,
                parent_id=kb_node["id"],
            )
            nodes.append(document_node)
            edges.append(
                build_edge(
                    source=kb_node["id"],
                    target=document_node["id"],
                    edge_type="contains",
                )
            )
            if include_memory:
                for memory_entry in memory_entries_by_document_id.get(document.id, []):
                    memory_node = build_memory_node(
                        memory_entry=memory_entry,
                        parent_id=document_node["id"],
                    )
                    nodes.append(memory_node)
                    edges.append(
                        build_edge(
                            source=document_node["id"],
                            target=memory_node["id"],
                            edge_type="extracts",
                        )
                    )

        if include_relationships:
            edges.extend(
                _filter_related_edges(
                    edges=[
                        _build_related_edge(
                            source_document_id=row["source_document_id"],
                            target_document_id=row["target_document_id"],
                            metadata=row["metadata"],
                        )
                        for row in related_rows
                    ],
                    min_shared_memory_count=min_shared_memory_count,
                    min_relationship_score=min_relationship_score,
                    max_related_edges=max_related_edges,
                )
            )

        return _finalize_payload(
            scope="knowledge_base",
            root_node_id=kb_node["id"],
            include_memory=include_memory,
            include_relationships=include_relationships,
            relationship_scope="knowledge_base",
            min_shared_memory_count=min_shared_memory_count,
            min_relationship_score=min_relationship_score,
            max_related_edges=max_related_edges,
            nodes=nodes,
            edges=edges,
        )
    except Exception as exc:  # pragma: no cover - depends on external service
        app_logger.bind(module="graph_query").exception(
            f"neo4j knowledge base graph read failed error_type={type(exc).__name__} error={exc}"
        )
        return None


async def build_document_graph_payload_from_neo4j(
        *,
        current_user,
        root_document,
        root_knowledge_base,
        include_memory: bool,
        include_relationships: bool,
        min_shared_memory_count: int,
        min_relationship_score: float,
        max_related_edges: int,
        relationship_scope: str,
) -> dict[str, Any] | None:
    if not should_use_neo4j_graph_backend():
        return None

    try:
        records = await _fetch_user_graph_records(user_id=current_user.id)
        user = records["user"]
        if user is None:
            return None

        knowledge_bases = records["knowledge_bases"]
        documents = records["documents"]
        root_document_record = next((item for item in documents if item.id == root_document.id), None)
        if root_document_record is None:
            return None

        root_node_id = f"document:{root_document.id}"
        related_edges: list[dict[str, Any]] = []
        related_document_ids: set[str] = set()
        if include_relationships:
            all_related_edges = await _fetch_related_edges_for_user(user_id=current_user.id)
            for edge in all_related_edges:
                source_id = edge["source"].removeprefix("document:")
                target_id = edge["target"].removeprefix("document:")
                if root_document.id not in {source_id, target_id}:
                    continue
                if relationship_scope == "knowledge_base":
                    other_document_id = target_id if source_id == root_document.id else source_id
                    other_document = next((item for item in documents if item.id == other_document_id), None)
                    if other_document is None or other_document.knowledge_base_id != root_knowledge_base.id:
                        continue
                related_edges.append(edge)
                related_document_ids.add(target_id if source_id == root_document.id else source_id)
            related_edges = _filter_related_edges(
                edges=related_edges,
                min_shared_memory_count=min_shared_memory_count,
                min_relationship_score=min_relationship_score,
                max_related_edges=max_related_edges,
            )

        included_documents: list = []
        seen_document_ids: set[str] = set()
        for document in documents:
            if document.id == root_document.id or document.id in related_document_ids:
                if document.id not in seen_document_ids:
                    included_documents.append(document)
                    seen_document_ids.add(document.id)

        included_document_count_by_kb_id: dict[str, int] = {}
        for document in included_documents:
            included_document_count_by_kb_id[document.knowledge_base_id] = (
                included_document_count_by_kb_id.get(document.knowledge_base_id, 0) + 1
            )

        nodes = [build_user_node(user=user)]
        edges: list[dict[str, Any]] = []
        knowledge_base_nodes: dict[str, dict[str, Any]] = {}
        visible_knowledge_bases = (
            knowledge_bases
            if relationship_scope == "user"
            else [
                item
                for item in knowledge_bases
                if item.id == root_knowledge_base.id
            ]
        )
        for knowledge_base in visible_knowledge_bases:
            if knowledge_base.id not in included_document_count_by_kb_id:
                continue
            kb_node = build_knowledge_base_node(
                knowledge_base=knowledge_base,
                parent_id=nodes[0]["id"],
                document_count=included_document_count_by_kb_id[knowledge_base.id],
            )
            knowledge_base_nodes[knowledge_base.id] = kb_node
            nodes.append(kb_node)
            edges.append(
                build_edge(
                    source=nodes[0]["id"],
                    target=kb_node["id"],
                    edge_type="owns",
                )
            )

        for document in sorted(
            included_documents,
            key=lambda item: (
                item.id != root_document.id,
                item.created_at,
                item.id,
            ),
        ):
            kb_node = knowledge_base_nodes.get(document.knowledge_base_id)
            if kb_node is None:
                continue
            document_node = build_document_node(
                document=document,
                parent_id=kb_node["id"],
            )
            nodes.append(document_node)
            edges.append(
                build_edge(
                    source=kb_node["id"],
                    target=document_node["id"],
                    edge_type="contains",
                )
            )

        if include_memory:
            root_memory_rows = await fetch_neo4j_records(
                """
                MATCH (:Document {id: $document_id})-[:EXTRACTS]->(m:MemoryEntry)
                RETURN properties(m) AS memory_entry
                ORDER BY m.created_at ASC, m.id ASC
                """,
                {"document_id": root_document.id},
            )
            for row in root_memory_rows:
                memory_entry = _hydrate_record(row["memory_entry"])
                memory_node = build_memory_node(
                    memory_entry=memory_entry,
                    parent_id=root_node_id,
                )
                nodes.append(memory_node)
                edges.append(
                    build_edge(
                        source=root_node_id,
                        target=memory_node["id"],
                        edge_type="extracts",
                    )
                )

        edges.extend(related_edges)

        return _finalize_payload(
            scope="document",
            root_node_id=root_node_id,
            include_memory=include_memory,
            include_relationships=include_relationships,
            relationship_scope=relationship_scope,
            min_shared_memory_count=min_shared_memory_count,
            min_relationship_score=min_relationship_score,
            max_related_edges=max_related_edges,
            nodes=nodes,
            edges=edges,
        )
    except Exception as exc:  # pragma: no cover - depends on external service
        app_logger.bind(module="graph_query").exception(
            f"neo4j document graph read failed error_type={type(exc).__name__} error={exc}"
        )
        return None
