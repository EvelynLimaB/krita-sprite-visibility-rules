# SPDX-License-Identifier: GPL-3.0-or-later
"""One application-wide, non-consuming visibility input event broker."""

from __future__ import annotations

from weakref import WeakSet

from .qt_compat import QObject


class InputEventBroker(QObject):
    """Route relevant Qt input events to each docker in the matching window."""

    def __init__(self, application):
        super().__init__(application)
        self.application = application
        self._dockers = WeakSet()
        application.installEventFilter(self)

    def register(self, docker) -> None:
        self._dockers.add(docker)

    def unregister(self, docker) -> None:
        self._dockers.discard(docker)

    @property
    def registered_count(self) -> int:
        return len(self._dockers)

    def eventFilter(self, watched, event):
        for docker in tuple(self._dockers):
            try:
                if docker._input_should_wake(watched, event):
                    docker.request_scan()
            except (ReferenceError, RuntimeError):
                self._dockers.discard(docker)
            except Exception:
                # Monitoring must never consume or disturb Krita's event path.
                pass
        return False


_broker = None


def get_input_event_broker(application):
    global _broker
    if _broker is None or _broker.application is not application:
        _broker = InputEventBroker(application)
    return _broker
