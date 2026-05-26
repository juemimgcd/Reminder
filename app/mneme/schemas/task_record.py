from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskRecordData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    target_id: str
    status: str
    progress_stage: str | None = None
    queue_name: str | None = None
    celery_task_id: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    result_summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskActionData(BaseModel):
    task_id: str
    status: str
    document_id: str | None = None
    message: str
