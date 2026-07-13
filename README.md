# Krita Sprite Visibility Rules

A Krita docker for game-art and sprite files where layer visibility needs to behave like state logic.

## V1 features

- **Inverse pair:** hiding A shows B; showing A hides B, and vice versa.
- **Exclusive set:** showing one expression/outfit layer hides every other member.
- **Linked set:** hiding or showing one layer applies the same state to every member.
- Detects changes made through Krita's normal eye icons, shortcuts, compositions, or other plugins.
- Embeds rules in the `.kra` document using Krita document annotations.
- Uses Krita node UUIDs, so renaming or moving a linked layer does not break the rule.
- Missing-layer warnings and **Rebind** support after a layer is deleted/recreated.
- Rule ordering, per-rule enable/disable, global pause, and configurable polling interval.
- Cycle detection: contradictory overlapping rules are reported instead of flickering forever.
- PyQt5/PyQt6 import compatibility and a Flatpak installation helper.

## Install in Krita

Download `sprite_visibility_rules-1.0.0.zip` from the release assets, then:

1. Open **Tools → Scripts → Import Python Plugin…**.
2. Select the ZIP and restart Krita.
3. Open **Settings → Configure Krita → Python Plugin Manager**.
4. Enable **Sprite Visibility Rules** and restart Krita again.
5. Open **Settings → Dockers → Sprite Visibility Rules**.

### Flatpak helper

From a source checkout:

```bash
./scripts/install-flatpak.sh
```

It installs into:

```text
~/.var/app/org.kde.krita/data/krita/pykrita
```

## First test: an inverse pair

1. Create two layers, for example `eyes_open` and `eyes_closed`.
2. Make one visible and one hidden.
3. Select both in the Layers docker.
4. Press **Add from selected layers…**.
5. Select **Inverse pair** and save the rule.
6. Click either normal eye icon. The other layer should immediately switch to the opposite state.
7. Save the `.kra`, close it, reopen it, and verify the rule reloads.

## Rule semantics

### Inverse pair

Exactly two layers always have opposite visibility:

```text
A visible  <=> B hidden
A hidden   <=> B visible
```

### Exclusive set

Showing one member hides all other members. With **Allow every layer hidden** disabled, the configured fallback is restored when the set would otherwise become empty.

### Linked set

The changed member becomes the driver and every other existing member receives the same visibility.

## Limits of V1

Krita's public Python API exposes `Node.visible()` and `Node.setVisible()` but no layer-visibility-changed signal. V1 therefore checks only linked layers on a short timer (125 ms by default). It does not inspect pixels or redraw the canvas itself.

An operation that changes several linked members in the same polling window is resolved deterministically: Krita's active layer wins when possible, then rule/member order. Overlapping rules are legal, but contradictory overlaps may be rejected as a cycle.

## Verification

The repository contains pure-Python tests for:

- both directions of inverse pairs;
- linked and exclusive behavior;
- strict fallback behavior;
- missing layers;
- cascaded rules;
- cycle detection;
- annotation serialization and malformed data;
- normal-eye-click simulation through the controller;
- Krita importer ZIP layout.

Run the complete local verification suite:

```bash
python scripts/verify_release.py
```

The GitHub Actions workflow runs linting, package tests, Flatpak installer tests, and the offscreen Qt docker smoke test. See `TEST_REPORT.md` for the V1 verification record.

The GitHub Actions workflow runs the same checks on Python 3.10–3.13.

## Safety

Test V1 on a copy of an important `.kra` file. The plugin stores only JSON rule configuration in a document annotation and changes only the `visible` property of participating layers. Removing a rule never deletes a layer.

## License

GPL-3.0-or-later.

## Publishing the prepared repository

After installing and authenticating GitHub CLI, the included helper creates the repository under `EvelynLimaB`, pushes `main` and tag `v1.0.0`, and uploads the plugin ZIP and checksum as a GitHub release:

```bash
gh auth login
./scripts/publish-github.sh
```
