# SPDX-License-Identifier: GPL-3.0-or-later
"""Render-safe scan scheduling for visibility rules."""

from __future__ import annotations

from typing import Callable

from .qt_compat import COARSE_TIMER, PRECISE_TIMER, QObject, QTimer

INPUT_SETTLE_MS = 32
MINIMUM_FALLBACK_POLL_MS = 50


class ScanScheduler(QObject):
    """Coordinate delayed input scans and low-frequency fallback polling."""

    def __init__(
        self,
        parent,
        scan_callback: Callable[[bool], None],
        interval_ms: int = 125,
        settle_ms: int = INPUT_SETTLE_MS,
    ):
        super().__init__(parent)
        self._scan_callback = scan_callback
        self._active = False
        self._pending = False
        self._arm_pending = False

        self.fallback_timer = QTimer(self)
        self.fallback_timer.timeout.connect(self._run_fallback)

        self.settle_timer = QTimer(self)
        self.settle_timer.setSingleShot(True)
        self.settle_timer.setTimerType(PRECISE_TIMER)
        self.settle_timer.setInterval(max(0, int(settle_ms)))
        self.settle_timer.timeout.connect(self._run_settled)

        self.set_interval(interval_ms)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def pending(self) -> bool:
        return self._pending or self._arm_pending or self.settle_timer.isActive()

    def set_interval(self, value: int) -> None:
        value = max(MINIMUM_FALLBACK_POLL_MS, int(value))
        timer_type = PRECISE_TIMER if value <= 125 else COARSE_TIMER
        self.fallback_timer.setTimerType(timer_type)
        self.fallback_timer.setInterval(value)

    def set_active(self, active: bool) -> bool:
        active = bool(active)
        changed = active != self._active
        self._active = active
        if active:
            if not self.fallback_timer.isActive():
                self.fallback_timer.start()
        else:
            self.fallback_timer.stop()
            self.settle_timer.stop()
            self._pending = False
            self._arm_pending = False
        return changed

    def request_after_input(self) -> None:
        """Start settling only after the current external action has returned."""

        if not self._active:
            return
        self._pending = True
        if self._arm_pending:
            return
        self._arm_pending = True
        QTimer.singleShot(0, self._arm_settle_timer)

    def _arm_settle_timer(self) -> None:
        self._arm_pending = False
        if self._active and self._pending:
            self.settle_timer.start()

    def _run_settled(self) -> None:
        if not self._active or not self._pending:
            return
        self._pending = False
        self._scan_callback(False)

    def _run_fallback(self) -> None:
        if not self._active or self.pending:
            return
        self._scan_callback(True)

    def dispose(self) -> None:
        self.set_active(False)
