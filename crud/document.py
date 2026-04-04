from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.document import Document


async def create_document(
        db: AsyncSession,
        *,
        document_id: str,
        knowledge_base_id: str | None,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int,
        status: str = "uploaded"
) -> Document:
    document = Document(
        id=document_id,
        knowledge_base_id=knowledge_base_id,
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


async def list_documents(db: AsyncSession) -> list[Document]:
    sql = select(Document).order_by(Document.created_at.desc())
    res = await db.execute(sql)
    document_list = list(res.scalars().all())
    return document_list


async def get_document_by_id(db: AsyncSession, document_id: str) -> Document | None:
    sql = select(Document).where(Document.id == document_id)
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

    await db.refresh(doc)
    return doc
