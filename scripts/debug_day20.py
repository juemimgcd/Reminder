import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.services.production_readiness_service import (
    AVOID_BY_DEFAULT,
    DEFAULT_STACK,
    OPTIONAL_STACK,
    build_production_readiness_report,
)


def main() -> None:
    print("Start Day 20 Production Readiness debug script...", flush=True)
    report = build_production_readiness_report()
    status_counts: dict[str, int] = {}
    for check in report.checks:
        status_counts[check.status] = status_counts.get(check.status, 0) + 1

    print(f"overall_status={report.overall_status}", flush=True)
    print(f"check_count={len(report.checks)}", flush=True)
    print(f"status_counts={status_counts}", flush=True)
    print(f"framework_decision_count={len(report.framework_decisions)}", flush=True)
    print(f"default_stack_count={len(DEFAULT_STACK)}", flush=True)
    print(f"optional_stack_count={len(OPTIONAL_STACK)}", flush=True)
    print(f"avoid_by_default_count={len(AVOID_BY_DEFAULT)}", flush=True)
    print(f"has_llamaindex_optional={any(item.area == 'document_ingestion' and item.decision == 'optional_poc' for item in report.framework_decisions)}", flush=True)
    print(f"has_duckdb_avoid={any(item.area == 'analytics_store' and item.decision == 'avoid_by_default' for item in report.framework_decisions)}", flush=True)
    print(f"markdown_has_framework={'Framework Decisions' in report.markdown}", flush=True)


if __name__ == "__main__":
    main()
