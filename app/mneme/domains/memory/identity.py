import hashlib
from typing import Any

DEFAULT_EXTRACTION_VERSION = "v1"


def normalize_memory_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def build_memory_source_fingerprint(entry: dict[str, Any]) -> str:
    extraction_version = entry.get("extraction_version") or DEFAULT_EXTRACTION_VERSION
    parts = (
        entry.get("user_id"),
        entry.get("knowledge_base_id"),
        entry.get("document_id"),
        entry.get("chunk_id"),
        entry.get("entry_type"),
        entry.get("entry_name"),
        entry.get("summary"),
        entry.get("evidence_text"),
        extraction_version,
    )
    raw = "|".join(normalize_memory_text(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_memory_entry_id(source_fingerprint: str) -> str:
    return f"entry_{source_fingerprint[:24]}"


def prepare_memory_entry_payload(entry: dict[str, Any], *, stable_id: bool = False) -> dict[str, Any]:
    payload = dict(entry)
    payload.setdefault("extraction_version", DEFAULT_EXTRACTION_VERSION)
    payload.setdefault("status", "active")
    payload.setdefault("confidence", 0.5)
    payload["source_fingerprint"] = payload.get("source_fingerprint") or build_memory_source_fingerprint(payload)
    if stable_id or not payload.get("id"):
        payload["id"] = build_memory_entry_id(payload["source_fingerprint"])
    return payload
