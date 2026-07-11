from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.mneme.models.document import Document


async def create_document(
        db: AsyncSession,
        *,
        document_id: str,
        user_id: int,
        knowledge_base_id: str,
        knowledge_base_pk: int,
        folder_pk: int,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int,
        status: str = "uploaded"
) -> Document:
    document = Document(
        id=document_id,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        knowledge_base_pk=knowledge_base_pk,
        folder_pk=folder_pk,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        status=status
    )

    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


async def list_documents(
        db: AsyncSession,
        *,
        user_id: int | None = None,
        knowledge_base_pk: int | None = None,
) -> list[Document]:
    sql = select(Document)

    if user_id:
        sql = sql.where(Document.user_id == user_id)

    if knowledge_base_pk:
        sql = sql.where(Document.knowledge_base_pk == knowledge_base_pk)

    sql = sql.order_by(Document.created_at.desc())
    res = await db.execute(sql)
    document_list = list(res.scalars().all())
    return document_list


async def get_document_by_id(
        db: AsyncSession,
        document_id: str,
        *,
        user_id: int | None = None,
        knowledge_base_pk: int | None = None,
) -> Document | None:
    sql = select(Document).where(Document.id == document_id)

    if user_id:
        sql = sql.where(Document.user_id == user_id)

    if knowledge_base_pk:
        sql = sql.where(Document.knowledge_base_pk == knowledge_base_pk)

    res = await db.execute(sql)
    document = res.scalar_one_or_none()
    return document


async def update_document_status(
        db: AsyncSession,
        *,
        document_id: str,
        status: str,
):

    sql = select(Document).where(Document.id == document_id)
    res = await db.execute(sql)

    doc = res.scalar_one_or_none()
    if not doc:
        return None

    doc.status = status
    await db.flush()
    await db.refresh(doc)
    return doc


async def delete_document_by_id(
        db: AsyncSession,
        *,
        document_id: str,
) -> int:
    sql = delete(Document).where(Document.id == document_id)
    res = await db.execute(sql)
    return res.rowcount or 0
