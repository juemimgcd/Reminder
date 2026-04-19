from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskRecordData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    target_id: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskActionData(BaseModel):
    task_id: str
    status: str
    document_id: str | None = None
    message: str
