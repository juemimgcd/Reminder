# Frontend Reliability and Authentication Design

## Objective

Make the production Mneme workspace fast enough to enter immediately after authentication, ensure every visible graph control has a real behavior, repair the settings and collapsed-shell layouts, and provide a complete registration flow alongside login.

## Confirmed Production Problems

The deployed application eagerly loads health, graph, documents, memory, profile, evidence, growth, analytics, advice, chat, and model data after authentication and after knowledge-base changes. A stale production `NEO4J_URI` points at `8.147.57.104:7687`, so graph reads wait for a network timeout before falling back. Profile, growth, advice, and chat routes can return 500 when model-backed work is unavailable; one rejected promise currently becomes a global `Internal Server Error` banner and prevents the rest of the page from settling.

The graph view contains placeholder folders and controls. Node movement has an empty handler, preview requires a delayed pointer hold, filter tabs do not update data, and the read-full action is not connected to a document. Collapsing the graph file rail hides its contents but leaves the 280px grid column in place.

The settings page renders a workspace title and a second large internal title/navigation column. Combined with the global error banner, this causes overlapping hierarchy and typography. The authentication API supports registration, but the authentication screen exposes only login.

## Architecture

The existing Vue 3 component structure remains. `useMnemeWorkspace` becomes an orchestrator for small, view-scoped loaders instead of one eager fan-out loader. Each view owns its loading, empty, ready, and error presentation while shared authentication, user, knowledge-base, and health state stays in the workspace composable.

The FastAPI contracts remain unchanged except where error handling needs a stable, user-safe response. Production configuration uses the internal Compose Neo4j address. Model-backed failures are treated as degraded feature states rather than shell-wide failures.

## Authentication

The authentication card has two explicit modes: login and registration. Login contains username and password. Registration contains username, optional display name, password, and password confirmation. Username and password constraints mirror the backend contract: username is 3–100 characters and password is 8–128 characters.

Registration calls `/auth/register`, then calls `/auth/login` with the same credentials, stores the returned token when storage is available, fetches `/auth/me`, and enters the default knowledge base. Buttons show a pending state, disable duplicate submission, and preserve form values after a recoverable error.

Authentication succeeds in memory even if `localStorage` is unavailable. Storage access is wrapped so browser privacy settings cannot prevent `/auth/me` from running. Storage failures produce a non-blocking session-only notice. Error messages distinguish invalid credentials, duplicate usernames, validation errors, network failures, and unexpected responses.

## Loading and Failure Isolation

Authentication startup loads only the current user, service health, readiness summary, and knowledge-base list. It then renders the shell. It does not wait for graph, memory, profile, analysis, advice, chat, or model configuration.

View loaders are routed as follows:

- Dashboard: documents plus compact analytics required by dashboard metrics.
- Vault: documents and document preview on demand.
- Graph: graph payload and document list; document preview only after node selection.
- AI Lab: chat sessions and model configuration; messages only for the active session.
- Settings: model configuration and health details.
- Profile, memory, growth, evidence, and advice: loaded only by views that display them or by an explicit refresh action.

Each loader tracks `idle`, `loading`, `ready`, `empty`, or `error`. Parallel calls use independent settlement so one failed endpoint does not erase successful sibling data. A view error is shown inside that view with retry. The shell banner is reserved for short user-triggered confirmations and is dismissible. Raw strings such as `Internal Server Error` are mapped to clear Chinese messages with an optional diagnostic detail.

Knowledge-base selection cancels or ignores stale in-flight results. Re-selecting a loaded view may reuse cached data; explicit refresh bypasses the cache.

## Graph Workspace

The graph file rail contains only real knowledge-base documents. Placeholder Machine Learning folders and files are removed. Selecting a document focuses its graph node when present and opens its preview.

Node interaction follows normal desktop and touch expectations:

- Single click or tap selects a node and opens the preview immediately.
- Pointer drag moves a node locally for the current view without issuing backend writes.
- Clicking empty canvas clears selection.
- Zoom in, zoom out, center, and restart layout update the rendered view.
- Restart layout recomputes node positions rather than only resetting zoom.
- Read full opens the corresponding document in the Vault view when the node references a document.

The filter tabs implement real derived views:

- All nodes: every node and visible connecting edge.
- Tags: tag/concept nodes and their connecting edges.
- Orphans: nodes with no visible edges.
- Filter button: toggles a compact filter panel for document, memory, and concept node types.

Graph search highlights matching nodes and supports the existing GraphRAG submission separately. Controls that cannot be backed by current data are removed rather than left inert.

Collapsing the file rail changes the graph grid from `280px minmax(0, 1fr)` to `0 minmax(0, 1fr)` on desktop. The canvas fills the released width and the toggle remains reachable. Tablet and mobile retain an overlay drawer with a scrim.

## Settings and Shell Layout

The workspace top bar remains the single page title. The settings view removes its second large `h1` and uses a compact sticky section navigation labeled Preferences. Settings cards use consistent sans-serif Chinese typography, line height, spacing, and tokenized colors. English technical labels remain only for provider/model identifiers.

The settings navigation and content columns use `minmax(0, ...)` to prevent text overflow. At narrower desktop widths the navigation becomes a horizontal scrollable section bar. At mobile width it becomes a compact select or tab row. Cards, choice controls, range controls, and status content cannot overlap the shell banner or each other.

The global status banner has a fixed internal layout, supports multiline content without absolute overlap, exposes a close control, and uses semantic success/warning/error variants. It does not cover the page title or navigation.

The resource sidebar and graph rail have separate collapse state and separate CSS modifiers. Closing either removes its grid track on desktop. Overlay behavior is used only below the tablet breakpoint.

## Production Configuration and Backend Degradation

Production sets:

```env
NEO4J_URI=bolt://neo4j:7687
```

The application is rebuilt after the environment change. Neo4j health, graph response time, and container logs are verified before frontend acceptance.

Model-backed profile, growth, advice, and chat failures must return actionable API errors without Python tracebacks leaking to the browser. The frontend displays those features as temporarily unavailable and keeps graph, documents, settings, and navigation usable. Fixing provider credentials or model configuration is tracked separately from frontend fault isolation if logs show an external provider failure.

## Accessibility and Interaction States

Every interactive control has hover, focus-visible, active, and disabled states. Icon-only buttons retain accessible labels. Authentication modes are keyboard operable. Graph nodes are keyboard selectable or have an equivalent accessible node list. Reduced-motion preferences disable layout animation. Loading skeletons do not replace the entire shell.

## Responsive Behavior

Desktop at 1280px and above supports activity bar, optional resource sidebar, and full content. Tablet from 768px to 1279px keeps the activity bar and uses overlay resource/graph rails. Mobile below 768px uses the bottom navigation and full-width views. Settings, graph controls, authentication, and status messages are explicitly verified at 1440px, 1024px, 768px, and 390px widths.

## Testing

Automated coverage includes:

- Authentication response parsing and storage failure tolerance.
- Registration validation, duplicate-user errors, automatic login, and duplicate-submit prevention.
- Startup does not call heavy view endpoints before a view requests them.
- Independent loader settlement preserves successful data when a sibling request fails.
- Knowledge-base switches ignore stale responses.
- Graph filter derivation, node selection, document navigation, actual layout restart, and rail collapse track removal.
- Settings contains one page-title hierarchy and responsive layout contracts.
- Nginx/Compose production configuration continues to bind private services correctly.

Frontend typecheck and production build remain mandatory. Browser acceptance uses a real production-like backend at desktop, tablet, and mobile breakpoints. Production verification measures authentication-to-shell time, confirms the stale Neo4j address is absent from logs, exercises every visible graph control, tests registration with a disposable account, and verifies that an intentionally unavailable model-backed endpoint does not break navigation.

## Success Criteria

- Login reaches the shell without waiting for graph/model timeouts.
- A new user can register, is automatically logged in, and receives a default knowledge base.
- No raw `Internal Server Error` banner appears during normal degraded operation.
- Every visible graph control performs its advertised action.
- Collapsing either sidebar releases its width without shifting or clipping content.
- Settings typography and hierarchy remain aligned at all required breakpoints.
- A failed profile/advice/growth request affects only its own panel.
- Production uses the internal Neo4j service and emits no connection attempts to `8.147.57.104:7687`.
