from typing import Any

from schemas.chat import EvidenceCitationDraft


def normalize_text(text: str) -> str:
    return "".join(text.split()).lower()


def quote_exists_in_source(*, quote: str, source_text: str) -> bool:
    cleaned_quote = quote.strip()
    if not cleaned_quote:
        return False
    if cleaned_quote in source_text:
        return True
    normalized_quote = normalize_text(cleaned_quote)
    normalized_source = normalize_text(source_text)
    return bool(normalized_quote and normalized_quote in normalized_source)


def build_source_lookup(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item["source_id"]): item
        for item in sources
        if item.get("source_id")
    }


def validate_citation_drafts(
    citation_drafts: list[EvidenceCitationDraft],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    source_lookup = build_source_lookup(sources)
    valid_citations: list[dict[str, Any]] = []
    invalid_citations: list[dict[str, Any]] = []

    for item in citation_drafts:
        source = source_lookup.get(item.source_id)
        if not source:
            invalid_citations.append(
                {
                    "source_id": item.source_id,
                    "quote": item.quote,
                    "reason": item.reason,
                    "validation_status": "invalid",
                    "quote_found": False,
                    "validation_reason": "source_id_not_found",
                }
            )
            continue

        quote_found = quote_exists_in_source(
            quote=item.quote,
            source_text=source.get("text") or "",
        )
        citation = {
            "source_id": item.source_id,
            "document_id": source["document_id"],
            "chunk_id": source["chunk_id"],
            "page_no": source.get("page_no"),
            "quote": item.quote,
            "reason": item.reason,
            "validation_status": "valid" if quote_found else "invalid",
            "quote_found": quote_found,
            "validation_reason": "quote_found" if quote_found else "quote_not_found_in_source",
        }
        if quote_found:
            valid_citations.append(citation)
        else:
            invalid_citations.append(citation)

    source_count = len(sources)
    valid_count = len(valid_citations)
    invalid_count = len(invalid_citations)
    return {
        "valid_citations": valid_citations,
        "invalid_citations": invalid_citations,
        "summary": {
            "source_count": source_count,
            "draft_citation_count": len(citation_drafts),
            "valid_citation_count": valid_count,
            "invalid_citation_count": invalid_count,
            "has_valid_citation": valid_count > 0,
        },
    }


def apply_citation_confidence_policy(
    *,
    confidence: str,
    uncertainty: str | None,
    citation_validation: dict[str, Any],
) -> tuple[str, str | None]:
    summary = citation_validation["summary"]
    if summary["valid_citation_count"] > 0:
        if summary["invalid_citation_count"] > 0:
            note = "部分引用未通过校验，已从 citations 中移除。"
            return confidence, append_uncertainty(uncertainty, note)
        return confidence, uncertainty

    if summary["source_count"] == 0:
        return "low", append_uncertainty(uncertainty, "当前没有可用证据来源。")

    if summary["draft_citation_count"] == 0:
        return "low", append_uncertainty(uncertainty, "回答没有提供可校验引用。")

    return "low", append_uncertainty(uncertainty, "所有引用均未通过 source_id 或 quote 校验。")


def append_uncertainty(current: str | None, note: str) -> str:
    if not current:
        return note
    if note in current:
        return current
    return f"{current} {note}"
