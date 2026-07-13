# SPDX-License-Identifier: GPL-3.0-or-later
"""Rule creation/editing dialogs."""

from __future__ import annotations

from typing import List, Optional

from .models import NodeRef, RuleKind, VisibilityRule
from .qt_compat import (
    CANCEL,
    OK,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
)


class RuleDialog(QDialog):
    def __init__(
        self, members: List[NodeRef], existing: Optional[VisibilityRule] = None, parent=None
    ):
        super().__init__(parent)
        self._members = members
        self._existing = existing
        self.setWindowTitle("Edit Visibility Rule" if existing else "Add Visibility Rule")
        self.resize(430, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(self)
        self.kind_combo = QComboBox(self)
        for kind in RuleKind:
            self.kind_combo.addItem(kind.label, kind.value)
        self.allow_none = QCheckBox("Allow every layer in the set to be hidden", self)
        self.fallback_combo = QComboBox(self)
        for member in members:
            self.fallback_combo.addItem(member.name, member.node_id)

        form.addRow("Name", self.name_edit)
        form.addRow("Rule type", self.kind_combo)
        form.addRow("Exclusive behavior", self.allow_none)
        form.addRow("Fallback layer", self.fallback_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Layers in this rule (in priority order):", self))
        member_list = QListWidget(self)
        for member in members:
            member_list.addItem(member.name)
        layout.addWidget(member_list)

        help_label = QLabel(
            "Exclusive: showing one hides the others.\n"
            "Linked: changing one applies the same state to all.\n"
            "Inverse: exactly two layers always have opposite states.",
            self,
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        buttons = QDialogButtonBox(OK | CANCEL, self)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.kind_combo.currentIndexChanged.connect(self._update_kind_controls)
        self.allow_none.toggled.connect(self._update_kind_controls)

        if existing:
            self.name_edit.setText(existing.name)
            index = self.kind_combo.findData(existing.kind.value)
            if index >= 0:
                self.kind_combo.setCurrentIndex(index)
            self.allow_none.setChecked(existing.allow_none)
            fallback_index = self.fallback_combo.findData(existing.fallback_id)
            if fallback_index >= 0:
                self.fallback_combo.setCurrentIndex(fallback_index)
        else:
            self.name_edit.setText(self._suggest_name())
            self.allow_none.setChecked(True)
        self._update_kind_controls()

    def _suggest_name(self) -> str:
        names = [member.name for member in self._members]
        return " / ".join(names[:2]) if names else "New rule"

    def _current_kind(self) -> RuleKind:
        return RuleKind(str(self.kind_combo.currentData()))

    def _update_kind_controls(self, *_args) -> None:
        exclusive = self._current_kind() == RuleKind.EXCLUSIVE
        self.allow_none.setEnabled(exclusive)
        self.fallback_combo.setEnabled(exclusive and not self.allow_none.isChecked())

    def _validate_and_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Invalid rule", "Enter a rule name.")
            return
        kind = self._current_kind()
        if len(self._members) < 2:
            QMessageBox.warning(self, "Invalid rule", "Select at least two layers in Krita.")
            return
        if kind == RuleKind.INVERSE and len(self._members) != 2:
            QMessageBox.warning(
                self, "Invalid inverse pair", "An inverse pair requires exactly two layers."
            )
            return
        self.accept()

    def build_rule(self) -> VisibilityRule:
        kind = self._current_kind()
        allow_none = self.allow_none.isChecked() if kind == RuleKind.EXCLUSIVE else True
        fallback_id = None
        if kind == RuleKind.EXCLUSIVE and not allow_none:
            fallback_id = str(self.fallback_combo.currentData())
        return (
            VisibilityRule(
                rule_id=self._existing.rule_id if self._existing else None,
                name=self.name_edit.text().strip(),
                kind=kind,
                members=list(self._members),
                enabled=self._existing.enabled if self._existing else True,
                allow_none=allow_none,
                fallback_id=fallback_id,
            )
            if self._existing
            else VisibilityRule(
                name=self.name_edit.text().strip(),
                kind=kind,
                members=list(self._members),
                enabled=True,
                allow_none=allow_none,
                fallback_id=fallback_id,
            )
        )
