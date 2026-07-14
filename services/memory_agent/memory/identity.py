import hashlib


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
    identity = "\x1f".join(
        (
            str(owner_id),
            knowledge_base_id if knowledge_base_id is not None else "<global>",
            source_type,
            source_id,
            source_version,
            content_hash,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def memory_slot_lock_key(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: str,
    subject: str,
    predicate: str,
) -> int:
    identity = "\x1f".join(
        (
            str(owner_id),
            knowledge_base_id if knowledge_base_id is not None else "<global>",
            memory_type,
            subject,
            predicate,
        )
    )
    return int.from_bytes(
        hashlib.sha256(identity.encode("utf-8")).digest()[:8],
        byteorder="big",
        signed=True,
    )
