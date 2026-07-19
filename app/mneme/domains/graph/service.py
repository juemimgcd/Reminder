from datetime import datetime
from itertools import combinations

from app.mneme.models.user import User


def build_user_node(*, user: User) -> dict:
    display_name = user.display_name or user.username
    return {
        "id": f"user:{user.id}",
        "entity_id": str(user.id),
        "node_type": "user",
        "label": display_name,
        "parent_id": None,
        "depth": 0,
        "metadata": {
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
        },
    }


def build_knowledge_base_node(*, knowledge_base, parent_id: str, document_count: int) -> dict:
    return {
        "id": f"knowledge_base:{knowledge_base.id}",
        "entity_id": knowledge_base.id,
        "node_type": "knowledge_base",
        "label": knowledge_base.name,
        "parent_id": parent_id,
        "depth": 1,
        "metadata": {
            "description": knowledge_base.description,
            "is_default": knowledge_base.is_default,
            "document_count": document_count,
            "created_at": knowledge_base.created_at,
            "updated_at": knowledge_base.updated_at,
        },
    }


def build_document_node(*, document, parent_id: str) -> dict:
    return {
        "id": f"document:{document.id}",
        "entity_id": document.id,
        "node_type": "document",
        "label": document.file_name,
        "parent_id": parent_id,
        "depth": 2,
        "metadata": {
            "file_name": document.file_name,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "status": document.status,
            "knowledge_base_id": document.knowledge_base_id,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        },
    }


def build_memory_node(*, memory_entry, parent_id: str) -> dict:
    return {
        "id": f"memory_entry:{memory_entry.id}",
        "entity_id": memory_entry.id,
        "node_type": "memory_entry",
        "label": memory_entry.entry_name,
        "parent_id": parent_id,
        "depth": 3,
        "metadata": {
            "entry_name": memory_entry.entry_name,
            "entry_type": memory_entry.entry_type,
            "summary": memory_entry.summary,
            "evidence_text": memory_entry.evidence_text,
            "importance_score": memory_entry.importance_score,
            "document_id": memory_entry.document_id,
            "knowledge_base_id": memory_entry.knowledge_base_id,
            "chunk_id": memory_entry.chunk_id,
            "created_at": memory_entry.created_at,
            "updated_at": memory_entry.updated_at,
        },
    }


def build_edge(*, source: str, target: str, edge_type: str, metadata: dict | None = None) -> dict:
    return {
        "id": f"edge:{source}->{target}",
        "source": source,
        "target": target,
        "edge_type": edge_type,
        "metadata": metadata or {},
    }


def _build_memory_segments(*, parent_node_id: str, memory_entries: list) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    for memory_entry in sorted(memory_entries, key=lambda item: item.created_at):
        memory_node = build_memory_node(
            memory_entry=memory_entry,
            parent_id=parent_node_id,
        )
        nodes.append(memory_node)
        edges.append(
            build_edge(
                source=parent_node_id,
                target=memory_node["id"],
                edge_type="extracts",
            )
        )
    return nodes, edges


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _build_memory_signature(memory_entry) -> tuple[str, str]:
    return (
        _normalize_text(memory_entry.entry_name),
        _normalize_text(memory_entry.entry_type),
    )


def _build_graph_type_counts(*, items: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_key = item.get(key)
        if not item_key:
            continue
        counts[item_key] = counts.get(item_key, 0) + 1
    return counts


def _annotate_relationship_ranks(edges: list[dict]) -> list[dict]:
    for index, edge in enumerate(edges, start=1):
        edge["metadata"]["relationship_rank"] = index
    return edges


def _build_related_document_edges(
        *,
        documents: list,
        memory_entries: list,
        min_shared_memory_count: int,
        min_relationship_score: float,
        max_related_edges: int | None,
) -> list[dict]:
    documents_by_id = {document.id: document for document in documents}
    signatures_by_document_id: dict[str, dict[tuple[str, str], dict]] = {}

    for memory_entry in memory_entries:
        document_id = memory_entry.document_id
        if document_id not in documents_by_id:
            continue

        signature = _build_memory_signature(memory_entry)
        if not signature[0]:
            continue

        doc_signatures = signatures_by_document_id.setdefault(document_id, {})
        previous = doc_signatures.get(signature)
        candidate = {
            "entry_name": memory_entry.entry_name,
            "entry_type": memory_entry.entry_type,
            "importance_score": memory_entry.importance_score,
        }
        if previous is None or candidate["importance_score"] > previous["importance_score"]:
            doc_signatures[signature] = candidate

    signatures_to_documents: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for document_id, signatures in signatures_by_document_id.items():
        for signature, payload in signatures.items():
            signatures_to_documents.setdefault(signature, []).append((document_id, payload))

    pair_buckets: dict[tuple[str, str], dict] = {}
    for signature, linked_documents in signatures_to_documents.items():
        if len(linked_documents) < 2:
            continue
        ordered_documents = sorted(linked_documents, key=lambda item: item[0])
        for left, right in combinations(ordered_documents, 2):
            left_document_id, left_payload = left
            right_document_id, right_payload = right
            pair_key = (left_document_id, right_document_id)
            bucket = pair_buckets.setdefault(
                pair_key,
                {
                    "shared_memories": [],
                    "shared_memory_types": set(),
                    "max_importance_score": 0.0,
                    "total_importance_score": 0.0,
                },
            )
            chosen_payload = (
                left_payload
                if left_payload["importance_score"] >= right_payload["importance_score"]
                else right_payload
            )
            shared_importance_score = max(left_payload["importance_score"], right_payload["importance_score"])
            bucket["shared_memories"].append(
                {
                    "entry_name": chosen_payload["entry_name"],
                    "entry_type": chosen_payload["entry_type"],
                    "importance_score": round(
                        shared_importance_score,
                        4,
                    ),
                }
            )
            bucket["shared_memory_types"].add(chosen_payload["entry_type"])
            bucket["total_importance_score"] += shared_importance_score
            bucket["max_importance_score"] = max(
                bucket["max_importance_score"],
                left_payload["importance_score"],
                right_payload["importance_score"],
            )

    related_edges: list[dict] = []
    for (left_document_id, right_document_id), bucket in sorted(pair_buckets.items()):
        shared_memory_count = len(bucket["shared_memories"])
        if shared_memory_count < min_shared_memory_count:
            continue

        left_document = documents_by_id[left_document_id]
        right_document = documents_by_id[right_document_id]
        left_signature_count = len(signatures_by_document_id.get(left_document_id, {}))
        right_signature_count = len(signatures_by_document_id.get(right_document_id, {}))
        union_signature_count = max(
            left_signature_count + right_signature_count - shared_memory_count,
            1,
        )
        avg_importance_score = bucket["total_importance_score"] / shared_memory_count
        jaccard_similarity = shared_memory_count / union_signature_count
        overlap_ratio = shared_memory_count / max(min(left_signature_count, right_signature_count), 1)
        count_score = min(shared_memory_count / 5, 1.0)
        type_diversity_score = min(len(bucket["shared_memory_types"]) / 3, 1.0)
        relationship_score = round(
            (
                0.35 * jaccard_similarity
                + 0.20 * overlap_ratio
                + 0.25 * avg_importance_score
                + 0.10 * type_diversity_score
                + 0.10 * count_score
            ),
            4,
        )
        if relationship_score < min_relationship_score:
            continue

        related_edges.append(
            build_edge(
                source=f"document:{left_document_id}",
                target=f"document:{right_document_id}",
                edge_type="related",
                metadata={
                    "relationship_strategy": "shared_memory_entries",
                    "shared_memory_count": shared_memory_count,
                    "shared_memory_types": sorted(bucket["shared_memory_types"]),
                    "shared_memories": bucket["shared_memories"][:8],
                    "strength": round(overlap_ratio, 4),
                    "jaccard_similarity": round(jaccard_similarity, 4),
                    "avg_importance_score": round(avg_importance_score, 4),
                    "relationship_score": relationship_score,
                    "max_importance_score": round(bucket["max_importance_score"], 4),
                    "cross_knowledge_base": left_document.knowledge_base_id != right_document.knowledge_base_id,
                    "source_document_name": left_document.file_name,
                    "target_document_name": right_document.file_name,
                    "source_knowledge_base_id": left_document.knowledge_base_id,
                    "target_knowledge_base_id": right_document.knowledge_base_id,
                },
            )
        )

    related_edges.sort(
        key=lambda item: (
            -item["metadata"]["relationship_score"],
            -item["metadata"]["shared_memory_count"],
            -item["metadata"]["jaccard_similarity"],
            item["source"],
            item["target"],
        )
    )
    if max_related_edges is not None:
        related_edges = related_edges[:max_related_edges]
    return _annotate_relationship_ranks(related_edges)


def build_user_graph_payload(
        *,
        user: User,
        knowledge_bases: list,
        documents: list,
        memory_entries: list | None = None,
        include_memory: bool = False,
        include_relationships: bool = False,
        min_shared_memory_count: int = 2,
        min_relationship_score: float = 0.35,
        max_related_edges: int | None = 80,
) -> dict:
    user_node = build_user_node(user=user)
    nodes = [user_node]
    edges: list[dict] = []

    documents_by_knowledge_base_id: dict[str, list] = {}
    for document in documents:
        documents_by_knowledge_base_id.setdefault(document.knowledge_base_id, []).append(document)

    memory_entries_by_document_id: dict[str, list] = {}
    for memory_entry in memory_entries or []:
        memory_entries_by_document_id.setdefault(memory_entry.document_id, []).append(memory_entry)

    for knowledge_base in knowledge_bases:
        kb_node = build_knowledge_base_node(
            knowledge_base=knowledge_base,
            parent_id=user_node["id"],
            document_count=len(documents_by_knowledge_base_id.get(knowledge_base.id, [])),
        )
        nodes.append(kb_node)
        edges.append(
            build_edge(
                source=user_node["id"],
                target=kb_node["id"],
                edge_type="owns",
            )
        )

        kb_documents = sorted(
            documents_by_knowledge_base_id.get(knowledge_base.id, []),
            key=lambda item: item.created_at,
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
                memory_nodes, memory_edges = _build_memory_segments(
                    parent_node_id=document_node["id"],
                    memory_entries=memory_entries_by_document_id.get(document.id, []),
                )
                nodes.extend(memory_nodes)
                edges.extend(memory_edges)

    if include_relationships:
        edges.extend(
            _build_related_document_edges(
                documents=documents,
                memory_entries=memory_entries or [],
                min_shared_memory_count=min_shared_memory_count,
                min_relationship_score=min_relationship_score,
                max_related_edges=max_related_edges,
            )
        )

    return {
        "scope": "user",
        "generated_at": datetime.now(),
        "root_node_id": user_node["id"],
        "include_memory": include_memory,
        "include_relationships": include_relationships,
        "relationship_strategy": "shared_memory_entries" if include_relationships else None,
        "relationship_scope": "user" if include_relationships else None,
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


def build_knowledge_base_graph_payload(
        *,
        user: User,
        knowledge_base,
        documents: list,
        memory_entries: list | None = None,
        include_memory: bool = False,
        include_relationships: bool = False,
        min_shared_memory_count: int = 2,
        min_relationship_score: float = 0.35,
        max_related_edges: int | None = 80,
) -> dict:
    user_node = build_user_node(user=user)
    kb_node = build_knowledge_base_node(
        knowledge_base=knowledge_base,
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
    memory_entries_by_document_id: dict[str, list] = {}
    for memory_entry in memory_entries or []:
        memory_entries_by_document_id.setdefault(memory_entry.document_id, []).append(memory_entry)

    for document in sorted(documents, key=lambda item: item.created_at):
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
            memory_nodes, memory_edges = _build_memory_segments(
                parent_node_id=document_node["id"],
                memory_entries=memory_entries_by_document_id.get(document.id, []),
            )
            nodes.extend(memory_nodes)
            edges.extend(memory_edges)

    if include_relationships:
        edges.extend(
            _build_related_document_edges(
                documents=documents,
                memory_entries=memory_entries or [],
                min_shared_memory_count=min_shared_memory_count,
                min_relationship_score=min_relationship_score,
                max_related_edges=max_related_edges,
            )
        )

    return {
        "scope": "knowledge_base",
        "generated_at": datetime.now(),
        "root_node_id": kb_node["id"],
        "include_memory": include_memory,
        "include_relationships": include_relationships,
        "relationship_strategy": "shared_memory_entries" if include_relationships else None,
        "relationship_scope": "knowledge_base" if include_relationships else None,
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


def build_document_graph_payload(
        *,
        user: User,
        knowledge_bases: list,
        root_document,
        documents: list,
        root_memory_entries: list | None = None,
        relationship_memory_entries: list | None = None,
        include_memory: bool = False,
        include_relationships: bool = False,
        min_shared_memory_count: int = 2,
        min_relationship_score: float = 0.35,
        max_related_edges: int | None = 24,
        relationship_scope: str = "knowledge_base",
) -> dict:
    user_node = build_user_node(user=user)
    root_document_node_id = f"document:{root_document.id}"

    relationship_edges: list[dict] = []
    related_document_ids: set[str] = set()
    if include_relationships:
        all_relationship_edges = _build_related_document_edges(
            documents=documents,
            memory_entries=relationship_memory_entries or [],
            min_shared_memory_count=min_shared_memory_count,
            min_relationship_score=min_relationship_score,
            max_related_edges=None,
        )
        relationship_edges = [
            item
            for item in all_relationship_edges
            if item["source"] == root_document_node_id or item["target"] == root_document_node_id
        ]
        if max_related_edges is not None:
            relationship_edges = relationship_edges[:max_related_edges]
        relationship_edges = _annotate_relationship_ranks(relationship_edges)
        for edge in relationship_edges:
            for node_id in (edge["source"], edge["target"]):
                if node_id != root_document_node_id and node_id.startswith("document:"):
                    related_document_ids.add(node_id.removeprefix("document:"))

    included_documents: list = []
    seen_document_ids: set[str] = set()
    for document in [root_document, *documents]:
        if document.id == root_document.id or document.id in related_document_ids:
            if document.id not in seen_document_ids:
                included_documents.append(document)
                seen_document_ids.add(document.id)

    included_document_count_by_kb_id: dict[str, int] = {}
    for document in included_documents:
        included_document_count_by_kb_id[document.knowledge_base_id] = (
            included_document_count_by_kb_id.get(document.knowledge_base_id, 0) + 1
        )

    nodes = [user_node]
    edges: list[dict] = []
    knowledge_base_nodes: dict[str, dict] = {}
    for knowledge_base in knowledge_bases:
        if knowledge_base.id not in included_document_count_by_kb_id:
            continue
        kb_node = build_knowledge_base_node(
            knowledge_base=knowledge_base,
            parent_id=user_node["id"],
            document_count=included_document_count_by_kb_id[knowledge_base.id],
        )
        knowledge_base_nodes[knowledge_base.id] = kb_node
        nodes.append(kb_node)
        edges.append(
            build_edge(
                source=user_node["id"],
                target=kb_node["id"],
                edge_type="owns",
            )
        )

    ordered_documents = sorted(
        included_documents,
        key=lambda item: (item.id != root_document.id, item.created_at, item.id),
    )
    for document in ordered_documents:
        kb_node = knowledge_base_nodes.get(document.knowledge_base_id)
        if not kb_node:
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
        memory_nodes, memory_edges = _build_memory_segments(
            parent_node_id=root_document_node_id,
            memory_entries=root_memory_entries or [],
        )
        nodes.extend(memory_nodes)
        edges.extend(memory_edges)

    edges.extend(relationship_edges)

    return {
        "scope": "document",
        "generated_at": datetime.now(),
        "root_node_id": root_document_node_id,
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
