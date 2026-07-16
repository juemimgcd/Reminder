import hashlib
from pathlib import Path

from app.mneme.memoria.server.cli.backfill import _aggregate_hash, _raw_chunk_map


def _raw(index: int, chunk_id: str, content: str) -> dict:
    return {
        "chunk_index": index,
        "chunk_id": chunk_id,
        "content": content,
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
    }


def test_backfill_chunk_scan_detects_duplicate_keys_and_hash_mismatch():
    first = _raw(0, "c0", "first")
    mapped, valid = _raw_chunk_map([first, first.copy()])
    assert not valid
    assert len(mapped) == 1

    broken = _raw(0, "c0", "first")
    broken["content_hash"] = "0" * 64
    _, valid = _raw_chunk_map([broken])
    assert not valid


def test_backfill_aggregate_hash_is_stable_for_sorted_chunk_keys():
    chunks = [_raw(1, "c1", "second"), _raw(0, "c0", "first")]
    expected = hashlib.sha256((chunks[1]["content_hash"] + chunks[0]["content_hash"]).encode("ascii")).hexdigest()
    assert _aggregate_hash({(chunk["chunk_index"], chunk["chunk_id"]): chunk for chunk in chunks}) == expected


def test_backfill_supports_resume_filters_and_reports_dry_run_without_writes():
    source = Path("app/mneme/memoria/server/cli/backfill.py").read_text(encoding="utf-8")

    assert "args.owner_id" in source
    assert "args.knowledge_base_id" in source
    assert "args.resume_from" in source
    assert '"dry_run": args.dry_run' in source
    assert "db.add" not in source
    assert "db.execute" not in source
