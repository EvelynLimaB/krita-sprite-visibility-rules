# Changelog

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
