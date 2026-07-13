# Krita documentation and API audit

Audit target: Sprite Visibility Rules 1.0.2  
Date: 2026-07-13

## Official references checked

- Krita manual: Python plugin recognition, `.desktop` descriptors, module folders, docker registration, and plugin enabling.
- Krita manual: Python plugin importer ZIP structure.
- Krita 6.0.2.1 PyKrita SIP API: `DockWidget`, `DockWidgetFactoryBase`, `Document`, `Node`, `View`, `Canvas`, and `Notifier`.
- Krita 6.0.2.1 built-in Python plugin importer implementation.
- Current Flathub manifest for `org.kde.krita`.

## Confirmed compatible surfaces

- Importer ZIP contains `sprite_visibility_rules.desktop`, an explicit `sprite_visibility_rules/` directory entry, and a matching module with `__init__.py`.
- Descriptor uses `Type=Service`, `ServiceTypes=Krita/PythonPlugin`, and a matching `X-KDE-Library`.
- Docker subclasses `DockWidget`, implements `canvasChanged`, and registers through `DockWidgetFactory`.
- Selected layers are read through `View.selectedNodes()`.
- Layer identity and visibility use `Node.uniqueId()`, `visible()`, and `setVisible()`.
- Rules persist through `Document.annotationTypes()`, `annotation()`, and `setAnnotation()`.
- `Document.setModified(True)` ensures the user is prompted to save rule changes.
- The current Krita Flatpak uses Python 3.13 and PyQt5, matching the plugin's primary import path.

## Importer packaging finding

Krita's built-in importer does not infer the module directory merely from paths such as `sprite_visibility_rules/__init__.py`. It first searches the ZIP member list for an explicit directory named after `X-KDE-Library`, then checks for `__init__.py`. Version 1.0.2 adds that explicit directory member and a regression test matching the importer logic.

## Why polling remains necessary

Krita 6.0.2.1's public `Notifier` API does not expose a node-visibility-changed signal. The plugin therefore polls only rule-member visibility. Tracked layers are resolved through `Document.nodeByUniqueID()` when available, avoiding repeated full-tree traversal.

## Known limits

- Multiple visibility changes inside one polling interval are resolved deterministically, not chronologically. The active layer wins when it is one of the changed members; otherwise rule/member order is used.
- Rules stored in annotations are intended for `.kra` files. Export-only formats should not be expected to preserve them.
- The final proof remains an interactive test in the exact graphical Flatpak installation and desktop session.
