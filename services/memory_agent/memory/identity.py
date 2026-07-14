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
