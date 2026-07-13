# Sprite Visibility Rules 1.1.0

Responsiveness and hot-path optimization release.

## Faster interaction

- Layers-docker and Compositions-docker mouse input now schedules an immediate coalesced scan at the next Qt event-loop opportunity.
- Shortcut events also wake the scanner immediately.
- The configurable timer remains as a fallback for visibility changes made by other plugins or unusual UI paths.
- Normal clicks no longer wait for the next 125 ms polling boundary.

## Less work per scan

- Tracked Krita node wrappers are cached briefly instead of being resolved by UUID on every tick.
- Rule membership is compiled into a dispatch index and rebuilt only when rule configuration changes.
- Cascades evaluate only rules affected by the changed layers.
- The controller reads back only layers it changed rather than resolving and rereading the entire tracked set again.
- The docker is no longer rebuilt after every successful rule correction.
- The plugin no longer calls `refreshProjection()` after visibility changes because Krita's own visibility setter already notifies the node graph and invalidates frames.

## Compatibility and safety

- Inverse, exclusive, linked, cascade, conflict, persistence, rebind, and document-scoping behavior is unchanged.
- Polling remains available and configurable from 25 to 1000 ms.
- The `.kra` annotation schema remains version 1 and is compatible with all 1.0.x files.
- The Krita importer packaging fix from 1.0.2 remains included.

## Install

Use the release asset named `sprite_visibility_rules-1.1.0.zip`. Do not use GitHub's automatically generated “Source code” ZIPs.
