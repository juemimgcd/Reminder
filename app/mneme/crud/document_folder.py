import uuid

from sqlalchemy import exists, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.mneme.models.document import Document
from app.mneme.models.document_folder import DocumentFolder
from app.mneme.utils.exceptions import BusinessException


async def ensure_root_folder(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str,
    knowledge_base_pk: int,
) -> DocumentFolder:
    existing = await db.scalar(
        select(DocumentFolder).where(
            DocumentFolder.knowledge_base_pk == knowledge_base_pk,
            DocumentFolder.is_root.is_(True),
        )
    )
    if existing is not None:
        return existing
    try:
        async with db.begin_nested():
            root = DocumentFolder(
                id=f"fld_root_{uuid.uuid4().hex[:24]}",
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                knowledge_base_pk=knowledge_base_pk,
                parent_pk=0,
                name="/",
                normalized_name="/",
                is_root=True,
            )
            db.add(root)
            await db.flush()
            root.parent_pk = root.pk
            await db.flush()
            return root
    except IntegrityError:
        winner = await db.scalar(
            select(DocumentFolder).where(
                DocumentFolder.knowledge_base_pk == knowledge_base_pk,
                DocumentFolder.is_root.is_(True),
            )
        )
        if winner is None:
            raise
        return winner


async def get_folder_by_id(
    db: AsyncSession,
    *,
    folder_id: str,
    user_id: int,
) -> DocumentFolder | None:
    return await db.scalar(
        select(DocumentFolder).where(
            DocumentFolder.id == folder_id,
            DocumentFolder.user_id == user_id,
        )
    )


async def get_folder_by_pk(
    db: AsyncSession,
    *,
    folder_pk: int,
    user_id: int,
) -> DocumentFolder | None:
    return await db.scalar(
        select(DocumentFolder).where(
            DocumentFolder.pk == folder_pk,
            DocumentFolder.user_id == user_id,
        )
    )


async def get_root_folder(
    db: AsyncSession,
    *,
    knowledge_base_pk: int,
    user_id: int,
) -> DocumentFolder:
    root = await db.scalar(
        select(DocumentFolder).where(
            DocumentFolder.knowledge_base_pk == knowledge_base_pk,
            DocumentFolder.user_id == user_id,
            DocumentFolder.is_root.is_(True),
        )
    )
    if root is None:
        raise BusinessException(
            message="knowledge base root folder integrity error",
            code=5004,
            status_code=409,
        )
    return root


async def list_folders(
    db: AsyncSession,
    *,
    knowledge_base_pk: int,
    user_id: int,
) -> list[DocumentFolder]:
    tree = (
        select(
            DocumentFolder.pk.label("pk"),
            literal(0).label("depth"),
        )
        .where(
            DocumentFolder.knowledge_base_pk == knowledge_base_pk,
            DocumentFolder.user_id == user_id,
            DocumentFolder.is_root.is_(True),
        )
        .cte("folder_tree", recursive=True)
    )
    child = aliased(DocumentFolder)
    tree = tree.union_all(
        select(child.pk, (tree.c.depth + 1).label("depth"))
        .join(tree, child.parent_pk == tree.c.pk)
        .where(child.pk != child.parent_pk)
    )
    result = await db.execute(
        select(DocumentFolder)
        .join(tree, DocumentFolder.pk == tree.c.pk)
        .order_by(tree.c.depth.asc(), DocumentFolder.pk.asc())
    )
    return list(result.scalars().all())


async def descendant_folder_pks(
    db: AsyncSession,
    *,
    folder_pk: int,
) -> set[int]:
    descendants = (
        select(DocumentFolder.pk.label("pk"))
        .where(
            DocumentFolder.parent_pk == folder_pk,
            DocumentFolder.pk != folder_pk,
        )
        .cte("folder_descendants", recursive=True)
    )
    child = aliased(DocumentFolder)
    descendants = descendants.union_all(
        select(child.pk).join(descendants, child.parent_pk == descendants.c.pk)
    )
    result = await db.execute(select(descendants.c.pk))
    return set(result.scalars().all())


async def folder_has_contents(
    db: AsyncSession,
    *,
    folder_pk: int,
) -> bool:
    document_exists = await db.scalar(
        select(exists().where(Document.folder_pk == folder_pk))
    )
    if document_exists:
        return True
    return bool(
        await db.scalar(
            select(
                exists().where(
                    DocumentFolder.parent_pk == folder_pk,
                    DocumentFolder.pk != folder_pk,
                )
            )
        )
    )
