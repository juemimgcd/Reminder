import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from schemas.chat import EvidenceCitationDraft
from services.citation_validation_service import apply_citation_confidence_policy, validate_citation_drafts


def main():
    sources = [
        {
            "source_id": "S1",
            "document_id": "doc_1",
            "chunk_id": "chunk_1",
            "page_no": 1,
            "text": "FastAPI 项目中负责接口设计、JWT 鉴权和 Milvus 检索接入。",
        }
    ]
    citation_drafts = [
        EvidenceCitationDraft(
            source_id="S1",
            quote="JWT 鉴权和 Milvus 检索接入",
            reason="这段证据直接说明了项目经验。",
        ),
        EvidenceCitationDraft(
            source_id="S1",
            quote="不存在的引用文本",
            reason="这条 quote 不在 source text 里。",
        ),
        EvidenceCitationDraft(
            source_id="S9",
            quote="FastAPI 项目",
            reason="这条 source_id 不存在。",
        ),
    ]
    validation = validate_citation_drafts(citation_drafts, sources)
    confidence, uncertainty = apply_citation_confidence_policy(
        confidence="high",
        uncertainty=None,
        citation_validation=validation,
    )

    print("开始执行 Day 12 Citation Validation 调试脚本...", flush=True)
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
