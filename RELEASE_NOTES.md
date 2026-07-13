# Sprite Visibility Rules 1.0.1

Documentation-audited test release for Krita sprite and game-art workflows.

## Included

- Inverse pairs: each member always has the opposite visibility of the other.
- Exclusive sets: showing one member hides the other members.
- Linked sets: showing or hiding one member applies the same state to the set.
- Detection of changes made through Krita's normal layer visibility controls.
- Rule data embedded inside each `.kra` file through a Krita document annotation.
- UUID-based layer references, missing-layer reporting, and layer rebinding.
- Rule ordering, enable/disable, global pause, polling interval, and manual enforcement.
- Conflict/cycle protection to prevent endless visibility oscillation.
- Krita Flatpak installation and GitHub publishing helpers.

## 1.0.1 audit fixes

- Use Krita 6's public `Document.nodeByUniqueID()` API before falling back to a full layer-tree walk.
- Bind each docker to its own canvas document, preventing inactive Krita windows from polling the globally active document.
- Roll back in-memory rule ordering when persistence fails.
- Fix Linux Mint publishing by using `python3` by default.
- Derive package, installer, tag, and release names from the plugin version instead of hardcoding `1.0.0`.
- Add tests for UUID lookup, canvas document binding, reorder rollback, and the publishing helper.

## Test status

The release passed the checks recorded in `TEST_REPORT.md`. The docker was constructed in an offscreen PyQt5 test against a fake object surface matching the public Krita 6 API. A real interactive run inside the user's exact Krita Flatpak remains the final compatibility test.

## Safety note

Use a copy of an important `.kra` file for the first test. V1 changes only participating layers' visibility and stores JSON rule configuration in a document annotation. The rule schema remains version 1 and is compatible with files created by 1.0.0.
