# Sprite Visibility Rules 1.1.1

Render-stability patch for the 1.1 responsiveness work.

## Fixed

Some Krita canvases could display a stale or incomplete intermediate projection after rapid linked visibility changes. Version 1.1.0 applied dependent layer visibility at the next event-loop opportunity and removed the explicit projection refresh used by earlier releases. That combination was too aggressive for some documents and rendering paths.

Version 1.1.1:

- waits 32 ms after layer-list or shortcut input before enforcing dependent visibility;
- coalesces rapid input into one rule batch;
- performs one `Document.refreshProjection()` after the complete plugin-generated visibility batch;
- raises the minimum fallback polling interval from 25 ms to 50 ms.

## Performance retained

The release keeps the safe 1.1.0 optimizations:

- cached UUID-resolved Krita node wrappers;
- compiled layer-to-rule dispatch;
- affected-rule-only cascade processing;
- no repeated full tracked-node readback;
- no docker-tree rebuild after ordinary successful corrections.

## Compatibility

- Inverse, exclusive, linked, cascade, conflict, persistence, rebind, and document-scoping behavior is unchanged.
- The `.kra` annotation schema remains version 1 and is compatible with every previous release.
- The Krita importer packaging fix from 1.0.2 remains included.

## Install

Use the release asset named `sprite_visibility_rules-1.1.1.zip`. Do not use GitHub's automatically generated “Source code” ZIPs.
