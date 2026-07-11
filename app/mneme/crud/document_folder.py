import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.document_folder import DocumentFolder


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
