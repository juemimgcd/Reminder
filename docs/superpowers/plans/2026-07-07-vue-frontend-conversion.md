# Vue Frontend Conversion Plan

## Goal

Convert `app/mneme_frontend_v0.2.1` from the legacy React implementation to a Vue 3 + TypeScript frontend, keeping the existing preview workbench behavior and build contracts intact.

## Success Criteria

- The frontend entrypoint is Vue + TypeScript (`src/main.ts`, `src/App.vue`).
- React dependencies, Vite React plugin usage, React JSX config, and `.tsx` app sources are removed.
- Preview mode still opens the populated Mneme workbench without backend login.
- Existing source contracts are updated to validate Vue source files instead of React source files.
- `npm run lint`, `npm run build`, and Playwright preview checks pass.

## Steps

1. Add a failing architecture contract for Vue and no React.
2. Replace Vite, TypeScript, and build-script entrypoints with Vue equivalents.
3. Rebuild the application shell and core preview workspace as Vue SFCs/composables.
4. Remove obsolete React component files and dependencies.
5. Verify typecheck, production build, and preview UI behavior.
