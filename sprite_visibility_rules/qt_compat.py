# SPDX-License-Identifier: GPL-3.0-or-later
"""Small PyQt5/PyQt6 compatibility layer.

Krita's current public Python examples and many production builds expose
PyQt5. PyQt6 is supported as a fallback for builds that migrate the bindings.
"""

try:
    from PyQt5.QtCore import QByteArray, Qt, QTimer
    from PyQt5.QtWidgets import (
        QAbstractItemView,
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
except ImportError:  # Future/alternate Krita builds may expose PyQt6.
    from PyQt6.QtCore import QByteArray, Qt, QTimer
    from PyQt6.QtWidgets import (
        QAbstractItemView,
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


def exec_dialog(dialog):
    """Execute a dialog on both older PyQt5 and PyQt6 bindings."""
    method = getattr(dialog, "exec", None)
    if method is None:
        method = dialog.exec_
    return method()


__all__ = [
    "ACCEPTED",
    "CANCEL",
    "OK",
    "QAbstractItemView",
    "QByteArray",
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QDialogButtonBox",
    "QFormLayout",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QMessageBox",
    "QPushButton",
    "QSpinBox",
    "QTimer",
    "QTreeWidget",
    "QTreeWidgetItem",
    "QVBoxLayout",
    "QWidget",
    "QT_MAJOR",
    "SELECT_ROWS",
    "SINGLE_SELECTION",
    "USER_ROLE",
    "YES",
    "exec_dialog",
]
