from collections import defaultdict

from app.mneme.memoria.server.multi_agent.contracts import (
    DroppedEvidence,
    EvidenceBundle,
    EvidenceConflict,
    JudgedEvidenceSet,
)


class EvidenceJudge:
    """Deterministic relevance, deduplication, conflict, and budget boundary."""

    def judge(
        self,
        bundles: list[EvidenceBundle],
        *,
        selected_sources: list[str],
        final_top_k: int,
    ) -> JudgedEvidenceSet:
        candidates = [item for bundle in bundles for item in bundle.evidence]
        by_id = {}
        dropped: list[DroppedEvidence] = []
        for item in candidates:
            previous = by_id.get(item.evidence_id)
            if previous is None or item.score > previous.score:
                if previous is not None:
                    dropped.append(
                        DroppedEvidence(
                            evidence_id=previous.evidence_id,
                            reason_code="duplicate",
                        )
                    )
                by_id[item.evidence_id] = item
            else:
                dropped.append(
                    DroppedEvidence(
                        evidence_id=item.evidence_id,
                        reason_code="duplicate",
                    )
                )

        ranked = sorted(
            by_id.values(),
            key=lambda item: (-item.score, item.source_type, item.evidence_id),
        )
        kept = ranked[:final_top_k]
        dropped.extend(
            DroppedEvidence(evidence_id=item.evidence_id, reason_code="budget")
            for item in ranked[final_top_k:]
        )

        variants = defaultdict(list)
        for item in by_id.values():
            variants[(item.source_type, item.source_id)].append(item)
        conflicts = [
            EvidenceConflict(
                source_type=source_type,
                source_id=source_id,
                evidence_ids=sorted(item.evidence_id for item in items),
            )
            for (source_type, source_id), items in variants.items()
            if len({item.content.strip() for item in items}) > 1
        ]

        present = {bundle.source_type for bundle in bundles if bundle.evidence}
        missing = [source for source in selected_sources if source not in present]
        coverage = len(present) / len(selected_sources) if selected_sources else 1.0
        uncertainty = []
        if missing:
            uncertainty.append(f"missing_sources:{','.join(missing)}")
        if conflicts:
            uncertainty.append(f"evidence_conflicts:{len(conflicts)}")
        if not kept:
            uncertainty.append("no_judged_evidence")
        return JudgedEvidenceSet(
            evidence=kept,
            kept_evidence_ids=[item.evidence_id for item in kept],
            dropped=dropped,
            conflicts=conflicts,
            coverage=coverage,
            missing_sources=missing,
            uncertainty=uncertainty,
            needs_supplemental=bool(missing) and coverage < 1.0,
        )
