# Sprite Visibility Rules 1.2.0

Interoperability, idle-efficiency, and multi-window correctness upgrade.

## External-plugin compatibility

The event-assisted scan now uses two stages:

1. return control to the Qt event loop so the current Krita or external-plugin action can finish;
2. wait the existing 32 ms render-settle interval before evaluating dependent rules.

This prevents the settle countdown from expiring inside a long synchronous action such as a multi-layer visibility toggle. Valid results from other plugins remain untouched. Invalid governed states still receive only the minimum dependent correction and one projection refresh.

Sprite Visibility Rules continues to avoid duplicating adjacent-layer navigation, selected-layer toggle, or label-color toggle commands.

## Lower idle work

- One application-wide event broker now serves all Sprite Visibility Rules dockers.
- Fallback polling stops when no document is open, no rule is enabled, or automatic rules are paused.
- Mouse events inside the plugin's own rule tree no longer schedule scans.
- Rule indexes are rebuilt from explicit revisions instead of reconstructing a complete signature every scan.

## Multi-window safety

Rule creation and rebinding now read selected nodes from the docker's own canvas view before falling back to Krita's active window. A docker in one window therefore cannot accidentally bind layers selected in another window.

## Internal cleanup

The temporary `safe_docker.py` subclass has been removed. Scheduling, rendering safety, and the optimized docker behavior now live in one implementation supported by dedicated scheduler and event-broker components.

## Compatibility

- The `.kra` annotation schema remains version 1.
- Existing inverse, exclusive, linked, cascade, conflict, persistence, and rebind behavior is unchanged.
- Existing files created with every 1.0.x and 1.1.x release remain compatible.
- The Krita importer packaging fix from 1.0.2 remains included.

## Install

Use the release asset named `sprite_visibility_rules-1.2.0.zip`. Do not use GitHub's automatically generated “Source code” ZIPs.
