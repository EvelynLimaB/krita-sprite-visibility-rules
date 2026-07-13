# Sprite Visibility Rules 1.0.0

Initial proof-checked test release for Krita sprite and game-art workflows.

## Included

- Inverse pairs: each member always has the opposite visibility of the other.
- Exclusive sets: showing one member hides the other members.
- Linked sets: showing or hiding one member applies the same state to the set.
- Detection of changes made through Krita's normal layer visibility controls.
- Rule data embedded inside each `.kra` file through a Krita document annotation.
- UUID-based layer references, missing-layer reporting, and layer rebinding.
- Rule ordering, enable/disable, global pause, polling interval, and manual enforcement.
- Conflict/cycle protection to prevent endless visibility oscillation.
- Krita Flatpak installation helper.

## Test status

The release passed the checks recorded in `TEST_REPORT.md`. The docker was constructed in an offscreen PyQt5 test against a fake object surface matching the public Krita API. A real interactive run inside the user's particular Krita Flatpak remains the necessary final compatibility test.

## Safety note

Use a copy of an important `.kra` file for the first test. V1 changes only participating layers' visibility and stores JSON rule configuration in a document annotation.
