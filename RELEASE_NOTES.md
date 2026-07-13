# Sprite Visibility Rules 1.0.2

Packaging-fix release for Krita's built-in Python Plugin Importer.

## Fixed

Krita 6 could open the 1.0.1 ZIP but reported **“No plugins found in archive.”** The files were at the correct paths, but the deterministic ZIP builder omitted the explicit `sprite_visibility_rules/` directory member. Krita's importer searches for that directory entry before checking `sprite_visibility_rules/__init__.py`.

Version 1.0.2 writes the required directory entry and includes regression tests matching Krita's importer discovery logic.

## Plugin functionality

- Inverse pairs: each member always has the opposite visibility of the other.
- Exclusive sets: showing one member hides the other members.
- Linked sets: showing or hiding one member applies the same state to the set.
- Detection of changes made through Krita's normal layer visibility controls.
- Rule data embedded inside each `.kra` file through a Krita document annotation.
- UUID-based layer references, missing-layer reporting, and layer rebinding.
- Rule ordering, enable/disable, global pause, polling interval, and manual enforcement.
- Conflict/cycle protection to prevent endless visibility oscillation.

The rule schema remains version 1 and is compatible with files created by 1.0.0 and 1.0.1.

## Install

Use the release asset named `sprite_visibility_rules-1.0.2.zip`. Do not use GitHub's automatically generated “Source code” ZIPs.
