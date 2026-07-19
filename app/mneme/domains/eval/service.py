import re
from datetime import datetime
from math import log2
from typing import Any

from app.mneme.schemas.eval import (
    EngineeringEvalMetrics,
    EvalCase,
    EvalDataset,
    EvalPrediction,
    EvalResult,
    EvalRun,
    GenerationEvalMetrics,
    RetrievalEvalMetrics,
)


def normalize_id(value: Any) -> str:
    return str(value).strip()


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def extract_retrieved_chunk_ids(debug: dict[str, Any], *, k: int | None = None) -> list[str]:
    final_context = debug.get("final_context") or []
    chunk_ids = [
        normalize_id(item.get("chunk_id"))
        for item in final_context
        if item.get("chunk_id")
    ]
    result = dedupe_preserve_order(chunk_ids)
    return result[:k] if k is not None else result


def extract_source_chunk_ids(sources: list[dict[str, Any]]) -> list[str]:
    chunk_ids: list[str] = []
    for source in sources:
        raw_source_chunk_ids = source.get("source_chunk_ids")
        if isinstance(raw_source_chunk_ids, list):
            chunk_ids.extend(normalize_id(item) for item in raw_source_chunk_ids)
            continue
        if source.get("chunk_id"):
            chunk_ids.append(normalize_id(source["chunk_id"]))
    return dedupe_preserve_order(chunk_ids)


def calculate_recall_at_k(*, expected_ids: list[str], retrieved_ids: list[str]) -> float:
    if not expected_ids:
        return 1.0
    hits = set(expected_ids).intersection(retrieved_ids)
    return len(hits) / len(set(expected_ids))


def calculate_mrr(*, expected_ids: list[str], retrieved_ids: list[str]) -> float:
    expected = set(expected_ids)
    if not expected:
        return 1.0
    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            return 1.0 / index
    return 0.0


def calculate_ndcg(*, expected_ids: list[str], retrieved_ids: list[str]) -> float:
    expected = set(expected_ids)
    if not expected:
        return 1.0

    dcg = 0.0
    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            dcg += 1.0 / log2(index + 1)

    ideal_hit_count = min(len(expected), len(retrieved_ids))
    if ideal_hit_count == 0:
        return 0.0
    idcg = sum(1.0 / log2(index + 1) for index in range(1, ideal_hit_count + 1))
    return dcg / idcg if idcg else 0.0


def evaluate_retrieval(
    *,
    expected_source_chunk_ids: list[str],
    debug: dict[str, Any],
    k: int,
) -> RetrievalEvalMetrics:
    expected_ids = dedupe_preserve_order([normalize_id(item) for item in expected_source_chunk_ids])
    retrieved_ids = extract_retrieved_chunk_ids(debug, k=k)
    return RetrievalEvalMetrics(
        recall_at_k=calculate_recall_at_k(
            expected_ids=expected_ids,
            retrieved_ids=retrieved_ids,
        ),
        mrr=calculate_mrr(
            expected_ids=expected_ids,
            retrieved_ids=retrieved_ids,
        ),
        ndcg=calculate_ndcg(
            expected_ids=expected_ids,
            retrieved_ids=retrieved_ids,
        ),
        source_hit=bool(set(expected_ids).intersection(retrieved_ids)) if expected_ids else True,
        expected_source_count=len(expected_ids),
        retrieved_source_count=len(retrieved_ids),
    )


def extract_terms(text: str | None) -> list[str]:
    if not text:
        return []
    normalized = text.lower()
    raw_terms = re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]{2,}", normalized)
    return dedupe_preserve_order([item for item in raw_terms if len(item) > 1])


def calculate_answer_relevance(*, expected_answer: str | None, answer: str) -> float:
    expected_terms = extract_terms(expected_answer)
    if not expected_terms:
        return 1.0 if answer.strip() else 0.0
    answer_lower = answer.lower()
    matched = [term for term in expected_terms if term in answer_lower]
    return len(matched) / len(expected_terms)


def calculate_citation_accuracy(
    *,
    expected_source_chunk_ids: list[str],
    sources: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> float:
    if not citations:
        return 1.0 if not expected_source_chunk_ids else 0.0

    source_lookup = {
        normalize_id(source.get("source_id")): set(extract_source_chunk_ids([source]))
        for source in sources
        if source.get("source_id")
    }
    expected = set(normalize_id(item) for item in expected_source_chunk_ids)
    if not expected:
        return 1.0

    valid_count = 0
    for citation in citations:
        source_ids = source_lookup.get(normalize_id(citation.get("source_id")))
        if source_ids and source_ids.intersection(expected):
            valid_count += 1
    return valid_count / len(citations)


def calculate_faithfulness(*, sources: list[dict[str, Any]], citations: list[dict[str, Any]]) -> float:
    if not citations:
        return 0.0 if sources else 1.0
    available_source_ids = {
        normalize_id(source.get("source_id"))
        for source in sources
        if source.get("source_id")
    }
    valid_citations = [
        citation
        for citation in citations
        if normalize_id(citation.get("source_id")) in available_source_ids
        and citation.get("validation_status") != "invalid"
        and citation.get("quote_found") is not False
    ]
    return len(valid_citations) / len(citations)


def calculate_abstention_accuracy(
    *,
    expected_source_chunk_ids: list[str],
    answer: str,
    source_hit: bool,
) -> float:
    no_evidence_expected = not expected_source_chunk_ids
    abstained = any(
        phrase in answer
        for phrase in [
            "没有检索到",
            "证据不足",
            "无法确认",
            "cannot answer",
            "not enough evidence",
        ]
    )
    if no_evidence_expected:
        return 1.0 if abstained or not answer.strip() else 0.0
    return 1.0 if source_hit else 0.0


def evaluate_generation(
    *,
    case: EvalCase,
    prediction: EvalPrediction,
    retrieval: RetrievalEvalMetrics,
) -> GenerationEvalMetrics:
    return GenerationEvalMetrics(
        faithfulness=calculate_faithfulness(
            sources=prediction.sources,
            citations=prediction.citations,
        ),
        citation_accuracy=calculate_citation_accuracy(
            expected_source_chunk_ids=case.expected_source_chunk_ids,
            sources=prediction.sources,
            citations=prediction.citations,
        ),
        answer_relevance=calculate_answer_relevance(
            expected_answer=case.expected_answer,
            answer=prediction.answer,
        ),
        abstention_accuracy=calculate_abstention_accuracy(
            expected_source_chunk_ids=case.expected_source_chunk_ids,
            answer=prediction.answer,
            source_hit=retrieval.source_hit,
        ),
    )


def evaluate_case(
    *,
    case: EvalCase,
    prediction: EvalPrediction,
    k: int = 5,
) -> EvalResult:
    retrieval = evaluate_retrieval(
        expected_source_chunk_ids=case.expected_source_chunk_ids,
        debug=prediction.debug,
        k=k,
    )
    generation = evaluate_generation(
        case=case,
        prediction=prediction,
        retrieval=retrieval,
    )
    engineering = EngineeringEvalMetrics(
        latency_ms=prediction.latency_ms,
        token_cost=prediction.token_cost,
        llm_call_count=prediction.llm_call_count,
        retrieval_count=prediction.retrieval_count,
    )
    return EvalResult(
        case_id=case.case_id,
        question=case.question,
        retrieval=retrieval,
        generation=generation,
        engineering=engineering,
        tags=case.tags,
        difficulty=case.difficulty,
    )


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def summarize_eval_results(results: list[EvalResult]) -> dict[str, float | int]:
    return {
        "case_count": len(results),
        "avg_recall_at_k": average([item.retrieval.recall_at_k for item in results]),
        "avg_mrr": average([item.retrieval.mrr for item in results]),
        "avg_ndcg": average([item.retrieval.ndcg for item in results]),
        "source_hit_rate": average([1.0 if item.retrieval.source_hit else 0.0 for item in results]),
        "avg_faithfulness": average([item.generation.faithfulness for item in results]),
        "avg_citation_accuracy": average([item.generation.citation_accuracy for item in results]),
        "avg_answer_relevance": average([item.generation.answer_relevance for item in results]),
        "avg_abstention_accuracy": average([item.generation.abstention_accuracy for item in results]),
    }


def build_eval_run(
    *,
    dataset: EvalDataset,
    predictions_by_case_id: dict[str, EvalPrediction],
    run_id: str,
    k: int = 5,
) -> EvalRun:
    started_at = datetime.now()
    results = [
        evaluate_case(
            case=case,
            prediction=predictions_by_case_id[case.case_id],
            k=k,
        )
        for case in dataset.cases
        if case.case_id in predictions_by_case_id
    ]
    completed_at = datetime.now()
    return EvalRun(
        run_id=run_id,
        dataset_id=dataset.dataset_id,
        started_at=started_at,
        completed_at=completed_at,
        results=results,
        summary=summarize_eval_results(results),
    )
