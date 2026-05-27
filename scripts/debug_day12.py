import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.schemas.chat import EvidenceCitationDraft
from app.mneme.services.citation_validation_service import apply_citation_confidence_policy, validate_citation_drafts


def main():
    sources = [
        {
            "source_id": "S1",
            "document_id": "doc_1",
            "chunk_id": "chunk_1",
            "page_no": 1,
            "text": "FastAPI project covers API design, JWT auth, and Milvus retrieval integration.",
        }
    ]
    citation_drafts = [
        EvidenceCitationDraft(
            source_id="S1",
            quote="JWT auth and Milvus retrieval integration",
            reason="This evidence directly describes project experience.",
        ),
        EvidenceCitationDraft(
            source_id="S1",
            quote="涓嶅瓨鍦ㄧ殑寮曠敤鏂囨湰",
            reason="This quote does not appear in the source text.",
        ),
        EvidenceCitationDraft(
            source_id="S9",
            quote="FastAPI 椤圭洰",
            reason="This source_id does not exist.",
        ),
    ]
    validation = validate_citation_drafts(citation_drafts, sources)
    confidence, uncertainty = apply_citation_confidence_policy(
        confidence="high",
        uncertainty=None,
        citation_validation=validation,
    )

    print("寮€濮嬫墽琛?Day 12 Citation Validation 璋冭瘯鑴氭湰...", flush=True)
    print(f"valid_citation_count={validation['summary']['valid_citation_count']}", flush=True)
    print(f"invalid_citation_count={validation['summary']['invalid_citation_count']}", flush=True)
    print(f"has_valid_citation={validation['summary']['has_valid_citation']}", flush=True)
    print(f"confidence={confidence}", flush=True)
    print(f"uncertainty={uncertainty}", flush=True)
    for item in validation["valid_citations"]:
        print("=" * 60, flush=True)
        print(f"valid source_id={item['source_id']}", flush=True)
        print(f"quote_found={item['quote_found']}", flush=True)
        print(f"validation_reason={item['validation_reason']}", flush=True)
    for item in validation["invalid_citations"]:
        print("=" * 60, flush=True)
        print(f"invalid source_id={item['source_id']}", flush=True)
        print(f"quote_found={item['quote_found']}", flush=True)
        print(f"validation_reason={item['validation_reason']}", flush=True)


if __name__ == "__main__":
    main()
