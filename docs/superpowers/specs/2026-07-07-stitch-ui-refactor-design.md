# Stitch UI Refactor Design

## Goal

Refactor `app/mneme_frontend_v0.2.1` so the Vue frontend follows the Stitch export in `C:\Users\jiayu\Downloads\stitch_ai_graph_ui_refactor\stitch_ai_graph_ui_refactor`, while preserving the current API contract, preview mode, authentication flow, and Vue 3 + Tailwind v4 stack.

## Source Material

- `mneme_intelligence/DESIGN.md` defines the Mneme Intelligence visual system: dark obsidian surfaces, refined glass panels, violet active states, Geist/Inter/JetBrains Mono typography, and a fixed 256px navigation rail.
- `_1/code.html` and `_1/screen.png` define the Research Vault layout.
- `_2/code.html` and `_2/screen.png` define the Knowledge Graph layout.
- `ai_1/code.html` and `ai_1/screen.png` define the AI Assistant layout.
- `ai_2/code.html` and `ai_2/screen.png` define the System Settings layout.

## Approach

Use the Stitch export as the visual and layout reference, but keep the existing Vue application architecture. The refactor changes the presentation layer first, with minimal changes to data loading or backend calls.

The main implementation should stay close to:

- `src/App.vue` for shell and view structure.
- `src/index.css` for design tokens and reusable visual utilities.
- `src/composables/useMnemeWorkspace.ts` only if the new UI needs small derived state or user-facing copy fixes.
- Tests only where current selectors or contracts need to follow the renamed/refactored UI.

## View Mapping

The existing app views map to the Stitch screens as follows:

- `dashboard` becomes the landing workspace for the Knowledge Graph overview, using current document, memory, graph, and health summary data.
- `notes` becomes Research Vault, with a file/directory rail and document cards populated from `selectedDocuments`.
- `graph` becomes the full-bleed Knowledge Graph workspace, with a file rail, SVG graph canvas, controls, and a right-side properties panel populated from `graphData` and the selected knowledge base.
- `ai` becomes AI Laboratory, with a conversation/history rail and a main chat surface reusing `askVault`, `askCompanion`, `chatResult`, and `companionResult`.
- `settings` becomes System Settings, with model, access/security, sync/readiness, and analytics panels populated from existing health, readiness, analytics, profile, growth, and advice data.

## Shell

Authenticated users see a fixed dark application shell:

- A 256px left navigation rail using lucide Vue icons instead of Material Symbols.
- The brand reads `Mneme Intelligence` with the subtitle `Cognitive Sanctuary`.
- Primary navigation uses the Stitch labels: `Knowledge Graph`, `Research Vault`, `Semantic Map`, `AI Laboratory`, and `System Settings`.
- A primary `New Research` button opens the existing create-vault command path.
- Documentation/support footer items are visual only unless an existing route or command already exists.

The unauthenticated login screen keeps the current login flow, but receives the same brand styling and corrected text.

## Data Flow

No backend API changes are planned. The UI continues to use `useMnemeWorkspace()` as the single source of state and commands.

The refactor may add computed values in `App.vue` for display-only data such as:

- active view labels and subtitles,
- document card metadata,
- graph node positions,
- AI message transcript derived from available request/response refs,
- settings summary cards.

These should remain deterministic and preview-mode friendly.

## Error Handling

Existing API error handling remains in the composable. The UI should show `banner`, `authError`, and loading/empty states where the current data may be missing.

Empty states should be concise and domain-specific:

- no vault selected,
- no documents in the vault,
- graph data loading or unavailable,
- no AI response yet.

## Styling Constraints

- Preserve the dark-mode-first Stitch palette and Tailwind v4 tokens already present in `index.css`.
- Use restrained violet highlights without making the interface a single-color theme.
- Keep cards and panels at 8px radius or less unless matching existing utilities.
- Use lucide icons from `@lucide/vue`; do not add Material Symbols.
- Avoid decorative gradient orbs and unrelated landing-page content.
- Fix current mojibake text in user-facing labels.
- Use valid Vue attributes such as `data-testid`, not React-style `testId`.

## Verification

Implementation is complete when:

- `npm run lint` passes in `app/mneme_frontend_v0.2.1`.
- `npm run build` passes in `app/mneme_frontend_v0.2.1`.
- Preview mode still renders the authenticated workbench without backend login.
- Existing frontend architecture tests are updated only as needed for Vue/Stitch contracts.
- The key `data-testid` hooks used by tests remain stable or are intentionally updated with matching tests.

## Out of Scope

- Changing backend endpoints or response schemas.
- Introducing a new router, state manager, design system package, or component registry.
- Implementing real file upload UI beyond what the current API/composable supports.
- Adding persistent chat sessions unless already available in the current frontend state.
- Replacing the SVG graph with a new force-directed graph engine.
