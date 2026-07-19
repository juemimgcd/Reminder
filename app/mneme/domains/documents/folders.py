import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.crud.document import get_document_by_id, move_document_to_folder
from app.mneme.crud.document_folder import (
    descendant_folder_pks,
    folder_has_contents,
    get_folder_by_id,
    get_folder_by_pk,
    list_folders,
)
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.models.document_folder import DocumentFolder
from app.mneme.models.knowledge_base import KnowledgeBase
from app.mneme.models.user import User
from app.mneme.schemas.document import (
    DocumentFolderCreate,
    DocumentFolderItem,
    DocumentFolderUpdate,
    DocumentMoveRequest,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/kb/document-folders", tags=["document-folders"])


def normalize_folder_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def validate_folder_move(*, folder_pk: int, new_parent_pk: int, descendant_pks: set[int]):
    if folder_pk == new_parent_pk or new_parent_pk in descendant_pks:
        raise BusinessException(
            "folder cannot be moved beneath itself or a descendant",
            code=4025,
        )


def _display_folder_name(value: str) -> str:
    display_name = " ".join(value.strip().split())
    if not display_name:
        raise BusinessException("folder name cannot be empty", code=4024)
    return display_name


async def _owned_knowledge_base(
    db: AsyncSession,
    *,
    knowledge_base_id: str,
    user_id: int,
) -> KnowledgeBase:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if knowledge_base is None:
        raise BusinessException("knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != user_id:
        raise BusinessException(
            "knowledge base does not belong to current user",
            code=4007,
            status_code=403,
        )
    return knowledge_base


def _folder_item(folder: DocumentFolder, *, parent_id: str) -> DocumentFolderItem:
    return DocumentFolderItem(
        id=folder.id,
        parent_id=parent_id,
        name=folder.name,
        is_root=folder.is_root,
    )


def _build_folder_tree(folders: list[DocumentFolder]) -> list[DocumentFolderItem]:
    folders_by_pk = {folder.pk: folder for folder in folders}
    items_by_pk = {
        folder.pk: _folder_item(
            folder,
            parent_id=folders_by_pk.get(folder.parent_pk, folder).id,
        )
        for folder in folders
    }
    roots: list[DocumentFolderItem] = []
    for folder in folders:
        if folder.is_root:
            continue
        parent = folders_by_pk.get(folder.parent_pk)
        if parent is not None and not parent.is_root:
            items_by_pk[parent.pk].children.append(items_by_pk[folder.pk])
        else:
            roots.append(items_by_pk[folder.pk])
    return roots


async def _flush_or_duplicate(db: AsyncSession) -> None:
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise BusinessException(
            "folder name already exists",
            code=4026,
            status_code=409,
        ) from exc


@router.get("")
async def get_folder_tree_api(
    knowledge_base_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    knowledge_base = await _owned_knowledge_base(
        db,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )
    folders = await list_folders(
        db,
        knowledge_base_pk=knowledge_base.pk,
        user_id=current_user.id,
    )
    return success_response(data=_build_folder_tree(folders))


@router.post("")
async def create_folder_api(
    payload: DocumentFolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    knowledge_base = await _owned_knowledge_base(
        db,
        knowledge_base_id=payload.knowledge_base_id,
        user_id=current_user.id,
    )
    parent = await get_folder_by_id(
        db,
        folder_id=payload.parent_id,
        user_id=current_user.id,
    )
    if parent is None or parent.knowledge_base_pk != knowledge_base.pk:
        raise BusinessException("parent folder not found in knowledge base", code=4045, status_code=404)
    display_name = _display_folder_name(payload.name)
    created = DocumentFolder(
        id=f"fld_{uuid.uuid4().hex[:24]}",
        user_id=current_user.id,
        knowledge_base_id=knowledge_base.id,
        knowledge_base_pk=knowledge_base.pk,
        parent_pk=parent.pk,
        name=display_name,
        normalized_name=normalize_folder_name(display_name),
        is_root=False,
    )
    db.add(created)
    await _flush_or_duplicate(db)
    return success_response(
        data=_folder_item(created, parent_id=parent.id),
        message="folder created",
    )


@router.patch("/{folder_id}")
async def update_folder_api(
    folder_id: str,
    payload: DocumentFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    target = await get_folder_by_id(db, folder_id=folder_id, user_id=current_user.id)
    if target is None:
        raise BusinessException("folder not found", code=4045, status_code=404)
    if target.is_root:
        raise BusinessException("root folder cannot be renamed or moved", code=4027)

    parent = None
    if payload.parent_id is not None:
        parent = await get_folder_by_id(
            db,
            folder_id=payload.parent_id,
            user_id=current_user.id,
        )
        if parent is None:
            raise BusinessException("parent folder not found", code=4045, status_code=404)
        if parent.knowledge_base_pk != target.knowledge_base_pk:
            raise BusinessException("folder cannot move across knowledge bases", code=4028)
        descendants = await descendant_folder_pks(db, folder_pk=target.pk)
        validate_folder_move(
            folder_pk=target.pk,
            new_parent_pk=parent.pk,
            descendant_pks=descendants,
        )
        target.parent_pk = parent.pk

    if payload.name is not None:
        display_name = _display_folder_name(payload.name)
        target.name = display_name
        target.normalized_name = normalize_folder_name(display_name)

    await _flush_or_duplicate(db)
    if parent is None:
        parent = await get_folder_by_pk(
            db,
            folder_pk=target.parent_pk,
            user_id=current_user.id,
        )
        if parent is None:
            raise BusinessException("parent folder integrity error", code=5004, status_code=409)
    parent_id = parent.id
    return success_response(
        data=_folder_item(target, parent_id=parent_id),
        message="folder updated",
    )


@router.delete("/{folder_id}")
async def delete_folder_api(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    target = await get_folder_by_id(db, folder_id=folder_id, user_id=current_user.id)
    if target is None:
        raise BusinessException("folder not found", code=4045, status_code=404)
    if target.is_root:
        raise BusinessException("root folder cannot be deleted", code=4027)
    if await folder_has_contents(db, folder_pk=target.pk):
        raise BusinessException("folder is not empty", code=4029)
    await db.delete(target)
    await db.flush()
    return success_response(data={"id": target.id}, message="folder deleted")


@router.post("/documents/{document_id}/move")
async def move_document_api(
    document_id: str,
    payload: DocumentMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    document = await get_document_by_id(db, document_id, user_id=current_user.id)
    if document is None:
        raise BusinessException("document not found", code=4044, status_code=404)
    destination = await get_folder_by_id(
        db,
        folder_id=payload.folder_id,
        user_id=current_user.id,
    )
    if destination is None:
        raise BusinessException("folder not found", code=4045, status_code=404)
    if destination.knowledge_base_pk != document.knowledge_base_pk:
        raise BusinessException("document cannot move across knowledge bases", code=4030)
    await move_document_to_folder(db, document=document, folder_pk=destination.pk)
    return success_response(
        data={"document_id": document.id, "folder_id": destination.id},
        message="document moved",
    )
