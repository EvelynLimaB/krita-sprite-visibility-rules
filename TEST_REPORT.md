# V1 verification report

Release: **1.0.0**

Verification date: **2026-07-13**

## Automated checks

- `ruff format --check .`
- `ruff check .`
- importer ZIP build through `scripts/build_release.py`
- 28 unit, controller, storage, and package tests
- offscreen PyQt5 docker import/construction smoke test
- recursive Python bytecode compilation
- Bash syntax validation
- mocked Flatpak installation and replacement-backup test
- ZIP CRC/integrity test
- SHA-256 generation
- local Git object and whitespace verification

## Behaviors covered

- inverse pair in both directions
- normal eye-click simulation through the polling controller
- linked visibility propagation
- exclusive visibility, including strict fallback behavior
- missing layer handling
- cascaded rules
- contradictory cycle rejection
- disabled rules
- annotation JSON round trip
- malformed and unsupported annotation data
- rule validation
- importer-compatible ZIP root layout
- plugin registration and docker construction
- switching between distinct documents that happen to share a root-node UUID
- preserving unsaved docker edits when Krita returns another wrapper for the same document

## Public Krita API surface checked

The implementation is limited to public libkis/PyKrita operations used by V1:

- `Krita.activeDocument()` and `Krita.activeWindow()`
- `Window.activeView()`
- `View.selectedNodes()`
- `Document.rootNode()`, `activeNode()`, annotations, `setModified()`, and `refreshProjection()`
- `Node.childNodes()`, `name()`, `uniqueId()`, `visible()`, and `setVisible()`
- docker registration through `DockWidgetFactory`

## Remaining real-world test

This environment cannot launch the user's graphical Krita Flatpak. The release is structurally and behaviorally checked, but the final proof is an interactive test in the exact installed Krita build, desktop session, and plugin combination. The first-test procedure in `README.md` is designed to expose compatibility problems without risking a production file.
