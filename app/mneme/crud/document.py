from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.mneme.models.document import Document
from app.mneme.models.document_folder import DocumentFolder


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
        status: str = "uploaded",
        content_sha256: str | None = None,
        normalized_file_name: str = "",
        version_group_id: str = "",
        version_number: int = 1,
        previous_document_id: str | None = None,
        duplicate_of_document_id: str | None = None,
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
        status=status,
        content_sha256=content_sha256,
        normalized_file_name=normalized_file_name,
        version_group_id=version_group_id,
        version_number=version_number,
        previous_document_id=previous_document_id,
        duplicate_of_document_id=duplicate_of_document_id,
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
    return list(res.scalars().all())


async def list_document_workspace_rows(
        db: AsyncSession,
        *,
        user_id: int | None = None,
        knowledge_base_pk: int | None = None,
) -> list[tuple[Document, str]]:
    sql = select(Document, DocumentFolder.id).join(
        DocumentFolder,
        and_(
            Document.folder_pk == DocumentFolder.pk,
            Document.user_id == DocumentFolder.user_id,
            Document.knowledge_base_pk == DocumentFolder.knowledge_base_pk,
        ),
    )

    if user_id:
        sql = sql.where(Document.user_id == user_id)

    if knowledge_base_pk:
        sql = sql.where(Document.knowledge_base_pk == knowledge_base_pk)

    sql = sql.order_by(Document.created_at.desc())
    res = await db.execute(sql)
    return [(document, folder_id) for document, folder_id in res.all()]


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


async def move_document_to_folder(
        db: AsyncSession,
        *,
        document: Document,
        folder_pk: int,
) -> Document:
    document.folder_pk = folder_pk
    await db.flush()
    return document


async def find_canonical_by_hash(
        db: AsyncSession,
        *,
        knowledge_base_pk: int,
        content_sha256: str,
) -> Document | None:
    return await db.scalar(
        select(Document)
        .where(
            Document.knowledge_base_pk == knowledge_base_pk,
            Document.content_sha256 == content_sha256,
            Document.duplicate_of_document_id.is_(None),
        )
        .order_by(Document.pk.asc())
        .limit(1)
    )


async def find_latest_version(
        db: AsyncSession,
        *,
        knowledge_base_pk: int,
        folder_pk: int,
        normalized_file_name: str,
) -> Document | None:
    return await db.scalar(
        select(Document)
        .where(
            Document.knowledge_base_pk == knowledge_base_pk,
            Document.folder_pk == folder_pk,
            Document.normalized_file_name == normalized_file_name,
        )
        .order_by(Document.version_number.desc(), Document.pk.desc())
        .limit(1)
    )


async def list_unhashed_documents(
        db: AsyncSession,
        *,
        after_pk: int = 0,
        limit: int = 100,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.pk > after_pk, Document.content_sha256.is_(None))
        .order_by(Document.pk.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
