import hashlib
import re
from collections import defaultdict
from typing import Any

from app.mneme.models.memory_entry import MemoryEntry
from app.mneme.schemas.memory_governance import CanonicalMemoryItem, MemoryGovernanceData, MemoryRelationItem

NEGATIVE_MARKERS = (
    "failed",
    "cannot",
    "can't",
    "not ",
    "blocked",
    "error",
)
POSITIVE_MARKERS = (
    "success",
    "can ",
    "resolved",
    "done",
    "complete",
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def canonical_key(entry: MemoryEntry) -> tuple[str, str]:
    return (
        normalize_text(entry.entry_type),
        normalize_text(entry.entry_name),
    )


def tokenize(value: str | None) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()

    tokens = set(re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]{2,}", normalized))
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    tokens.update(
        "".join(cjk_chars[index : index + 2])
        for index in range(max(len(cjk_chars) - 1, 0))
    )
    return tokens or {normalized}


def jaccard_similarity(left: str | None, right: str | None) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def text_polarity(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None

    if any(marker in normalized for marker in ("not completed", "not yet", "unfinished")):
        return "negative"

    has_negative = any(marker in normalized for marker in NEGATIVE_MARKERS)
    has_positive = any(marker in normalized for marker in POSITIVE_MARKERS)
    if has_negative and not has_positive:
        return "negative"
    if has_positive and not has_negative:
        return "positive"
    return None


def relation_type_counts(relations: list[MemoryRelationItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relation in relations:
        counts[relation.relation_type] = counts.get(relation.relation_type, 0) + 1
    return counts


def pick_representative_entry(entries: list[MemoryEntry]) -> MemoryEntry:
    return max(
        entries,
        key=lambda item: (
            float(item.importance_score or 0.0),
            item.created_at,
            item.id,
        ),
    )


def classify_memory_relation(
    source: MemoryEntry,
    target: MemoryEntry,
) -> tuple[str, float, str]:
    source_summary = normalize_text(source.summary)
    target_summary = normalize_text(target.summary)
    source_evidence = normalize_text(source.evidence_text)
    target_evidence = normalize_text(target.evidence_text)
    summary_similarity = jaccard_similarity(source.summary, target.summary)
    evidence_similarity = jaccard_similarity(source.evidence_text, target.evidence_text)
    source_polarity = text_polarity(f"{source.summary} {source.evidence_text}")
    target_polarity = text_polarity(f"{target.summary} {target.evidence_text}")

    if (
        source_summary == target_summary
        or source_evidence == target_evidence
        or max(summary_similarity, evidence_similarity) >= 0.92
    ):
        return "duplicate", 0.95, "same canonical key and near-identical text"

    if source_polarity and target_polarity and source_polarity != target_polarity:
        return "contradict", 0.72, "same canonical key with opposite polarity markers"

    if source_summary and target_summary and (source_summary in target_summary or target_summary in source_summary):
        return "refine", 0.78, "one summary is a more specific version of the other"

    if summary_similarity >= 0.65 or evidence_similarity >= 0.65:
        return "refine", 0.7, "same canonical key with strong semantic overlap"

    if source.created_at.date() != target.created_at.date():
        return "temporal_update", 0.62, "same canonical key observed at different times"

    return "supplement", 0.58, "same canonical key with complementary evidence"


def build_relations_for_group(entries: list[MemoryEntry]) -> list[MemoryRelationItem]:
    if len(entries) < 2:
        return []

    ordered_entries = sorted(entries, key=lambda item: (item.created_at, item.id))
    relations: list[MemoryRelationItem] = []
    for index, target in enumerate(ordered_entries[1:], start=1):
        source = ordered_entries[index - 1]
        relation_type, confidence, reason = classify_memory_relation(source, target)
        relations.append(
            MemoryRelationItem(
                relation_id=stable_id("relation", source.id, target.id, relation_type),
                source_entry_id=source.id,
                target_entry_id=target.id,
                relation_type=relation_type,
                confidence=confidence,
                reason=reason,
            )
        )
    return relations


def build_canonical_memory_item(
    *,
    knowledge_base_id: str,
    entries: list[MemoryEntry],
    relations: list[MemoryRelationItem],
) -> CanonicalMemoryItem:
    representative = pick_representative_entry(entries)
    relation_counts = relation_type_counts(relations)
    if relation_counts.get("contradict"):
        status = "needs_review"
    elif relation_counts.get("duplicate"):
        status = "merged"
    elif len(entries) > 1:
        status = "stable"
    else:
        status = "single"

    sorted_entries = sorted(entries, key=lambda item: item.created_at)
    document_ids = {entry.document_id for entry in entries}
    importance_score = max(float(entry.importance_score or 0.0) for entry in entries)

    return CanonicalMemoryItem(
        canonical_id=stable_id(
            "canonical",
            knowledge_base_id,
            representative.entry_type,
            representative.entry_name,
        ),
        entry_name=representative.entry_name,
        entry_type=representative.entry_type,
        summary=representative.summary,
        representative_entry_id=representative.id,
        entry_ids=[entry.id for entry in sorted_entries],
        evidence_count=len(entries),
        document_count=len(document_ids),
        importance_score=round(importance_score, 4),
        status=status,
        first_seen_at=sorted_entries[0].created_at,
        last_seen_at=sorted_entries[-1].created_at,
    )


def build_memory_governance_view(
    *,
    knowledge_base_id: str,
    entries: list[MemoryEntry],
) -> MemoryGovernanceData:
    grouped: dict[tuple[str, str], list[MemoryEntry]] = defaultdict(list)
    for entry in entries:
        key = canonical_key(entry)
        if not key[0] or not key[1]:
            continue
        grouped[key].append(entry)

    canonical_memories: list[CanonicalMemoryItem] = []
    relations: list[MemoryRelationItem] = []
    for group_entries in grouped.values():
        group_relations = build_relations_for_group(group_entries)
        relations.extend(group_relations)
        canonical_memories.append(
            build_canonical_memory_item(
                knowledge_base_id=knowledge_base_id,
                entries=group_entries,
                relations=group_relations,
            )
        )

    canonical_memories.sort(
        key=lambda item: (
            item.status != "needs_review",
            -item.evidence_count,
            -item.importance_score,
            item.entry_name,
        )
    )

    return MemoryGovernanceData(
        knowledge_base_id=knowledge_base_id,
        raw_entry_count=len(entries),
        canonical_memory_count=len(canonical_memories),
        relation_count=len(relations),
        relation_type_counts=relation_type_counts(relations),
        canonical_memories=canonical_memories,
        relations=relations,
    )
