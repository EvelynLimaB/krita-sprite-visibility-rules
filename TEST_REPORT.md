# Verification report

Release: **1.0.2**  
Verification date: **2026-07-13**

## Automated checks

- `ruff format --check .`
- `ruff check .`
- deterministic importer ZIP build through `scripts/build_release.py`
- unit, controller, adapter, storage, package, and importer-layout tests
- offscreen PyQt5 docker import/construction smoke test
- recursive Python bytecode compilation
- Bash syntax validation
- mocked Flatpak installation and replacement-backup test
- ZIP CRC/integrity test
- SHA-256 generation
- reproducible-build digest comparison
- local Git whitespace verification

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
- plugin registration and docker construction
- direct `Document.nodeByUniqueID()` resolution and compatibility fallback
- per-window canvas document binding
- in-memory rule-order rollback after a failed save
- Linux Mint publishing through `python3`
- explicit ZIP module-directory entry required by Krita's importer
- module discovery matching Krita's directory plus `__init__.py` algorithm

## Packaging regression fixed

Version 1.0.1 contained the correct files but omitted the explicit `sprite_visibility_rules/` directory member. Krita's importer therefore returned “No plugins found in archive.” Version 1.0.2 writes this directory entry and tests it directly.

## Remaining real-world test

The final proof is an interactive import and runtime test in the user's exact Krita Flatpak, desktop session, and plugin combination.
