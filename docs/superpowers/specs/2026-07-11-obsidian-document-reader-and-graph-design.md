# Obsidian Document Reader, Folders, Deduplication, and Graph Design

## Goal

Turn Mneme's uploaded documents into a coherent Obsidian-style reading workspace. A document must open from every place where it is shown, remain connected to its versions and backlinks, and be reachable directly from the knowledge graph. At the same time, replace the graph's rigid presentation with a quieter Obsidian Classic display that preserves the existing force-directed lifecycle.

## Confirmed Product Decisions

- Use one unified document reader inside the existing workspace rather than a modal, drawer, or browser-only download flow.
- Support real nested folders with create, rename, expand, collapse, and drag-to-move behavior.
- Deduplicate exact file content across an entire knowledge base.
- Treat the same file name with different content in the same folder as a version chain.
- Use the Obsidian Classic graph direction: freely settling nodes, thin straight edges, low label density, and focus-based disclosure.
- Keep the current Mneme visual language and design tokens. This is a functional extension of the existing workspace, not a new theme.

## Current-State Findings

The current upload endpoint creates a new document ID and stored file for every request. It validates ownership, type, size, and rate limits, but it does not hash content or detect duplicates. A user can currently upload the same file repeatedly. The practical limits are 10 MB per file and 10 upload requests per user per 60 seconds.

The frontend can request a document preview, but the preview contains only a summary, up to five chunks, and memory entries. There is no complete-content or original-file endpoint. Vault document rows expose only index and delete actions. Recent-file buttons have no click handler. Graph `Read full` only changes the active view to `notes`; it does not carry an active document into a reader, and the notes view does not render `documentPreview`. These disconnected state transitions are the root cause of the reported behavior.

## Unified Document State

`useMnemeWorkspace` remains the shared boundary and gains a focused document workspace state:

- `activeDocumentId`
- `openDocumentTabs`
- `documentContent`
- `documentContentPhase: idle | loading | ready | empty | error`
- `documentContentError`
- `openDocument(documentId)`
- `closeDocument(documentId)`
- `selectDocumentVersion(documentId)`
- `downloadDocument(documentId)`

`openDocument` is the only entry point for opening content. It selects or creates a reader tab, switches the active workspace view to `notes`, requests full content, and keeps the corresponding document active in the file tree and graph.

The following surfaces call this same method:

- Vault document rows
- Recent files in the global resource sidebar
- Graph file rail
- Graph `Read full`
- Double-click or keyboard open on a document graph node
- Duplicate-upload notice
- Version history

Single-clicking a graph document node continues to show a compact graph preview. Opening full content is a distinct double-click, Enter action, or `Read full` action so dragging and selection remain reliable.

## Reader Layout

Desktop uses a three-pane workspace:

1. A left file tree containing the active knowledge base, nested folders, documents, version badges, and a recent-files section.
2. A central tabbed reader containing the complete document body and a compact status bar.
3. A right properties pane containing type, indexing status, tags, summary, version history, memories, and backlinks.

The center reader is the visual priority. Properties remain secondary and may be collapsed. On tablet, the file tree becomes an overlay and the properties pane is collapsible. On mobile, both side panes become drawers and the document body occupies the primary screen.

Reader tabs are in-memory workspace state. They survive navigation between Mneme views during the current session but are cleared on logout. This phase does not add browser-style restoration across separate login sessions.

## Full Content and Original File APIs

Add two authenticated document endpoints:

### `GET /kb/documents/{document_id}/content`

Returns a typed content envelope:

- document and version metadata
- `render_mode`: `markdown`, `text`, `structured`, `office`, `pdf`, or `unsupported`
- MIME type and encoding when applicable
- complete text or structured sections
- headings or section labels where the source parser exposes them
- empty and parse-warning information

Content behavior by format:

- Markdown and plain text return complete UTF-8-safe text.
- JSON, CSV, XML, and HTML return safely escaped structured or text content.
- Uploaded HTML is never executed as an application document.
- PDF returns metadata that instructs the frontend to use the raw endpoint as an authenticated Blob.
- DOCX, PPTX, XLSX, XLS, and EPUB reuse the existing document loader and return structured sections, slides, sheets, or extracted text.
- Unsupported but allowed future formats return metadata plus an original-file download action.

The endpoint can use indexed chunks when they represent the complete source, but indexing is not required for reading. When complete chunks are unavailable, it parses the stored source on demand. Reader loading is lazy and does not add work to authentication or workspace startup.

### `GET /kb/documents/{document_id}/raw?disposition=inline|attachment`

Streams the original stored file after ownership validation. The server sets a safe MIME type and sanitized `Content-Disposition`. The frontend fetches PDF content with the bearer token, creates an object URL, embeds it, and revokes the object URL when the tab closes or changes.

## Safe Rendering

- Markdown output is sanitized before insertion into the DOM.
- Raw HTML scripts, event handlers, executable URLs, and untrusted embeds are removed.
- JSON, XML, and other structured text is displayed as text, not interpreted markup.
- External resources are not loaded automatically from uploaded documents.
- Content requests are aborted when the user switches documents before the current request finishes.
- Parse failures produce a readable error state with metadata and a download-original action rather than a blank pane.

## Real Folder Model

Add a `document_folders` table with:

- internal and public IDs
- owner and knowledge-base identity
- non-null parent folder identity
- display name and normalized name
- root-folder marker
- timestamps

Every knowledge base has one hidden root folder. User-created top-level folders are children of this root, which avoids nullable-parent uniqueness ambiguity. Folder names are unique case-insensitively within the same parent.

Documents gain a non-null folder reference. Existing documents migrate into their knowledge base root folder. Physical raw-file storage remains document-ID based and does not mirror user folder names, preventing path traversal and keeping moves metadata-only.

Folder APIs support:

- list tree
- create folder
- rename folder
- move folder
- move document
- delete empty folder

Moving a folder beneath itself or one of its descendants is rejected. Cross-user and cross-knowledge-base moves are rejected. Non-empty folders cannot be deleted in this phase; users must first move or delete their contents.

## Deduplication and Versioning

Uploads stream to a temporary path while calculating SHA-256. The complete file is never buffered in memory solely for hashing.

Documents gain:

- `content_sha256`
- `normalized_file_name`
- `version_group_id`
- `version_number`
- `previous_document_id`
- `duplicate_of_document_id`

Exact-content behavior:

- The deduplication scope is the complete knowledge base, not the folder.
- If a canonical document already has the same SHA-256, the temporary upload is removed and no document, index task, graph node, or raw-file copy is created.
- The upload response is idempotent and returns `disposition: duplicate` plus the existing document ID, file name, folder location, and version.
- The frontend presents `File already exists` with an `Open existing file` action.

Version behavior:

- Version grouping is scoped to the same folder and case-insensitive normalized file name.
- Same folder plus same name plus different content creates the next version number and points to the previous latest document.
- The newest version is shown by default; older versions remain readable and downloadable from the properties pane.
- The same name in different folders is an independent version group.
- Renaming or moving an existing document does not silently merge version groups.

Concurrent uploads are protected by a PostgreSQL partial unique index on canonical documents per knowledge base and hash. If concurrent requests race, the loser resolves and returns the canonical existing document rather than surfacing a database error.

Legacy backfill preserves data. Existing exact duplicates are not deleted: the earliest document becomes canonical, later exact copies are marked with `duplicate_of_document_id`, and all existing references remain intact. Future uploads resolve to the canonical document.

## Upload Experience

The file input uses a shared upload state with pending, success, duplicate, and error feedback.

- A new upload refreshes the active folder tree, invalidates notes and graph data, and opens the uploaded document immediately.
- An exact duplicate opens a notice with the canonical document's folder path and an explicit open action.
- A new version opens as the active version and displays its version badge.
- Uploading into a selected folder preserves that destination.
- After upload, navigating to the graph always retrieves or applies fresh graph data so the new document cannot be hidden by a previously loaded view cache.

## Obsidian Classic Graph Display

The existing single D3 force simulation remains the foundation. The optimized display changes presentation and interaction rather than introducing another graph engine.

### Layout behavior

- Thin, neutral, straight edges replace visually heavy relationship lines.
- Node radius incorporates node type and graph degree, within strict minimum and maximum bounds.
- Charge and link distance become degree-aware so high-degree nodes receive space without forming a rigid hub-and-spoke diagram.
- Centering is weaker and deterministic starting positions include mild seeded asymmetry, producing a more organic distribution.
- Collision includes label allowance only for labels that are currently visible.
- The simulation still settles naturally, stops after convergence, pauses in hidden tabs, publishes positions at most once per frame, and respects reduced-motion preferences.

### Label disclosure

Always show labels for:

- the knowledge-base root
- the selected node
- the hovered or keyboard-focused node
- a bounded set of the highest-degree visible nodes

Additional labels appear as the user zooms in. Low-priority labels remain hidden at the default zoom to reduce clutter. Label selection is deterministic so labels do not flicker while the simulation moves.

### Focus behavior

- Single-click selects a node and computes its one-hop neighborhood.
- Selected nodes and direct neighbors remain fully visible.
- Unrelated nodes and edges fade but remain spatially present.
- Clicking the canvas clears focus.
- Double-clicking a document node or pressing Enter calls the shared `openDocument` path.
- Graph file-rail actions and `Read full` use the same path.
- Drag, restart, filters, zoom, GraphRAG, responsive rail behavior, and reduced motion remain supported.

## Loading, Empty, and Error States

Every new data surface has explicit states:

- File tree loading skeleton and empty knowledge-base guidance
- Reader loading skeleton
- Empty-readable-content explanation
- Parse-warning state with download action
- Ownership or missing-document error without leaking file-system paths
- Folder mutation pending and error feedback
- Duplicate-upload notice with open action
- Version-history empty and loading states
- Graph empty, loading, and scoped request errors

Interactive controls include hover, focus-visible, disabled, and pending states. Drag and drop also has a keyboard-accessible move action.

## Data Refresh and Cache Boundaries

- Folder and document mutations invalidate the notes view.
- Upload, delete, indexing completion, and graph rebuild invalidate graph data.
- Reader content is cached per immutable document version during the active session.
- Selecting another version uses its distinct document ID and cache entry.
- Original-file Blob URLs are never kept after the corresponding tab closes.
- Folder movement does not reparse or reindex document content.

## Testing

### Backend

- folder creation, rename, move, empty delete, duplicate names, and cycle rejection
- ownership and knowledge-base boundaries for folders and documents
- migration of legacy documents into root folders
- complete content for text, Markdown, structured, PDF metadata, and Office extraction
- original-file inline and attachment responses
- HTML and response-header sanitization
- exact duplicate detection across folders and file names
- same-name different-content version creation
- same names in different folders remaining independent
- concurrent exact uploads resolving to one canonical document
- legacy duplicate backfill without deleting records

### Frontend

- Vault rows, recent files, graph rail, graph `Read full`, graph double-click, and keyboard open all reach the same reader
- upload success automatically opens the new document
- duplicate upload creates no new row and exposes `Open existing file`
- version history and version switching
- folder create, rename, expand, collapse, document move, folder move, and cycle-error feedback
- reader loading, empty, parse-error, PDF Blob cleanup, and download states
- safe Markdown and structured rendering
- Obsidian label-priority behavior, selected-neighborhood fade, double-click open, drag, restart, filters, and convergence
- desktop, tablet, and mobile file-tree and properties-pane behavior
- existing authentication, lazy loading, GraphRAG, settings, localization, and responsive tests remain green

### Release verification

- complete backend test suite and Python compilation
- all frontend source contracts
- typecheck, production build, and complete desktop/mobile Playwright suite
- browser inspection at desktop, tablet, and mobile breakpoints
- production migration backup and named-volume audit
- production upload/read tests with Markdown, PDF, Office, exact duplicate, and new version samples
- cleanup of acceptance-test records after verification
- service health, migration exit, port binding, and recent error-log audit

## Deployment

Deploy on the existing `codex/frontend-reliability` branch and Compose stack. Before migration, back up the production environment file and PostgreSQL data. Preserve all existing `mneme_*` named volumes and never run `docker compose down -v`.

Apply the folder/version schema migration, run the controlled legacy hash and duplicate backfill, build the verified source, and start the existing Compose project. Production acceptance uses an isolated test knowledge base or test account and deletes its sample documents and folders after verification.

## Non-Goals

- Editing and saving uploaded Office or PDF files in the browser
- Collaborative real-time editing
- Executing uploaded HTML or embedded scripts
- Recursive deletion of non-empty folders
- Replacing the D3 graph engine
- Perpetual graph animation after convergence
- Cross-knowledge-base deduplication or file moves

