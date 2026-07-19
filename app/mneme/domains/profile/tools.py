from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.mneme.domains.memory.governance import build_memory_governance_view
from app.mneme.models.memory_entry import MemoryEntry
from app.mneme.schemas.memory_governance import MemoryGovernanceData
from app.mneme.schemas.profile_evidence import (
    EvidenceProfileData,
    EvidenceProfileRiskItem,
    EvidenceProfileTraitItem,
    ProfileEvidenceItem,
    ProfileToolCallItem,
    TopicTimelineItem,
)

GOAL_MARKERS = (
    "goal",
    "plan",
    "next",
    "todo",
    "focus",
)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def serialize_evidence(entry: MemoryEntry) -> ProfileEvidenceItem:
    return ProfileEvidenceItem(
        entry_id=entry.id,
        entry_name=entry.entry_name,
        entry_type=entry.entry_type,
        summary=entry.summary,
        evidence_text=entry.evidence_text,
        document_id=entry.document_id,
        chunk_id=entry.chunk_id,
        created_at=entry.created_at,
    )


def collect_evidence_entries(entries: list[MemoryEntry], entry_ids: list[str]) -> list[ProfileEvidenceItem]:
    entries_by_id = {entry.id: entry for entry in entries}
    result: list[ProfileEvidenceItem] = []
    for entry_id in entry_ids:
        entry = entries_by_id.get(entry_id)
        if entry:
            result.append(serialize_evidence(entry))
    return result


def unique_evidence(items: list[ProfileEvidenceItem]) -> list[ProfileEvidenceItem]:
    seen: set[str] = set()
    result: list[ProfileEvidenceItem] = []
    for item in items:
        if item.entry_id in seen:
            continue
        seen.add(item.entry_id)
        result.append(item)
    return result


def search_stable_memory(governance: MemoryGovernanceData, *, limit: int = 6) -> list[EvidenceProfileTraitItem]:
    stable_items = [
        item
        for item in governance.canonical_memories
        if item.status in {"single", "stable", "merged"}
    ]
    stable_items.sort(
        key=lambda item: (
            -item.importance_score,
            -item.evidence_count,
            item.entry_name,
        )
    )
    return [
        EvidenceProfileTraitItem(
            trait_name=item.entry_name,
            summary=item.summary,
            confidence="high" if item.status in {"stable", "merged"} else "medium",
            evidence_entry_ids=item.entry_ids[:5],
        )
        for item in stable_items[:limit]
    ]


def search_recent_memory(
    entries: list[MemoryEntry],
    *,
    recent_days: int,
    limit: int = 6,
) -> list[EvidenceProfileTraitItem]:
    if not entries:
        return []

    latest = max(to_utc(entry.created_at) for entry in entries)
    cutoff = latest - timedelta(days=recent_days)
    recent_entries = [
        entry
        for entry in entries
        if to_utc(entry.created_at) >= cutoff
    ]
    recent_entries.sort(
        key=lambda item: (
            item.created_at,
            float(item.importance_score or 0.0),
            item.id,
        ),
        reverse=True,
    )
    return [
        EvidenceProfileTraitItem(
            trait_name=entry.entry_name,
            summary=entry.summary,
            confidence="medium",
            evidence_entry_ids=[entry.id],
        )
        for entry in recent_entries[:limit]
    ]


def search_topic_timeline(entries: list[MemoryEntry], *, limit: int = 8) -> list[TopicTimelineItem]:
    grouped: dict[tuple[str, str], list[MemoryEntry]] = defaultdict(list)
    for entry in entries:
        grouped[(entry.entry_type, entry.entry_name)].append(entry)

    timeline_items: list[TopicTimelineItem] = []
    for (entry_type, entry_name), group_entries in grouped.items():
        ordered = sorted(group_entries, key=lambda item: item.created_at)
        timeline_items.append(
            TopicTimelineItem(
                topic_name=entry_name,
                entry_type=entry_type,
                entry_count=len(ordered),
                first_seen_at=ordered[0].created_at,
                last_seen_at=ordered[-1].created_at,
                evidence_entry_ids=[entry.id for entry in ordered[:6]],
            )
        )

    timeline_items.sort(
        key=lambda item: (
            -item.entry_count,
            item.topic_name,
        )
    )
    return timeline_items[:limit]


def get_contradictions(governance: MemoryGovernanceData) -> list[EvidenceProfileRiskItem]:
    canonical_by_entry_id = {
        entry_id: item
        for item in governance.canonical_memories
        for entry_id in item.entry_ids
    }
    risks: list[EvidenceProfileRiskItem] = []
    for relation in governance.relations:
        if relation.relation_type != "contradict":
            continue
        canonical = canonical_by_entry_id.get(relation.source_entry_id)
        risk_name = canonical.entry_name if canonical else "conflicting memory"
        risks.append(
            EvidenceProfileRiskItem(
                risk_name=risk_name,
                summary=relation.reason,
                relation_type=relation.relation_type,
                evidence_entry_ids=[relation.source_entry_id, relation.target_entry_id],
            )
        )
    return risks


def search_goal_memory(entries: list[MemoryEntry], *, limit: int = 5) -> list[EvidenceProfileTraitItem]:
    goal_entries = []
    for entry in entries:
        text = f"{entry.entry_name} {entry.entry_type} {entry.summary} {entry.evidence_text}".lower()
        if any(marker in text for marker in GOAL_MARKERS):
            goal_entries.append(entry)

    goal_entries.sort(
        key=lambda item: (
            float(item.importance_score or 0.0),
            item.created_at,
            item.id,
        ),
        reverse=True,
    )
    return [
        EvidenceProfileTraitItem(
            trait_name=entry.entry_name,
            summary=entry.summary,
            confidence="medium",
            evidence_entry_ids=[entry.id],
        )
        for entry in goal_entries[:limit]
    ]


def build_profile_snapshot(
    *,
    knowledge_base_id: str,
    entries: list[MemoryEntry],
    governance: MemoryGovernanceData,
    recent_days: int,
) -> EvidenceProfileData:
    stable_traits = search_stable_memory(governance)
    recent_focus = search_recent_memory(entries, recent_days=recent_days)
    topic_timeline = search_topic_timeline(entries)
    risks = get_contradictions(governance)
    goals = search_goal_memory(entries)

    tool_calls = [
        ProfileToolCallItem(
            tool_name="search_stable_memory",
            input={"limit": 6},
            output_count=len(stable_traits),
            evidence_entry_ids=[entry_id for item in stable_traits for entry_id in item.evidence_entry_ids],
        ),
        ProfileToolCallItem(
            tool_name="search_recent_memory",
            input={"recent_days": recent_days, "limit": 6},
            output_count=len(recent_focus),
            evidence_entry_ids=[entry_id for item in recent_focus for entry_id in item.evidence_entry_ids],
        ),
        ProfileToolCallItem(
            tool_name="search_topic_timeline",
            input={"limit": 8},
            output_count=len(topic_timeline),
            evidence_entry_ids=[entry_id for item in topic_timeline for entry_id in item.evidence_entry_ids],
        ),
        ProfileToolCallItem(
            tool_name="get_contradictions",
            input={},
            output_count=len(risks),
            evidence_entry_ids=[entry_id for item in risks for entry_id in item.evidence_entry_ids],
        ),
        ProfileToolCallItem(
            tool_name="search_goal_memory",
            input={"limit": 5},
            output_count=len(goals),
            evidence_entry_ids=[entry_id for item in goals for entry_id in item.evidence_entry_ids],
        ),
    ]

    evidence_ids = [
        entry_id
        for collection in (stable_traits, recent_focus, goals, risks, topic_timeline)
        for item in collection
        for entry_id in item.evidence_entry_ids
    ]
    evidence = unique_evidence(collect_evidence_entries(entries, evidence_ids))
    uncertainty = None
    if risks:
        uncertainty = "Some profile signals include contradictory memory entries and should be reviewed."
    elif not stable_traits:
        uncertainty = "Not enough stable governed memories are available for a high-confidence profile."

    return EvidenceProfileData(
        knowledge_base_id=knowledge_base_id,
        entry_count=len(entries),
        canonical_memory_count=governance.canonical_memory_count,
        stable_traits=stable_traits,
        recent_focus=recent_focus,
        goals=goals,
        risks=risks,
        topic_timeline=topic_timeline,
        evidence=evidence,
        tool_calls=tool_calls,
        uncertainty=uncertainty,
    )


def build_evidence_profile_from_entries(
    *,
    knowledge_base_id: str,
    entries: list[MemoryEntry],
    recent_days: int = 30,
) -> EvidenceProfileData:
    governance = build_memory_governance_view(
        knowledge_base_id=knowledge_base_id,
        entries=entries,
    )
    return build_profile_snapshot(
        knowledge_base_id=knowledge_base_id,
        entries=entries,
        governance=governance,
        recent_days=recent_days,
    )
