import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from schemas.eval import EvalCase, EvalDataset, EvalPrediction
from services.eval_service import build_eval_run


def build_debug_packet(*, final_chunk_ids: list[str]) -> dict:
    final_context = [
        {
            "rank": index,
            "recall_type": "vector+keyword" if index == 1 else "vector",
            "document_id": f"doc_{index}",
            "chunk_id": chunk_id,
            "fusion_score": 0.05 / index,
            "rerank_score": 0.06 / index,
            "text_preview": f"debug preview for {chunk_id}",
        }
        for index, chunk_id in enumerate(final_chunk_ids, start=1)
    ]
    return {
        "route": {
            "query_type": "kb_qa",
            "requires_retrieval": True,
            "target_pipeline": "evidence_rag",
            "confidence": "medium",
            "reason": "eval debug",
        },
        "query_terms": ["fastapi", "jwt", "milvus"],
        "lexical_backend": "postgres_keyword",
        "counts": {
            "raw_count": len(final_chunk_ids),
            "dedup_count": len(final_chunk_ids),
            "vector_count": len(final_chunk_ids),
            "lexical_count": 1,
            "memory_count": 0,
            "candidate_count": len(final_chunk_ids) + 1,
            "fusion_count": len(final_chunk_ids),
            "rerank_count": len(final_chunk_ids),
            "final_count": len(final_chunk_ids),
        },
        "vector_candidates": final_context,
        "lexical_candidates": final_context[:1],
        "memory_candidates": [],
        "fused_candidates": final_context,
        "final_context": final_context,
        "answer_debug": {
            "source_count": len(final_chunk_ids),
            "citation_count": 1,
            "confidence": "medium",
        },
    }


def main():
    dataset = EvalDataset(
        dataset_id="debug_day11_dataset",
        name="Day 11 Debug Dataset",
        cases=[
            EvalCase(
                case_id="case_hit",
                question="FastAPI JWT Milvus 的检索调试怎么做？",
                expected_answer="FastAPI JWT Milvus Retrieval Debug",
                expected_source_chunk_ids=["chunk_expected"],
                tags=["retrieval", "debug"],
                difficulty="medium",
            ),
            EvalCase(
                case_id="case_miss",
                question="系统是否能召回不存在的 chunk？",
                expected_answer="证据不足",
                expected_source_chunk_ids=["chunk_missing"],
                tags=["negative"],
                difficulty="easy",
            ),
        ],
    )
    predictions = {
        "case_hit": EvalPrediction(
            answer="FastAPI JWT Milvus 的 Retrieval Debug 需要记录 router、recall、fusion 和 rerank。",
            sources=[
                {
                    "source_id": "S1",
                    "document_id": "doc_1",
                    "chunk_id": "chunk_expected",
                    "source_chunk_ids": ["chunk_expected"],
                }
            ],
            citations=[
                {
                    "source_id": "S1",
                    "document_id": "doc_1",
                    "chunk_id": "chunk_expected",
                }
            ],
            debug=build_debug_packet(final_chunk_ids=["chunk_expected", "chunk_other"]),
            latency_ms=120.0,
            token_cost=0.0,
            llm_call_count=1,
            retrieval_count=3,
        ),
        "case_miss": EvalPrediction(
            answer="当前证据不足，无法确认。",
            sources=[],
            citations=[],
            debug=build_debug_packet(final_chunk_ids=["chunk_other"]),
            latency_ms=80.0,
            token_cost=0.0,
            llm_call_count=1,
            retrieval_count=3,
        ),
    }
    eval_run = build_eval_run(
        dataset=dataset,
        predictions_by_case_id=predictions,
        run_id="debug_day11_run",
        k=2,
    )

    print("开始执行 Day 11 RAG Eval 调试脚本...", flush=True)
    print(f"case_count={eval_run.summary['case_count']}", flush=True)
    print(f"avg_recall_at_k={eval_run.summary['avg_recall_at_k']:.4f}", flush=True)
    print(f"avg_mrr={eval_run.summary['avg_mrr']:.4f}", flush=True)
    print(f"avg_ndcg={eval_run.summary['avg_ndcg']:.4f}", flush=True)
    print(f"source_hit_rate={eval_run.summary['source_hit_rate']:.4f}", flush=True)
    print(f"avg_citation_accuracy={eval_run.summary['avg_citation_accuracy']:.4f}", flush=True)
    print(f"avg_answer_relevance={eval_run.summary['avg_answer_relevance']:.4f}", flush=True)
    for result in eval_run.results:
        print("=" * 60, flush=True)
        print(f"case_id={result.case_id}", flush=True)
        print(f"recall_at_k={result.retrieval.recall_at_k:.4f}", flush=True)
        print(f"mrr={result.retrieval.mrr:.4f}", flush=True)
        print(f"ndcg={result.retrieval.ndcg:.4f}", flush=True)
        print(f"source_hit={result.retrieval.source_hit}", flush=True)
        print(f"citation_accuracy={result.generation.citation_accuracy:.4f}", flush=True)
        print(f"abstention_accuracy={result.generation.abstention_accuracy:.4f}", flush=True)


if __name__ == "__main__":
    main()
