import hashlib
import json


def _canonical_identity(tag: str, values: list[str | int | None]) -> bytes:
    serialized = json.dumps(
        [tag, 1, values],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")


def normalize_memory_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def memory_fingerprint(*, subject: str, predicate: str, value: str) -> str:
    normalized = "\x1f".join(
        (
            normalize_memory_text(subject),
            normalize_memory_text(predicate),
            normalize_memory_text(value),
        )
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def evidence_identity(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    source_type: str,
    source_id: str,
    source_version: str,
    content_hash: str,
) -> str:
    identity = _canonical_identity(
        "mneme:evidence-identity",
        [
            owner_id,
            knowledge_base_id,
            source_type,
            source_id,
            source_version,
            content_hash,
        ],
    )
    return hashlib.sha256(identity).hexdigest()


def memory_slot_lock_key(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: str,
    subject: str,
    predicate: str,
) -> int:
    identity = _canonical_identity(
        "mneme:memory-slot-lock",
        [
            owner_id,
            knowledge_base_id,
            memory_type,
            subject,
            predicate,
        ],
    )
    return int.from_bytes(
        hashlib.sha256(identity).digest()[:8],
        byteorder="big",
        signed=True,
    )
