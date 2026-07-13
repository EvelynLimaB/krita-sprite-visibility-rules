# SPDX-License-Identifier: GPL-3.0-or-later
"""Small PyQt5/PyQt6 compatibility layer."""

try:
    from PyQt5.QtCore import QByteArray, QEvent, QObject, Qt, QTimer, QUuid
    from PyQt5.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_MAJOR = 5
    USER_ROLE = Qt.UserRole
    SELECT_ROWS = QAbstractItemView.SelectRows
    SINGLE_SELECTION = QAbstractItemView.SingleSelection
    ACCEPTED = QDialog.Accepted
    OK = QDialogButtonBox.Ok
    CANCEL = QDialogButtonBox.Cancel
    YES = QMessageBox.Yes
    PRECISE_TIMER = Qt.PreciseTimer
    COARSE_TIMER = Qt.CoarseTimer
    MOUSE_BUTTON_RELEASE = QEvent.MouseButtonRelease
    SHORTCUT_EVENT = QEvent.Shortcut
except ImportError:
    from PyQt6.QtCore import QByteArray, QEvent, QObject, Qt, QTimer, QUuid
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_MAJOR = 6
    USER_ROLE = Qt.ItemDataRole.UserRole
    SELECT_ROWS = QAbstractItemView.SelectionBehavior.SelectRows
    SINGLE_SELECTION = QAbstractItemView.SelectionMode.SingleSelection
    ACCEPTED = QDialog.DialogCode.Accepted
    OK = QDialogButtonBox.StandardButton.Ok
    CANCEL = QDialogButtonBox.StandardButton.Cancel
    YES = QMessageBox.StandardButton.Yes
    PRECISE_TIMER = Qt.TimerType.PreciseTimer
    COARSE_TIMER = Qt.TimerType.CoarseTimer
    MOUSE_BUTTON_RELEASE = QEvent.Type.MouseButtonRelease
    SHORTCUT_EVENT = QEvent.Type.Shortcut


def exec_dialog(dialog):
    """Execute a dialog on both older PyQt5 and PyQt6 bindings."""
    method = getattr(dialog, "exec", None)
    if method is None:
        method = dialog.exec_
    return method()


__all__ = [
    "ACCEPTED",
    "CANCEL",
    "COARSE_TIMER",
    "MOUSE_BUTTON_RELEASE",
    "OK",
    "PRECISE_TIMER",
    "QAbstractItemView",
    "QApplication",
    "QByteArray",
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QDialogButtonBox",
    "QEvent",
    "QFormLayout",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QMessageBox",
    "QObject",
    "QPushButton",
    "QSpinBox",
    "QTimer",
    "QUuid",
    "QTreeWidget",
    "QTreeWidgetItem",
    "QVBoxLayout",
    "QWidget",
    "QT_MAJOR",
    "SELECT_ROWS",
    "SHORTCUT_EVENT",
    "SINGLE_SELECTION",
    "USER_ROLE",
    "YES",
    "exec_dialog",
]
