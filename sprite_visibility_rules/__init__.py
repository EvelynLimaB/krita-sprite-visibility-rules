# SPDX-FileCopyrightText: 2026 Evelyn Lima
# SPDX-License-Identifier: GPL-3.0-or-later
"""Krita plugin registration.

The guarded import lets the pure rule/storage modules be unit-tested without a
Krita installation. Krita itself imports this package with the ``krita`` module
available and registers the docker exactly once.
"""

_REGISTERED = False

try:
    from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita
except ImportError:  # pragma: no cover - expected in standalone unit tests
    pass
else:
    from .safe_docker import SpriteVisibilityRulesDocker

    if not _REGISTERED:
        Krita.instance().addDockWidgetFactory(
            DockWidgetFactory(
                "sprite_visibility_rules_docker",
                DockWidgetFactoryBase.DockRight,
                SpriteVisibilityRulesDocker,
            )
        )
        _REGISTERED = True
