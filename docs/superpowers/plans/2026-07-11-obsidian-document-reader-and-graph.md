# Obsidian Document Reader, Folders, Deduplication, and Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Obsidian-style document workspace with nested folders, full-content reading, exact-content deduplication, same-name version chains, and a quieter Obsidian Classic graph that opens documents through the same reader.

**Architecture:** Extend the PostgreSQL document model with root-backed folder metadata, content hashes, canonical duplicate markers, and version lineage. Keep document storage ID-based, expose authenticated content/raw/folder APIs, and route every frontend file-opening surface through one lazy document-workspace state. Preserve the existing single D3 simulation while adding degree-aware layout, deterministic label disclosure, and selected-neighborhood focus.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, PostgreSQL 17, Alembic, MarkItDown, Vue 3.5, TypeScript 5.8, D3 7.9, `marked`, DOMPurify, Playwright 1.60, Docker Compose

## Global Constraints

- Preserve all existing `mneme_*` production volumes; never run `docker compose down -v`.
- Keep raw storage document-ID based; never construct server paths from folder or uploaded file names.
- Deduplicate exact SHA-256 content across one knowledge base, not across users or knowledge bases.
- Version grouping is case-insensitive and scoped to one folder plus normalized file name.
- Existing exact duplicates remain readable and are marked as duplicates during backfill; no legacy document rows are deleted.
- Complete document content is lazy-loaded and must not add requests to login or initial workspace startup.
- Uploaded HTML and rendered Markdown must not execute scripts, event attributes, executable URLs, or untrusted embeds.
- Every folder, document content, raw file, move, and version operation validates current-user ownership.
- Non-empty folders cannot be deleted, and folders cannot be moved beneath themselves or descendants.
- Reuse the existing D3 dependency and maintain exactly one simulation per mounted graph.
- Graph positions publish at most once per animation frame; hidden tabs pause; converged simulations stop; reduced motion remains synchronous.
- Preserve authentication, GraphRAG, zoom, filters, drag, restart, settings, localization, and current responsive shell behavior.
- Every UI data surface has loading, empty, error, hover, focus-visible, disabled, and pending states.

---

## File Structure

### Backend

- `app/mneme/models/document_folder.py`: folder persistence model only.
- `app/mneme/models/document.py`: document folder, hash, canonical duplicate, and version fields.
- `app/mneme/crud/document_folder.py`: folder and tree database queries.
- `app/mneme/crud/document.py`: document hash/version/canonical queries in addition to existing document access.
- `app/mneme/domains/documents/folders.py`: authenticated folder HTTP routes.
- `app/mneme/domains/documents/upload_service.py`: streaming upload, SHA-256, deduplication, and version resolution.
- `app/mneme/domains/documents/content_service.py`: safe complete-content conversion and raw-file metadata.
- `app/mneme/domains/documents/router.py`: thin document HTTP routes delegating to the focused services.
- `app/mneme/schemas/document.py`: folder, upload disposition, version, and content response schemas.
- `alembic/versions/20260711_01_add_document_workspace.py`: merge-head schema migration and root-folder/legacy metadata backfill.
- `scripts/backfill_document_hashes.py`: controlled file-system hash backfill and legacy canonical selection.

### Frontend

- `app/mneme_frontend_v0.2.1/src/composables/useDocumentWorkspace.ts`: tabs, active document, tree, content cache, Blob lifecycle, and folder mutations.
- `app/mneme_frontend_v0.2.1/src/components/documents/DocumentTree.vue`: accessible nested tree and move controls.
- `app/mneme_frontend_v0.2.1/src/components/documents/DocumentReader.vue`: reader shell, tabs, body, and status states.
- `app/mneme_frontend_v0.2.1/src/components/documents/DocumentContent.vue`: sanitized Markdown/text/Office/PDF rendering.
- `app/mneme_frontend_v0.2.1/src/components/documents/DocumentProperties.vue`: metadata, versions, memories, and backlinks.
- `app/mneme_frontend_v0.2.1/src/views/VaultView.vue`: compose the three-pane reader instead of inert document rows.
- `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`: focused neighborhood, label disclosure, and unified document open.
- `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`: degree-aware force and focus state.
- `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`: expose the document workspace and invalidate notes/graph after mutations.
- `app/mneme_frontend_v0.2.1/src/lib/api.ts`: real folder/content/raw/move/version API calls.
- `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`: deterministic preview equivalents for visual and browser tests.
- `app/mneme_frontend_v0.2.1/src/types.ts`: shared API and reader types.

---

### Task 1: Add folder, hash, canonical duplicate, and version persistence

**Files:**
- Create: `app/mneme/models/document_folder.py`
- Modify: `app/mneme/models/document.py`
- Modify: `app/mneme/models/__init__.py`
- Create: `app/mneme/crud/document_folder.py`
- Modify: `app/mneme/crud/document.py`
- Modify: `app/mneme/crud/knowledge_base.py`
- Modify: `app/mneme/domains/documents/router.py`
- Create: `alembic/versions/20260711_01_add_document_workspace.py`
- Create: `tests/test_document_workspace_schema.py`
- Modify: `tests/test_documents_domain_convergence.py`

**Interfaces:**
- Produces: `DocumentFolder`, `Document.folder_pk`, `content_sha256`, `normalized_file_name`, `version_group_id`, `version_number`, `previous_document_id`, and `duplicate_of_document_id`.
- Migration revision: `20260711_01`, with both current heads `20260526_03` and `20260707_02` as `down_revision`.

- [ ] **Step 1: Write the failing schema contract**

```python
# tests/test_document_workspace_schema.py
from pathlib import Path

from app.mneme.models.document import Document
from app.mneme.models.document_folder import DocumentFolder


def test_document_workspace_models_expose_folder_hash_and_version_fields():
    assert DocumentFolder.__tablename__ == "document_folders"
    for name in {
        "folder_pk", "content_sha256", "normalized_file_name",
        "version_group_id", "version_number", "previous_document_id",
        "duplicate_of_document_id",
    }:
        assert hasattr(Document, name)


def test_workspace_migration_merges_heads_and_defines_canonical_hash_index():
    source = Path("alembic/versions/20260711_01_add_document_workspace.py").read_text("utf-8")
    assert 'down_revision = ("20260526_03", "20260707_02")' in source
    assert "uq_documents_kb_canonical_sha256" in source
    assert "duplicate_of_document_id IS NULL" in source
```

- [ ] **Step 2: Run the contract and verify RED**

Run:

```powershell
python -m pytest tests/test_document_workspace_schema.py -q -p no:cacheprovider
```

Expected: collection fails because `app.mneme.models.document_folder` and the migration do not exist.

- [ ] **Step 3: Add the folder model and document fields**

```python
# app/mneme/models/document_folder.py
from sqlalchemy import BigInteger, Boolean, ForeignKey, Identity, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.mneme.models.base import Base


class DocumentFolder(Base):
    __tablename__ = "document_folders"
    __table_args__ = (
        UniqueConstraint("knowledge_base_pk", "parent_pk", "normalized_name", name="uq_document_folders_parent_name"),
        Index("idx_document_folders_kb_parent", "knowledge_base_pk", "parent_pk"),
        Index("uq_document_folders_kb_root", "knowledge_base_pk", unique=True, postgresql_where=text("is_root")),
    )

    pk: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_base_pk: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_bases.pk"), nullable=False)
    parent_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_folders.pk", deferrable=True, initially="DEFERRED"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

Add the following columns to `Document` and import/export `DocumentFolder` from `app/mneme/models/__init__.py`:

```python
folder_pk: Mapped[int] = mapped_column(BigInteger, ForeignKey("document_folders.pk"), nullable=False)
content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
normalized_file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
version_group_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
previous_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
duplicate_of_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Import `text` in `document.py` and extend `Document.__table_args__` with the same canonical constraint used by the migration:

```python
Index(
    "uq_documents_kb_canonical_sha256",
    "knowledge_base_pk",
    "content_sha256",
    unique=True,
    postgresql_where=text("content_sha256 IS NOT NULL AND duplicate_of_document_id IS NULL"),
),
```

Create the compatibility helper before making `folder_pk` mandatory:

```python
# app/mneme/crud/document_folder.py
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
```

The self-reference foreign key is deferrable, so the temporary `parent_pk=0` is corrected before transaction commit. Call `ensure_root_folder` from both `create_knowledge_base` and `get_or_create_default_knowledge_base`. Update the existing upload route to resolve the requested knowledge base's root folder and pass `folder_pk=root.pk` into the extended `create_document` function. This keeps all pre-folder upload tests working immediately after Task 1.

- [ ] **Step 4: Create the merge-head migration**

The migration must:

```python
revision = "20260711_01"
down_revision = ("20260526_03", "20260707_02")

def upgrade():
    op.create_table(
        "document_folders",
        sa.Column("pk", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("knowledge_base_id", sa.String(64), nullable=False),
        sa.Column("knowledge_base_pk", sa.BigInteger(), sa.ForeignKey("knowledge_bases.pk"), nullable=False),
        sa.Column(
            "parent_pk",
            sa.BigInteger(),
            sa.ForeignKey("document_folders.pk", deferrable=True, initially="DEFERRED"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("is_root", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("knowledge_base_pk", "parent_pk", "normalized_name", name="uq_document_folders_parent_name"),
    )
    op.create_index("idx_document_folders_kb_parent", "document_folders", ["knowledge_base_pk", "parent_pk"])
    op.create_index(
        "uq_document_folders_kb_root", "document_folders", ["knowledge_base_pk"], unique=True,
        postgresql_where=sa.text("is_root"),
    )
    op.add_column("documents", sa.Column("folder_pk", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("content_sha256", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("normalized_file_name", sa.String(255), nullable=False, server_default=""))
    op.add_column("documents", sa.Column("version_group_id", sa.String(64), nullable=False, server_default=""))
    op.add_column("documents", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("previous_document_id", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("duplicate_of_document_id", sa.String(64), nullable=True))
    op.create_foreign_key("fk_documents_folder_pk", "documents", "document_folders", ["folder_pk"], ["pk"])
    op.execute(sa.text("""
        INSERT INTO document_folders
            (id, user_id, knowledge_base_id, knowledge_base_pk, parent_pk, name, normalized_name, is_root)
        SELECT
            'fld_root_' || substr(md5(id), 1, 24), user_id, id, pk, NULL, '/', '/', TRUE
        FROM knowledge_bases
    """))
    op.execute(sa.text("UPDATE document_folders SET parent_pk = pk WHERE is_root"))
    op.execute(sa.text("""
        UPDATE documents AS d
        SET folder_pk = f.pk,
            normalized_file_name = lower(btrim(d.file_name)),
            version_group_id = d.id,
            version_number = 1
        FROM document_folders AS f
        WHERE f.knowledge_base_pk = d.knowledge_base_pk AND f.is_root
    """))
    op.alter_column("document_folders", "parent_pk", nullable=False)
    op.alter_column("documents", "folder_pk", nullable=False)
    op.create_index(
        "uq_documents_kb_canonical_sha256",
        "documents", ["knowledge_base_pk", "content_sha256"], unique=True,
        postgresql_where=sa.text("content_sha256 IS NOT NULL AND duplicate_of_document_id IS NULL"),
    )

def downgrade():
    op.drop_index("uq_documents_kb_canonical_sha256", table_name="documents")
    op.drop_constraint("fk_documents_folder_pk", "documents", type_="foreignkey")
    for column in (
        "duplicate_of_document_id", "previous_document_id", "version_number",
        "version_group_id", "normalized_file_name", "content_sha256", "folder_pk",
    ):
        op.drop_column("documents", column)
    op.drop_index("uq_document_folders_kb_root", table_name="document_folders")
    op.drop_index("idx_document_folders_kb_parent", table_name="document_folders")
    op.drop_table("document_folders")
```

The root row uses `parent_pk = pk` after its generated primary key is known. Downgrade removes the partial index and document columns before dropping `document_folders`.

- [ ] **Step 5: Verify schema contracts and migration heads**

```powershell
python -m pytest tests/test_document_workspace_schema.py tests/test_documents_domain_convergence.py -q -p no:cacheprovider
python -m alembic heads
```

Expected: 2 tests pass and Alembic reports only `20260711_01 (head)`.

- [ ] **Step 6: Commit persistence**

```powershell
git add app/mneme/models/document_folder.py app/mneme/models/document.py app/mneme/models/__init__.py app/mneme/crud/document_folder.py app/mneme/crud/document.py app/mneme/crud/knowledge_base.py app/mneme/domains/documents/router.py alembic/versions/20260711_01_add_document_workspace.py tests/test_document_workspace_schema.py tests/test_documents_domain_convergence.py
git commit -m "feat(documents): add folder and version persistence"
```

---

### Task 2: Implement authenticated folder tree and move APIs

**Files:**
- Modify: `app/mneme/crud/document_folder.py`
- Create: `app/mneme/domains/documents/folders.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/schemas/document.py`
- Modify: `app/mneme/crud/document.py`
- Create: `tests/test_document_folders_api.py`

**Interfaces:**
- Consumes: `DocumentFolder` and `Document.folder_pk` from Task 1.
- Produces: `GET/POST/PATCH/DELETE /kb/document-folders`, `POST /kb/document-folders/documents/{document_id}/move`, and typed tree responses.

- [ ] **Step 1: Write failing folder service tests**

```python
# tests/test_document_folders_api.py
import pytest
from app.mneme.domains.documents.folders import normalize_folder_name, validate_folder_move
from app.mneme.utils.exceptions import BusinessException


def test_folder_names_are_casefolded_and_trimmed():
    assert normalize_folder_name("  Research  ") == "research"


def test_folder_cannot_move_beneath_descendant():
    with pytest.raises(BusinessException, match="descendant"):
        validate_folder_move(folder_pk=4, new_parent_pk=9, descendant_pks={9, 10})
```

Add async API tests using the repository's FastAPI test fixtures for ownership, duplicate sibling names, empty deletion, non-empty deletion rejection, cross-knowledge-base moves, and document move success.

- [ ] **Step 2: Run folder tests and verify RED**

```powershell
python -m pytest tests/test_document_folders_api.py -q -p no:cacheprovider
```

Expected: import fails because folder CRUD and routes are absent.

- [ ] **Step 3: Add folder schemas and CRUD**

```python
class DocumentFolderCreate(BaseModel):
    knowledge_base_id: str
    parent_id: str
    name: str = Field(min_length=1, max_length=255)

class DocumentFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = None

class DocumentFolderItem(BaseModel):
    id: str
    parent_id: str
    name: str
    is_root: bool
    children: list["DocumentFolderItem"] = Field(default_factory=list)

class DocumentMoveRequest(BaseModel):
    folder_id: str
```

`app/mneme/crud/document_folder.py` must expose these exact async functions:

- `get_folder_by_id(db, *, folder_id: str, user_id: int) -> DocumentFolder | None` selects one owned folder.
- `get_root_folder(db, *, knowledge_base_pk: int, user_id: int) -> DocumentFolder` selects the hidden root or raises a controlled integrity error.
- `list_folders(db, *, knowledge_base_pk: int, user_id: int) -> list[DocumentFolder]` returns parent-before-child order.
- `descendant_folder_pks(db, *, folder_pk: int) -> set[int]` uses a recursive PostgreSQL CTE and excludes `folder_pk` itself.
- `folder_has_contents(db, *, folder_pk: int) -> bool` checks both direct documents and direct child folders.

- [ ] **Step 4: Implement routes with ownership and cycle guards**

```python
router = APIRouter(prefix="/kb/document-folders", tags=["document-folders"])

def normalize_folder_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()

def validate_folder_move(*, folder_pk: int, new_parent_pk: int, descendant_pks: set[int]):
    if folder_pk == new_parent_pk or new_parent_pk in descendant_pks:
        raise BusinessException("folder cannot be moved beneath itself or a descendant", code=4025)
```

Use `IntegrityError` to map sibling-name races to a deterministic `folder name already exists` business error. Add `app.mneme.domains.documents.folders` to `ROUTER_MODULE_NAMES`.
Root folders reject rename, move, and delete operations. Moving or renaming a document or folder changes only location/name metadata; it never rewrites an existing document's `version_group_id` or merges two version histories.

- [ ] **Step 5: Run folder tests and the router registry contract**

```powershell
python -m pytest tests/test_document_folders_api.py tests/test_documents_domain_convergence.py -q -p no:cacheprovider
```

Expected: all folder and router tests pass.

- [ ] **Step 6: Commit folder APIs**

```powershell
git add app/mneme/crud/document_folder.py app/mneme/domains/documents/folders.py app/mneme/bootstrap/router_registry.py app/mneme/schemas/document.py app/mneme/crud/document.py tests/test_document_folders_api.py
git commit -m "feat(documents): add nested folder APIs"
```

---

### Task 3: Add streaming deduplication, versions, and legacy hash backfill

**Files:**
- Create: `app/mneme/domains/documents/upload_service.py`
- Modify: `app/mneme/domains/documents/router.py`
- Modify: `app/mneme/crud/document.py`
- Modify: `app/mneme/schemas/document.py`
- Create: `scripts/backfill_document_hashes.py`
- Create: `tests/test_document_upload_dedup.py`
- Create: `tests/test_document_hash_backfill.py`

**Interfaces:**
- Consumes: folder IDs and document persistence from Tasks 1-2.
- Produces: `store_uploaded_document(db: AsyncSession, *, file: UploadFile, current_user: User, knowledge_base: KnowledgeBase, folder: DocumentFolder) -> DocumentUploadData` with `disposition: created | duplicate`, version metadata, folder metadata, and canonical existing document resolution.

- [ ] **Step 1: Write failing hash/version tests**

```python
# tests/test_document_upload_dedup.py
from app.mneme.domains.documents.upload_service import normalize_file_name, next_version


def test_file_name_normalization_is_case_insensitive():
    assert normalize_file_name("  Notes.MD ") == "notes.md"


def test_next_version_links_latest_document():
    version = next_version(latest_id="doc-v2", latest_version=2, group_id="doc-v1")
    assert version == {"version_group_id": "doc-v1", "version_number": 3, "previous_document_id": "doc-v2"}
```

Add async integration cases proving exact bytes across different names/folders return `duplicate`, same name/different bytes in one folder creates v2, different folders create independent v1 groups, and a simulated canonical unique-index race resolves to the existing canonical row.

- [ ] **Step 2: Run dedup tests and verify RED**

```powershell
python -m pytest tests/test_document_upload_dedup.py -q -p no:cacheprovider
```

Expected: import fails because `upload_service.py` does not exist.

- [ ] **Step 3: Implement streaming hash storage**

```python
async def stream_upload_to_temp(file: UploadFile, temp_path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with temp_path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.MAX_FILE_SIZE:
                raise BusinessException(f"The uploaded size of the file must be less than {settings.MAX_FILE_SIZE}")
            digest.update(chunk)
            target.write(chunk)
    return digest.hexdigest(), size
```

`store_uploaded_document` performs this exact order: validate folder ownership, stream to a temporary ID path, query canonical hash inside the knowledge base, return duplicate and delete temp if found, resolve same-folder normalized-name version lineage, atomically move temp to the final ID path, and create the document. If the partial unique index raises `IntegrityError`, it rolls back, deletes the losing request's final raw-file path, resolves the winning canonical record, and returns `disposition: duplicate`. Every exception path removes its own temporary or newly moved file without touching the canonical file.

- [ ] **Step 4: Extend upload response and route**

```python
class DocumentUploadData(BaseModel):
    disposition: Literal["created", "duplicate"]
    document_id: str
    canonical_document_id: str
    folder_id: str
    folder_path: list[str]
    file_name: str
    file_type: str
    file_size: int
    status: str
    version_group_id: str
    version_number: int
```

Add `folder_id: str | None = Form(default=None)` to `/kb/documents/upload`. Delegate all persistence to `store_uploaded_document`. Only `disposition == "created"` calls `sync_document_projection`; duplicate responses enqueue no work.

- [ ] **Step 5: Implement controlled legacy backfill**

```python
# scripts/backfill_document_hashes.py
async def backfill_batch(db: AsyncSession, *, after_pk: int = 0, batch_size: int = 100) -> tuple[int, int, int]:
    documents = await list_unhashed_documents(db, after_pk=after_pk, limit=batch_size)
    canonical_by_hash: dict[tuple[int, str], Document] = {}
    failed = 0
    for document in documents:
        if not Path(document.file_path).is_file():
            app_logger.bind(module="document_hash_backfill").error(
                f"raw file missing document_id={document.id}"
            )
            failed += 1
            continue
        digest = await asyncio.to_thread(sha256_path, Path(document.file_path))
        key = (document.knowledge_base_pk, digest)
        canonical = canonical_by_hash.get(key)
        if canonical is None:
            canonical = await find_canonical_by_hash(
                db,
                knowledge_base_pk=document.knowledge_base_pk,
                content_sha256=digest,
            )
        if canonical is None:
            canonical = document
            canonical_by_hash[key] = document
        document.content_sha256 = digest
        document.normalized_file_name = normalize_file_name(document.file_name)
        document.duplicate_of_document_id = None if document.id == canonical.id else canonical.id
        await db.flush()
    await db.commit()
    return len(documents), (documents[-1].pk if documents else after_pk), failed
```

`list_unhashed_documents` orders by ascending primary key so the keyset cursor is stable. The executable advances `after_pk` until a batch returns zero rows, logs missing raw files without exposing content, and exits nonzero after the scan when any file was missing or a database error occurred.

- [ ] **Step 6: Verify dedup, backfill, and existing upload tests**

```powershell
python -m pytest tests/test_document_upload_dedup.py tests/test_document_hash_backfill.py tests/test_documents_domain_convergence.py -q -p no:cacheprovider
```

Expected: all tests pass and no prior upload behavior regresses.

- [ ] **Step 7: Commit deduplication and versions**

```powershell
git add app/mneme/domains/documents/upload_service.py app/mneme/domains/documents/router.py app/mneme/crud/document.py app/mneme/schemas/document.py scripts/backfill_document_hashes.py tests/test_document_upload_dedup.py tests/test_document_hash_backfill.py
git commit -m "feat(documents): deduplicate uploads and track versions"
```

---

### Task 4: Add complete-content and authenticated raw-file APIs

**Files:**
- Create: `app/mneme/domains/documents/content_service.py`
- Modify: `app/mneme/domains/documents/router.py`
- Modify: `app/mneme/schemas/document.py`
- Create: `tests/test_document_content_api.py`

**Interfaces:**
- Produces: `GET /kb/documents/{id}/content`, `GET /kb/documents/{id}/raw`, `DocumentContentData`, and `DocumentVersionListData`.
- Reuses: `convert_file_to_markdown` from `app/mneme/clients/document_loader_client.py` through `asyncio.to_thread`.

- [ ] **Step 1: Write failing content classification tests**

```python
# tests/test_document_content_api.py
from app.mneme.domains.documents.content_service import classify_render_mode, sanitize_download_name


def test_render_modes_are_explicit():
    assert classify_render_mode("md") == "markdown"
    assert classify_render_mode("pdf") == "pdf"
    assert classify_render_mode("docx") == "office"
    assert classify_render_mode("json") == "structured"


def test_download_name_removes_header_control_characters():
    assert sanitize_download_name('report\r\nX-Test: injected.pdf') == "reportX-Test_ injected.pdf"
```

Add authenticated route tests for owner success, cross-user 404, missing raw file, inline PDF MIME type, attachment disposition, uploaded HTML being forced to `application/octet-stream` attachment even when `inline` is requested, complete Markdown text, escaped HTML content, Office conversion, and version listing order.

- [ ] **Step 2: Run content tests and verify RED**

```powershell
python -m pytest tests/test_document_content_api.py -q -p no:cacheprovider
```

Expected: import fails because `content_service.py` is absent.

- [ ] **Step 3: Implement typed complete-content conversion**

```python
RenderMode = Literal["markdown", "text", "structured", "office", "pdf", "unsupported"]

async def build_document_content(document: Document) -> DocumentContentData:
    mode = classify_render_mode(document.file_type)
    if mode == "pdf":
        return DocumentContentData.from_document(document, render_mode="pdf", text=None, sections=[])
    if mode in {"markdown", "text", "structured"}:
        text = await asyncio.to_thread(read_text_safely, Path(document.file_path))
        return DocumentContentData.from_document(document, render_mode=mode, text=text, sections=[])
    if mode == "office":
        markdown = await asyncio.to_thread(convert_file_to_markdown, document.file_path)
        return DocumentContentData.from_document(document, render_mode="office", text=markdown, sections=split_sections(markdown))
    return DocumentContentData.from_document(document, render_mode="unsupported", text=None, sections=[])
```

`read_text_safely` tries UTF-8 and UTF-8-SIG, then returns a clear parse warning instead of silently using an unsafe or lossy decoder.

- [ ] **Step 4: Add content, raw, and version routes**

```python
async def require_owned_document(db: AsyncSession, document_id: str, user_id: int) -> Document:
    document = await get_document_by_id(db, document_id=document_id, user_id=user_id)
    if document is None:
        raise BusinessException("document not found or not owned by current user", code=4044, status_code=404)
    return document

@router.get("/{document_id}/content")
async def document_content(document_id: str, current_user=Depends(get_current_user), db=Depends(get_database)):
    document = await require_owned_document(db, document_id, current_user.id)
    return success_response(await build_document_content(document))

@router.get("/{document_id}/raw")
async def document_raw(
    document_id: str,
    disposition: Literal["inline", "attachment"] = "inline",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    document = await require_owned_document(db, document_id, current_user.id)
    effective_disposition = "inline" if document.file_type == "pdf" and disposition == "inline" else "attachment"
    media_type = "application/pdf" if document.file_type == "pdf" else "application/octet-stream"
    return FileResponse(
        document.file_path,
        media_type=media_type,
        content_disposition_type=effective_disposition,
        filename=sanitize_download_name(document.file_name),
    )

@router.get("/{document_id}/versions")
async def document_versions(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    document = await require_owned_document(db, document_id, current_user.id)
    return success_response(await list_document_versions(db, document.version_group_id, current_user.id))
```

- [ ] **Step 5: Run content and security tests**

```powershell
python -m pytest tests/test_document_content_api.py tests/test_documents_domain_convergence.py -q -p no:cacheprovider
```

Expected: content, ownership, MIME, filename, and sanitization tests pass.

- [ ] **Step 6: Commit content APIs**

```powershell
git add app/mneme/domains/documents/content_service.py app/mneme/domains/documents/router.py app/mneme/schemas/document.py tests/test_document_content_api.py
git commit -m "feat(documents): expose complete and raw content"
```

---

### Task 5: Add frontend document API contracts and unified workspace state

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/package.json`
- Modify: `app/mneme_frontend_v0.2.1/package-lock.json`
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Create: `app/mneme_frontend_v0.2.1/src/composables/useDocumentWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/document-workspace-state.spec.ts`

**Interfaces:**
- Produces: `DocumentFolderData`, `DocumentContentData`, `DocumentVersionData`, `DocumentTab`, and `useDocumentWorkspace` methods used by Tasks 6-7.
- Adds dependencies: `marked` and `dompurify` only; no second state library or graph package.

- [ ] **Step 1: Add failing browser state contracts**

```ts
// tests/document-workspace-state.spec.ts
import { expect, test } from '@playwright/test';

test('opening a recent file reaches the unified reader', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  await page.getByTestId('sidebar-group-files').getByRole('button', { name: /zettelkasten/i }).click();
  await expect(page.getByTestId('document-reader')).toBeVisible();
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');
});

test('duplicate upload exposes the canonical open action', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Upload document').setInputFiles({ name: 'copy.md', mimeType: 'text/markdown', buffer: Buffer.from('# Atomic notes') });
  await expect(page.getByTestId('duplicate-upload-notice')).toContainText('already exists');
  await page.getByRole('button', { name: 'Open existing file' }).click();
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');
});
```

- [ ] **Step 2: Run contracts and verify RED**

```powershell
npx playwright test tests/document-workspace-state.spec.ts --project="Desktop Chrome" --workers=1
```

Expected: tests fail because recent files are inert and the unified reader state does not exist.

- [ ] **Step 3: Define frontend types and API methods**

```ts
export interface DocumentFolderData { id: string; parent_id: string; name: string; is_root: boolean; children: DocumentFolderData[]; }
export interface DocumentVersionData { document_id: string; version_group_id: string; version_number: number; file_name: string; created_at: string; }
export interface DocumentContentData { document_id: string; folder_id: string; file_name: string; render_mode: 'markdown'|'text'|'structured'|'office'|'pdf'|'unsupported'; mime_type: string; text: string|null; sections: { title: string|null; text: string }[]; parse_warning: string|null; }
export interface DocumentTab { documentId: string; title: string; blobUrl: string|null; }

export interface DocumentListItem {
  id: string;
  user_id: number;
  knowledge_base_id: string;
  folder_id: string;
  file_name: string;
  file_type: string;
  status: string;
  version_group_id: string;
  version_number: number;
  duplicate_of_document_id: string|null;
  created_at: string;
}
```

Add API methods:

```ts
listDocumentFolders(token, knowledgeBaseId)
createDocumentFolder(token, payload)
updateDocumentFolder(token, folderId, payload)
deleteDocumentFolder(token, folderId)
moveDocument(token, documentId, folderId)
documentContent(token, documentId, options?: { signal?: AbortSignal })
documentVersions(token, documentId)
documentRawBlob(token, documentId, disposition)
```

`documentRawBlob` uses the existing request base URL but returns `Response.blob()` after checking `response.ok`.
Extend `uploadDocument` with `folderId?: string | null` and append it to `FormData` as `folder_id`. `loadNotesView` requests `listDocuments`, `listDocumentFolders`, and the memory library in parallel; it publishes documents and folders only when the captured loader generation is current.

- [ ] **Step 4: Implement `useDocumentWorkspace`**

```ts
export function useDocumentWorkspace(params: {
  token: Ref<string>;
  activeKnowledgeBaseId: ComputedRef<string>;
  view: Ref<WorkspaceView>;
  invalidateWorkspace: () => void;
}) {
  const activeDocumentId = ref('');
  const openDocumentTabs = ref<DocumentTab[]>([]);
  const documentContent = ref<DocumentContentData | null>(null);
  const documentContentPhase = ref<'idle'|'loading'|'ready'|'empty'|'error'>('idle');
  const duplicateUpload = ref<DocumentUploadData | null>(null);
  const contentCache = new Map<string, DocumentContentData>();
  let contentAbort: AbortController | null = null;

  async function openDocument(documentId: string) {
    activeDocumentId.value = documentId;
    params.view.value = 'notes';
    contentAbort?.abort();
    documentContentPhase.value = 'loading';
    try {
      contentAbort = new AbortController();
      const content = contentCache.get(documentId) ?? await api.documentContent(
        params.token.value,
        documentId,
        { signal: contentAbort.signal },
      );
      contentCache.set(documentId, content);
      documentContent.value = content;
      documentContentPhase.value = content.text || content.sections.length || content.render_mode === 'pdf' ? 'ready' : 'empty';
      if (!openDocumentTabs.value.some(tab => tab.documentId === documentId)) {
        openDocumentTabs.value = [...openDocumentTabs.value, { documentId, title: content.file_name, blobUrl: null }];
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') documentContentPhase.value = 'error';
    }
  }

  function closeDocument(documentId: string) {
    const tab = openDocumentTabs.value.find(item => item.documentId === documentId);
    if (tab?.blobUrl) URL.revokeObjectURL(tab.blobUrl);
    openDocumentTabs.value = openDocumentTabs.value.filter(item => item.documentId !== documentId);
  }

  return { activeDocumentId, closeDocument, documentContent, documentContentPhase, duplicateUpload, openDocument, openDocumentTabs };
}
```

Wire it into `useMnemeWorkspace`. `openDocument` loads content, preview metadata, and version history together but publishes only results for the currently active document. Upload `created` opens the new ID immediately; upload `duplicate` sets the notice without creating a local document row. Both notes and graph loaders are invalidated after created uploads, delete, folder moves, and index completion.

- [ ] **Step 5: Extend preview data and install renderer dependencies**

```powershell
npm install marked dompurify
```

Preview documents include root/folder/version/hash metadata. Preview upload hashes fixture bytes with `crypto.subtle.digest`; known fixture content returns `disposition: 'duplicate'`, while changed same-name content increments the version.

- [ ] **Step 6: Run state tests and typecheck**

```powershell
npx playwright test tests/document-workspace-state.spec.ts --project="Desktop Chrome" --workers=1
npm run lint
```

Expected: unified opening and duplicate state pass; TypeScript exits 0.

- [ ] **Step 7: Commit frontend state**

```powershell
git add app/mneme_frontend_v0.2.1/package.json app/mneme_frontend_v0.2.1/package-lock.json app/mneme_frontend_v0.2.1/src/types.ts app/mneme_frontend_v0.2.1/src/lib/api.ts app/mneme_frontend_v0.2.1/src/lib/previewApi.ts app/mneme_frontend_v0.2.1/src/composables/useDocumentWorkspace.ts app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts app/mneme_frontend_v0.2.1/tests/document-workspace-state.spec.ts
git commit -m "feat(frontend): add unified document workspace state"
```

---

### Task 6: Build the responsive Obsidian reader and real file tree

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentTree.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentReader.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentContent.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentProperties.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/VaultView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/document-reader.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/layout-regression.spec.ts`

**Interfaces:**
- Consumes: `workspace.openDocument`, folder methods, tabs, content, versions, and duplicate notice from Task 5.
- Produces: three-pane desktop reader, overlay tablet tree, mobile drawers, safe content rendering, and accessible move controls.

- [ ] **Step 1: Write failing reader and folder interactions**

```ts
test('vault row opens markdown in the reader and exposes versions', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: /vault/i }).click();
  await page.getByTestId('document-tree').getByRole('button', { name: /zettelkasten/i }).click();
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');
  await expect(page.getByTestId('document-markdown')).toContainText('Atomic notes');
  await expect(page.getByTestId('document-version-history')).toContainText('v1');
});

test('folder tree creates and moves a document with keyboard controls', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: 'New folder' }).click();
  await page.getByLabel('Folder name').fill('Research');
  await page.getByRole('button', { name: 'Create folder' }).click();
  await page.getByRole('button', { name: /move zettelkasten/i }).click();
  await page.getByRole('option', { name: 'Research' }).click();
  await expect(page.getByTestId('folder-Research')).toContainText('zettelkasten-principles.md');
});
```

Add PDF Blob cleanup, Office section rendering, parse-error fallback, empty content, tab close, duplicate notice, desktop/tablet/mobile, non-empty folder delete, and drag-to-move tests.

- [ ] **Step 2: Run reader tests and verify RED**

```powershell
npx playwright test tests/document-reader.spec.ts --project="Desktop Chrome" --workers=1
```

Expected: tests fail because the document components do not exist.

- [ ] **Step 3: Implement sanitized content rendering**

```ts
// DocumentContent.vue setup
import DOMPurify from 'dompurify';
import { marked } from 'marked';

const safeMarkdown = computed(() => DOMPurify.sanitize(marked.parse(props.content.text ?? '') as string, {
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'style'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'style'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
}));
```

Use `v-html="safeMarkdown"` only for `markdown` and `office`. Text and structured modes render through `textContent`/interpolation. PDF obtains the authenticated Blob through the document workspace and renders `<iframe :src="blobUrl">`. Unsupported and parse-error states show metadata plus `Download original`.

- [ ] **Step 4: Implement the folder tree**

`DocumentTree.vue` recursively renders folders with `role="tree"`, folders with `role="treeitem"`, and documents as buttons. It emits `open-document`, `create-folder`, `rename-folder`, `move-folder`, `move-document`, and `delete-folder`. Native drag events and a keyboard move menu call the same emitted move operations. A non-empty delete error remains visible beside the attempted folder.

- [ ] **Step 5: Compose the reader shell and wire every non-graph entry**

Replace `VaultView`'s inert rows with:

```vue
<div class="document-workspace" :class="{ 'document-workspace--properties-open': propertiesOpen }">
  <DocumentTree :folders="workspace.documentFolders.value" :documents="workspace.selectedDocuments.value" :active-document-id="workspace.activeDocumentId.value" @open-document="workspace.openDocument" />
  <DocumentReader :tabs="workspace.openDocumentTabs.value" :content="workspace.documentContent.value" :phase="workspace.documentContentPhase.value" @select-tab="workspace.openDocument" @close-tab="workspace.closeDocument" />
  <DocumentProperties :preview="workspace.documentPreview.value" :versions="workspace.documentVersions.value" @select-version="workspace.openDocument" />
</div>
```

Bind global recent-file buttons in `App.vue` to `workspace.openDocument(doc.id)`. Upload controls receive the selected folder ID and use one accessible `aria-label="Upload document"`.

- [ ] **Step 6: Add responsive styling and inspect breakpoints**

Desktop: `grid-template-columns: 230px minmax(0,1fr) 270px`. Tablet: tree overlay and collapsible properties. Mobile: body-only default with explicit Files and Properties drawer buttons. Reuse existing canvas, sidebar, border, accent, serif, mono, radius, and shadow tokens.

Run:

```powershell
npx playwright test tests/document-reader.spec.ts tests/layout-regression.spec.ts --project="Desktop Chrome" --project="Mobile Chrome" --workers=2
npm run lint
npm run build
```

Expected: reader, folder, version, duplicate, security rendering, and all breakpoint tests pass; build exits 0.

- [ ] **Step 7: Commit the reader UI**

```powershell
git add app/mneme_frontend_v0.2.1/src/components/documents app/mneme_frontend_v0.2.1/src/views/VaultView.vue app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/tests/document-reader.spec.ts app/mneme_frontend_v0.2.1/tests/layout-regression.spec.ts
git commit -m "feat(frontend): add Obsidian document reader"
```

---

### Task 7: Optimize the graph as Obsidian Classic and open full documents

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/graph-reader-navigation.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

**Interfaces:**
- Consumes: `workspace.openDocument(documentId)` from Task 5 and reader UI from Task 6.
- Produces: deterministic label priority, degree-aware forces, selected one-hop focus, and graph-to-reader navigation.

- [ ] **Step 1: Write failing focus, label, and reader-navigation tests**

```ts
test('graph focus keeps one-hop neighbors visible and fades unrelated nodes', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.locator('[data-node-id="node-doc-zettel"]').click();
  await expect(page.locator('[data-node-id="node-memory-atomic"]')).toHaveAttribute('data-focus-state', 'neighbor');
  await expect(page.locator('[data-node-id="node-doc-graph"]')).toHaveAttribute('data-focus-state', 'dimmed');
});

test('double-click and Read full open the same document reader', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.locator('[data-node-id="node-doc-graph"]').dblclick();
  await expect(page.getByTestId('document-reader-title')).toContainText('memory-graph-design.pdf');
  await page.getByRole('button', { name: /graph/i }).click();
  await page.locator('[data-node-id="node-doc-zettel"]').click();
  await page.getByRole('link', { name: /read full|阅读全文/i }).click();
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');
});
```

Add deterministic default-label count, zoom-expanded labels, canvas clear, Enter open, drag-not-double-open, mobile, and reduced-motion regression cases.

- [ ] **Step 2: Run graph tests and verify RED**

```powershell
npx playwright test tests/graph-reader-navigation.spec.ts tests/force-directed-graph.spec.ts --project="Desktop Chrome" --workers=1
```

Expected: focus attributes and unified reader navigation fail.

- [ ] **Step 3: Add degree, adjacency, and label-priority state**

```ts
const neighborIds = computed(() => {
  const selected = selectedNode.value?.id;
  if (!selected) return new Set<string>();
  return new Set(edges.value.flatMap(edge => edge.source === selected ? [edge.target] : edge.target === selected ? [edge.source] : []));
});

function focusState(nodeId: string): 'selected'|'neighbor'|'dimmed'|'normal' {
  if (!selectedNode.value) return 'normal';
  if (selectedNode.value.id === nodeId) return 'selected';
  return neighborIds.value.has(nodeId) ? 'neighbor' : 'dimmed';
}

function labelVisible(nodeId: string, zoom: number, hoveredId: string | null) {
  if (nodeId === hoveredId || nodeId === selectedNode.value?.id) return true;
  if (simulationNode(nodeId)?.depth === 0) return true;
  const ranked = [...degreeByNode.value].sort((a,b) => b[1]-a[1] || a[0].localeCompare(b[0]));
  const limit = zoom >= 1.45 ? 14 : zoom >= 1.1 ? 8 : 4;
  return ranked.slice(0, limit).some(([id]) => id === nodeId);
}

function setVisibleLabelIds(next: Set<string>) {
  if ([...next].every(id => visibleLabelIds.has(id)) && next.size === visibleLabelIds.size) return;
  visibleLabelIds = new Set(next);
  collisionForce?.radius(node => {
    const base = node.depth === 0 ? 31 : 16;
    const labelAllowance = visibleLabelIds.has(node.id) ? Math.min(44, node.label.length * 2.4) : 0;
    return base + labelAllowance;
  });
  if (reducedMotionActive) settleReducedMotion(0.12);
  else if (simulation) {
    simulation.alpha(Math.max(simulation.alpha(), 0.12)).restart();
    simulationPhase.value = 'running';
  }
}
```

Store the configured `forceCollide` instance in `collisionForce`. Expose `focusState`, `labelVisible`, and `setVisibleLabelIds` from the composable. `GraphView` computes the stable visible-label ID set from zoom, selection, hover, root, and degree priority and calls `setVisibleLabelIds` only when that set changes.

- [ ] **Step 4: Tune forces without changing the lifecycle**

Use degree-bounded radii and charge:

```ts
const degree = degreeByNode.value.get(node.id) ?? 0;
const radius = Math.min(28, 9 + Math.sqrt(degree) * 4 + (node.depth === 0 ? 7 : 0));
forceManyBody<SimulationGraphNode>().strength(node => -150 - Math.min(240, (degreeByNode.value.get(node.id) ?? 0) * 28));
forceLink<SimulationGraphNode, SimulationGraphLink>(links).distance(link => link.edge_type === 'contains' ? 125 : 150).strength(0.32);
forceCenter(380, 340).strength(0.065);
```

Keep the Task 1 lifecycle: identity-only rebuild signature, hidden pause, frame batching, teardown, reduced-motion synchronous ticks, and settled stop.

- [ ] **Step 5: Render Obsidian Classic focus and unified opening**

In `GraphView.vue`, track `hoveredNodeId`, add `:data-focus-state`, conditionally render labels through `interaction.labelVisible(node.id, zoom, hoveredNodeId)`, use thin `1px` neutral edges, and lower opacity for dimmed nodes/edges. Add:

```ts
function openGraphDocument(node: GraphNodeData) {
  if (node.node_type === 'document') void props.workspace.openDocument(node.entity_id);
}

function openSelectedDocument() {
  const node = previewNode.value;
  if (node?.node_type === 'document') void props.workspace.openDocument(node.entity_id);
}
```

Bind `@dblclick.stop="openGraphDocument(node)"` and Enter to `openGraphDocument`; Space remains selection. Prevent double-click from starting a drag by checking pointer displacement before treating a pointer sequence as drag.

- [ ] **Step 6: Run graph and reader regression tests**

```powershell
npx playwright test tests/graph-reader-navigation.spec.ts tests/force-directed-graph.spec.ts tests/preview-mode.spec.ts -g "graph|reader|document|drag|filter|rail|motion" --project="Desktop Chrome" --project="Mobile Chrome" --workers=2
npm run lint
npm run build
```

Expected: graph focus, labels, open actions, existing force behavior, preview, drag, filters, rail, reduced motion, typecheck, and build all pass.

- [ ] **Step 7: Commit graph optimization**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts app/mneme_frontend_v0.2.1/src/views/GraphView.vue app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts app/mneme_frontend_v0.2.1/tests/graph-reader-navigation.spec.ts app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts
git commit -m "feat(frontend): connect Obsidian graph to document reader"
```

---

### Task 8: Full validation, migration rehearsal, push, deployment, and production acceptance

**Files:**
- Modify only if a test-driven correction is required by a failing acceptance check.
- Production source: `/root/project/Reminder`
- Environment backup: `/root/reminder-env-before-document-workspace-20260711`
- PostgreSQL backup: `/root/mneme-postgres-before-document-workspace-20260711.dump`

**Interfaces:**
- Consumes: Tasks 1-7.
- Produces: pushed `codex/frontend-reliability` HEAD and verified production reader, folders, deduplication, versions, and graph navigation.

- [ ] **Step 1: Run all local backend and source contracts**

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall -q app/mneme alembic scripts main.py
cd app/mneme_frontend_v0.2.1
Get-ChildItem tests -Filter '*.test.mjs' | Sort-Object Name | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: every backend test and subtest passes, compilation exits 0, and every source contract exits 0.

- [ ] **Step 2: Run clean complete frontend validation**

```powershell
npm ci --no-audit --no-fund
npm run lint
npm run build
npx playwright test --project="Desktop Chrome" --project="Mobile Chrome" --workers=2
```

Expected: dependency install, typecheck, production build, and complete desktop/mobile browser suite exit 0.

- [ ] **Step 3: Rehearse migration and backfill against a disposable PostgreSQL database**

Create a database from a schema/data fixture containing legacy rootless documents and exact duplicates. Run:

```powershell
python -m alembic upgrade heads
python scripts/backfill_document_hashes.py
python -m pytest tests/test_document_workspace_schema.py tests/test_document_hash_backfill.py -q -p no:cacheprovider
```

Expected: one hidden root per knowledge base, all documents attached, hashes populated for existing files, one canonical per knowledge-base/hash, duplicate rows preserved, and rerunning the backfill changes zero rows.

- [ ] **Step 4: Inspect the real UI at three breakpoints**

At 1440x900, 1024x768, and 390x844 in `/?preview=1`, verify file-tree hierarchy, reader tabs, Markdown, PDF fallback, Office sections, version history, properties, duplicate notice, focus-visible controls, graph label density, selected-neighborhood fade, drag, double-click, and mobile drawers. Save screenshots under `.tmp/document-workspace-visual/` and inspect each image.

- [ ] **Step 5: Final review and push**

```powershell
git status --short
git diff --check
git push origin codex/frontend-reliability
```

Expected: worktree clean and remote branch SHA equals local HEAD. If local GitHub SSH is unavailable, use the already verified server-side temporary bare-bundle push method without changing the production checkout.

- [ ] **Step 6: Back up production and audit volumes**

On `124.223.14.145`:

```bash
cd /root/project/Reminder
cp .env /root/reminder-env-before-document-workspace-20260711
docker exec reminder-postgres pg_dump -U postgres -Fc agentic > /root/mneme-postgres-before-document-workspace-20260711.dump
test -s /root/mneme-postgres-before-document-workspace-20260711.dump
docker volume ls --format '{{.Name}}' | grep '^mneme_' | sort
```

Expected: environment and non-empty database backups exist; all six current `mneme_*` volumes remain listed.

- [ ] **Step 7: Deploy verified source and run schema/backfill**

Upload a `git archive` of verified HEAD over `/root/project/Reminder`, restore the backed-up `.env`, and run:

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose config -q
COMPOSE_PROJECT_NAME=mneme docker compose build app worker migrate
COMPOSE_PROJECT_NAME=mneme docker compose run --rm migrate
COMPOSE_PROJECT_NAME=mneme docker compose run --rm app python scripts/backfill_document_hashes.py
COMPOSE_PROJECT_NAME=mneme docker compose up -d
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
```

Expected: migration and idempotent backfill exit 0; app, PostgreSQL, Redis, and Neo4j are healthy; worker runs; optional stack remains stopped; no named volume is deleted.

- [ ] **Step 8: Execute production acceptance with isolated data**

Using an isolated test account or test knowledge base:

1. Create nested folders `Research/Graph`.
2. Upload Markdown, PDF, DOCX, PPTX, and XLSX samples into `Research/Graph`.
3. Verify each opens from the tree; Markdown and Office content render; PDF embeds; originals download.
4. Upload the same Markdown bytes under another name and folder; verify no new document is created and `Open existing file` opens the canonical document.
5. Upload changed bytes under the same name/folder; verify v2 and version switching.
6. Move a document, move a folder, reject a descendant cycle, and reject non-empty deletion.
7. Open the graph, select a node, verify neighbor focus and label limits, double-click a document, and verify the same reader opens.
8. Delete the acceptance-test knowledge base/account and confirm its raw files and graph projections are removed through normal application deletion.

- [ ] **Step 9: Audit health, ports, and logs**

```bash
cd /root/project/Reminder
curl -fsS https://www.mneme.com.cn/health
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
logs="$(COMPOSE_PROJECT_NAME=mneme docker compose logs --since=15m app worker 2>&1)"
test "$(printf '%s' "$logs" | grep -c 'Traceback' || true)" = 0
test "$(printf '%s' "$logs" | grep -c 'Internal Server Error' || true)" = 0
docker inspect reminder-app reminder-worker --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -c '8\.147\.57\.104' | grep '^0$'
```

Expected: health code 0, migration exit 0, core services healthy, host ports remain loopback-only, old IP count 0 in running configuration, and error counts 0.
