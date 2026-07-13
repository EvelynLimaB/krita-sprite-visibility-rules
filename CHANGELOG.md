# Changelog

## 1.1.1 — 2026-07-13

- Added a 32 ms render-settle debounce before event-assisted visibility enforcement.
- Restored one batched `Document.refreshProjection()` call after plugin-generated visibility changes.
- Raised the minimum fallback polling interval from 25 ms to 50 ms.
- Preserved the node cache, compiled rule dispatch, affected-rule-only cascades, and reduced docker rebuilding from 1.1.0.
- Added regression tests for one projection refresh per batch and delayed/coalesced input scans.
- Kept the document annotation schema at version 1; existing `.kra` rules remain compatible.

## 1.1.0 — 2026-07-13

- Added immediate, coalesced scans after layer-list mouse input and shortcut events.
- Retained configurable polling as a fallback for programmatic and unusual visibility changes.
- Added short-lived node-wrapper caching to avoid repeated UUID resolution on every timer tick.
- Added compiled rule membership indexes so only rules touched by changed layers are evaluated.
- Removed redundant projection refreshes after `Node.setVisible()`.
- Removed repeated full node scans and docker rebuilds from the normal visibility-change path.
- Added a synthetic hot-path benchmark and regression tests for caching, dispatch, and scan coalescing.
- Kept the document annotation schema at version 1; existing `.kra` rules remain compatible.

## 1.0.2 — 2026-07-13

- Fixed the release ZIP so Krita's built-in importer recognizes the plugin.
- Added the explicit `sprite_visibility_rules/` ZIP directory entry required by Krita's importer implementation.
- Added regression tests that mirror Krita's module-discovery logic.
- Plugin behavior and `.kra` annotation schema are unchanged from 1.0.1.

## 1.0.1 — 2026-07-13

- Audited the plugin against Krita 6.0.2.1's public PyKrita API and importer.
- Added direct UUID lookup with a compatibility fallback to layer-tree traversal.
- Scoped each docker to its own canvas document.
- Fixed failed rule-order saves not rolling back in memory.
- Fixed the GitHub helper to use `python3` and derive all release names from the version.
- Expanded adapter, UI, package, and Flatpak tests.

## 1.0.0 — 2026-07-13

- Initial proof-checked release.
- Added inverse pairs, exclusive sets, and linked sets.
- Added normal eye-icon detection through tracked-node polling.
- Added `.kra` annotation persistence using node UUIDs.
- Added docker UI, missing-layer rebind, rule ordering, pause, and manual enforcement.
- Added cycle protection, Flatpak helper, importer ZIP builder, and automated tests.
