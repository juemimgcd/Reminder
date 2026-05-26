import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.services.task_state_service import (
    ACTIVE_TASK_STATUSES,
    CANCELLED,
    FAILED,
    PENDING,
    RETRYING,
    RUNNING,
    SUCCEEDED,
    is_active_task_status,
    normalize_task_status,
    resolve_task_transition,
)


def show_transition(current_status: str, requested_status: str) -> None:
    next_status, progress_stage = resolve_task_transition(
        current_status=current_status,
        requested_status=requested_status,
    )
    print(
        f"{current_status}->{requested_status}: status={next_status} progress_stage={progress_stage}",
        flush=True,
    )


def main() -> None:
    print("Start Day 16 TaskRecord lifecycle debug script...", flush=True)
    print(f"active_statuses={sorted(ACTIVE_TASK_STATUSES)}", flush=True)
    print(f"legacy_queued={normalize_task_status('queued')}", flush=True)
    print(f"legacy_completed={normalize_task_status('completed')}", flush=True)
    print(f"legacy_canceled={normalize_task_status('canceled')}", flush=True)

    show_transition(PENDING, "parsing")
    show_transition(RUNNING, "chunking")
    show_transition(RUNNING, SUCCEEDED)
    show_transition(FAILED, RETRYING)
    show_transition(RETRYING, PENDING)
    show_transition(PENDING, CANCELLED)

    print(f"is_pending_active={is_active_task_status(PENDING)}", flush=True)
    print(f"is_running_active={is_active_task_status(RUNNING)}", flush=True)
    print(f"is_retrying_active={is_active_task_status(RETRYING)}", flush=True)
    print(f"is_succeeded_active={is_active_task_status(SUCCEEDED)}", flush=True)

    try:
        resolve_task_transition(current_status=SUCCEEDED, requested_status=FAILED)
    except Exception as exc:
        print(f"illegal_transition_error={type(exc).__name__}", flush=True)


if __name__ == "__main__":
    main()
