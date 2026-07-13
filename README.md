# Krita Sprite Visibility Rules

A Krita docker for game-art and sprite files where layer visibility needs to behave like state logic.

## Features

- **Inverse pair:** hiding A shows B; showing A hides B, and vice versa.
- **Exclusive set:** showing one expression/outfit layer hides every other member.
- **Linked set:** hiding or showing one layer applies the same state to every member.
- Detects changes made through Krita's normal eye icons, shortcuts, compositions, or other plugins.
- Uses event-assisted scanning with a short render-settle delay while retaining polling as a compatibility fallback.
- Embeds rules in the `.kra` document using Krita document annotations.
- Uses Krita node UUIDs, so renaming or moving a linked layer does not break the rule.
- Missing-layer warnings and **Rebind** support after a layer is deleted/recreated.
- Rule ordering, per-rule enable/disable, global pause, and configurable fallback polling interval.
- Cycle detection: contradictory overlapping rules are reported instead of flickering forever.
- PyQt5 support for the current Krita Flatpak, a conservative PyQt6 fallback, and a Flatpak installation helper.

## Install in Krita

Download the release asset named `sprite_visibility_rules-1.1.1.zip`, then:

1. Open **Tools → Scripts → Import Python Plugin…**.
2. Select the ZIP and restart Krita.
3. Open **Settings → Configure Krita → Python Plugin Manager**.
4. Enable **Sprite Visibility Rules** and restart Krita again.
5. Open **Settings → Dockers → Sprite Visibility Rules**.

Do **not** use GitHub's automatically generated **Source code (zip)** download. Use the specifically named plugin asset from the release.

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
6. Click either normal eye icon. The other layer should switch to the opposite state after the short render-settle delay.
7. Save the `.kra`, close it, reopen it, and verify the rule reloads.

## Responsiveness and render safety

Version 1.1 uses an event-assisted fast path. Version 1.1.1 waits 32 ms after Layers/Compositions mouse input or a shortcut before enforcing dependent visibility. Rapid input is coalesced into one batch. This gives Krita time to finish its own layer-toggle transaction and projection scheduling before the plugin changes related layers.

After a plugin-generated visibility batch, the controller requests one `Document.refreshProjection()`. It does not refresh after every individual layer, resolve all tracked nodes again, or rebuild the docker tree.

The fallback interval defaults to 125 ms and cannot be set below 50 ms. Since ordinary Layers-docker input uses the event-assisted path, increasing the fallback to 250–500 ms can reduce idle API traffic without noticeably slowing normal eye-icon clicks.

The optimized hot path still:

- caches resolved Krita node wrappers for a short period;
- compiles rule membership and dispatch indexes only when rules change;
- evaluates only rules touched by the changed layers;
- avoids a second complete node-resolution pass after enforcement;
- avoids rebuilding the docker after every successful visibility correction.

Run the synthetic rule-dispatch benchmark:

```bash
python3 scripts/benchmark_hot_path.py
```

The benchmark isolates pure rule dispatch. It is not a canvas-rendering or GPU benchmark.

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

## Limits

Krita's public Python API exposes `Node.visible()` and `Node.setVisible()` but no layer-visibility-changed signal. Event-assisted scanning therefore supplements rather than replaces polling.

Tracked node wrappers are refreshed approximately twice per second and immediately after rule/document changes. A newly deleted layer can consequently take up to about half a second to be reported as missing, while visibility changes continue to use the fast cached path.

An operation that changes several linked members in the same scan window is resolved deterministically: Krita's active layer wins when possible, then rule/member order. Overlapping rules are legal, but contradictory overlaps may be rejected as a cycle.

## Verification

Run the complete local verification suite:

```bash
python3 scripts/verify_release.py
```

The release builder writes the explicit `sprite_visibility_rules/` ZIP directory entry required by Krita's own importer, and the package tests mirror Krita's directory-and-`__init__.py` discovery algorithm.

The GitHub Actions workflows run linting, package tests, Flatpak installer tests, the offscreen Qt docker smoke test, deterministic ZIP checks, and automatic release publishing.

## Safety

Test the plugin on a copy of an important `.kra` file. It stores only JSON rule configuration in a document annotation and changes only the `visible` property of participating layers. Removing a rule never deletes a layer.

## License

GPL-3.0-or-later.
