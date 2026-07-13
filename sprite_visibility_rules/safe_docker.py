# SPDX-License-Identifier: GPL-3.0-or-later
"""Render-stable wrapper around the optimized visibility docker."""

from __future__ import annotations

from .docker import SpriteVisibilityRulesDocker as _OptimizedDocker
from .qt_compat import PRECISE_TIMER, QTimer

# Give Krita roughly two 60 Hz frames to finish its own layer-toggle and
# projection scheduling before the plugin applies dependent visibility writes.
INPUT_SETTLE_MS = 32
MINIMUM_FALLBACK_POLL_MS = 50


class SpriteVisibilityRulesDocker(_OptimizedDocker):
    """Use the optimized engine with a render-safe input debounce."""

    def __init__(self):
        super().__init__()

        self._input_settle_timer = QTimer(self)
        self._input_settle_timer.setSingleShot(True)
        self._input_settle_timer.setTimerType(PRECISE_TIMER)
        self._input_settle_timer.setInterval(INPUT_SETTLE_MS)
        self._input_settle_timer.timeout.connect(self._run_pending_scan)

        # Extremely short fallback polling can compete with Krita's projection
        # work on complex canvases. Normal layer-list input still wakes through
        # the settle timer, so 50 ms remains responsive while avoiding the most
        # aggressive idle setting.
        self.interval_spin.setMinimum(MINIMUM_FALLBACK_POLL_MS)
        if self.interval_spin.value() < MINIMUM_FALLBACK_POLL_MS:
            self.interval_spin.setValue(MINIMUM_FALLBACK_POLL_MS)

    def request_scan(self) -> None:
        """Coalesce input and scan after Krita's own UI transaction settles."""

        self._scan_pending = True
        self._input_settle_timer.start()
