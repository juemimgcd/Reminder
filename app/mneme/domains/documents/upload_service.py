from __future__ import annotations

import hashlib
import os
from pathlib import Path
import unicodedata
import uuid

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.crud.document import (
    create_document,
    find_canonical_by_hash,
    find_latest_version,
)
from app.mneme.crud.document_folder import get_folder_by_pk
from app.mneme.models.document import Document
from app.mneme.models.document_folder import DocumentFolder
from app.mneme.models.knowledge_base import KnowledgeBase
from app.mneme.models.user import User
from app.mneme.schemas.document import DocumentUploadData
from app.mneme.utils.exceptions import BusinessException


CHUNK_SIZE = 1024 * 1024


def normalize_file_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value.strip()).casefold()


def next_version(*, latest_id: str, latest_version: int, group_id: str) -> dict[str, str | int]:
    return {
        "version_group_id": group_id,
        "version_number": latest_version + 1,
        "previous_document_id": latest_id,
    }


async def stream_upload_to_temp(file: UploadFile, temp_path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with temp_path.open("wb") as target:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > settings.MAX_FILE_SIZE:
                raise BusinessException(
                    f"The uploaded size of the file must be less than {settings.MAX_FILE_SIZE}"
                )
            digest.update(chunk)
            target.write(chunk)
    if size == 0:
        raise BusinessException(message="uploaded file cannot be empty", code=4003)
    return digest.hexdigest(), size


def _unlink_owned(path: Path | None) -> None:
    if path is not None:
        path.unlink(missing_ok=True)


async def _folder_path(db: AsyncSession, *, folder_pk: int, user_id: int) -> tuple[str, list[str]]:
    names: list[str] = []
    seen: set[int] = set()
    current_pk = folder_pk
    public_id = ""
    while current_pk not in seen:
        seen.add(current_pk)
        folder = await get_folder_by_pk(db, folder_pk=current_pk, user_id=user_id)
        if folder is None:
            break
        if not public_id:
            public_id = folder.id
        if not folder.is_root:
            names.append(folder.name)
        if folder.parent_pk == folder.pk:
            break
        current_pk = folder.parent_pk
    names.reverse()
    return public_id, names


async def _upload_data(
    db: AsyncSession,
    *,
    document: Document,
    disposition: str,
) -> DocumentUploadData:
    folder_id, folder_path = await _folder_path(
        db,
        folder_pk=document.folder_pk,
        user_id=document.user_id,
    )
    return DocumentUploadData(
        disposition=disposition,
        document_id=document.id,
        canonical_document_id=document.id,
        user_id=document.user_id,
        knowledge_base_id=document.knowledge_base_id,
        folder_id=folder_id,
        folder_path=folder_path,
        file_name=document.file_name,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status,
        version_group_id=document.version_group_id or document.id,
        version_number=document.version_number,
    )


def _validate_destination(*, current_user: User, knowledge_base: KnowledgeBase, folder: DocumentFolder) -> None:
    if folder.user_id != current_user.id or knowledge_base.user_id != current_user.id:
        raise BusinessException("upload destination does not belong to current user", code=4007, status_code=403)
    if folder.knowledge_base_pk != knowledge_base.pk:
        raise BusinessException("folder does not belong to knowledge base", code=4030)


async def store_uploaded_document(
    db: AsyncSession,
    *,
    file: UploadFile,
    current_user: User,
    knowledge_base: KnowledgeBase,
    folder: DocumentFolder,
) -> DocumentUploadData:
    _validate_destination(current_user=current_user, knowledge_base=knowledge_base, folder=folder)
    if not file.filename:
        raise BusinessException(message="uploaded file name cannot be empty", code=4001)
    file_name = Path(file.filename.strip()).name
    file_ext = Path(file_name).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise BusinessException(message=f"unsupported file type, allowed: {allowed}")

    raw_dir = settings.RAW_FILE_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    request_id = uuid.uuid4().hex
    document_id = f"doc_{request_id[:24]}"
    temp_path = raw_dir / f".upload-{request_id}.tmp"
    safe_name = file_name.replace(" ", "_")
    final_path = raw_dir / f"{document_id}__{safe_name}"
    moved = False
    try:
        digest, file_size = await stream_upload_to_temp(file, temp_path)
        canonical = await find_canonical_by_hash(
            db,
            knowledge_base_pk=knowledge_base.pk,
            content_sha256=digest,
        )
        if canonical is not None:
            _unlink_owned(temp_path)
            return await _upload_data(db, document=canonical, disposition="duplicate")

        normalized_name = normalize_file_name(file_name)
        latest = await find_latest_version(
            db,
            knowledge_base_pk=knowledge_base.pk,
            folder_pk=folder.pk,
            normalized_file_name=normalized_name,
        )
        version = (
            next_version(
                latest_id=latest.id,
                latest_version=latest.version_number,
                group_id=latest.version_group_id or latest.id,
            )
            if latest is not None
            else {
                "version_group_id": document_id,
                "version_number": 1,
                "previous_document_id": None,
            }
        )
        os.replace(temp_path, final_path)
        moved = True
        try:
            async with db.begin_nested():
                document = await create_document(
                    db,
                    document_id=document_id,
                    user_id=current_user.id,
                    knowledge_base_id=knowledge_base.id,
                    knowledge_base_pk=knowledge_base.pk,
                    folder_pk=folder.pk,
                    file_name=file_name,
                    file_path=str(final_path),
                    file_type=file_ext.lstrip("."),
                    file_size=file_size,
                    status="uploaded",
                    content_sha256=digest,
                    normalized_file_name=normalized_name,
                    **version,
                )
        except IntegrityError:
            _unlink_owned(final_path)
            moved = False
            canonical = await find_canonical_by_hash(
                db,
                knowledge_base_pk=knowledge_base.pk,
                content_sha256=digest,
            )
            if canonical is None:
                raise
            return await _upload_data(db, document=canonical, disposition="duplicate")
        return await _upload_data(db, document=document, disposition="created")
    except Exception:
        _unlink_owned(temp_path)
        if moved:
            _unlink_owned(final_path)
        raise
