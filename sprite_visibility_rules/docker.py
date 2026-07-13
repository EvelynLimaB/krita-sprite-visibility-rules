# SPDX-License-Identifier: GPL-3.0-or-later
"""Sprite Visibility Rules docker."""

from __future__ import annotations

from typing import List, Optional

from krita import DockWidget, Krita

from .controller import ScanReport, VisibilityController
from .dialogs import RuleDialog
from .krita_adapter import node_ref, selected_nodes
from .models import NodeRef
from .qt_compat import (
    ACCEPTED,
    SELECT_ROWS,
    SINGLE_SELECTION,
    USER_ROLE,
    YES,
    QByteArray,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    exec_dialog,
)
from .storage import StorageError
from .version import __version__


class SpriteVisibilityRulesDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Visibility Rules")
        self.app = Krita.instance()
        self.controller = VisibilityController(QByteArray)

        root = QWidget(self)
        layout = QVBoxLayout(root)

        title = QLabel("Linked layer visibility for sprite and game-art files", root)
        title.setWordWrap(True)
        layout.addWidget(title)

        self.document_label = QLabel("No document", root)
        layout.addWidget(self.document_label)

        self.rule_tree = QTreeWidget(root)
        self.rule_tree.setColumnCount(4)
        self.rule_tree.setHeaderLabels(["Rule", "Type", "Layers", "Status"])
        self.rule_tree.setSelectionBehavior(SELECT_ROWS)
        self.rule_tree.setSelectionMode(SINGLE_SELECTION)
        self.rule_tree.itemDoubleClicked.connect(lambda *_args: self.edit_rule())
        layout.addWidget(self.rule_tree)

        first_row = QHBoxLayout()
        self.add_button = QPushButton("Add from selected layers…", root)
        self.edit_button = QPushButton("Edit", root)
        self.rebind_button = QPushButton("Rebind", root)
        self.remove_button = QPushButton("Remove", root)
        first_row.addWidget(self.add_button)
        first_row.addWidget(self.edit_button)
        first_row.addWidget(self.rebind_button)
        first_row.addWidget(self.remove_button)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        self.toggle_button = QPushButton("Enable / disable", root)
        self.up_button = QPushButton("Move up", root)
        self.down_button = QPushButton("Move down", root)
        self.enforce_button = QPushButton("Enforce now", root)
        second_row.addWidget(self.toggle_button)
        second_row.addWidget(self.up_button)
        second_row.addWidget(self.down_button)
        second_row.addWidget(self.enforce_button)
        layout.addLayout(second_row)

        settings_row = QHBoxLayout()
        self.pause_checkbox = QCheckBox("Pause automatic rules", root)
        self.interval_spin = QSpinBox(root)
        self.interval_spin.setRange(50, 1000)
        self.interval_spin.setSingleStep(25)
        stored_interval = int(
            self.app.readSetting("sprite_visibility_rules", "poll_interval_ms", "125")
        )
        self.interval_spin.setValue(max(50, min(1000, stored_interval)))
        settings_row.addWidget(self.pause_checkbox)
        settings_row.addWidget(QLabel("Poll ms:", root))
        settings_row.addWidget(self.interval_spin)
        layout.addLayout(settings_row)

        self.status_label = QLabel("Ready — plugin v{}".format(__version__), root)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setWidget(root)

        self.add_button.clicked.connect(self.add_rule)
        self.edit_button.clicked.connect(self.edit_rule)
        self.rebind_button.clicked.connect(self.rebind_rule)
        self.remove_button.clicked.connect(self.remove_rule)
        self.toggle_button.clicked.connect(self.toggle_rule)
        self.up_button.clicked.connect(lambda: self.move_rule(-1))
        self.down_button.clicked.connect(lambda: self.move_rule(1))
        self.enforce_button.clicked.connect(self.enforce_now)
        self.pause_checkbox.toggled.connect(self._set_paused)
        self.interval_spin.valueChanged.connect(self._set_interval)

        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_spin.value())
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._switch_document()

    def canvasChanged(self, _canvas):
        self._switch_document()

    def _current_document(self):
        return self.app.activeDocument()

    def _switch_document(self) -> None:
        document = self._current_document()
        changed = self.controller.set_document(document)
        if document is None:
            self.document_label.setText("No document")
        else:
            name = str(document.name() or document.fileName() or "Untitled")
            self.document_label.setText("Document: {}".format(name))
        if changed:
            self.refresh_tree()
            if self.controller.last_error:
                self._set_status(self.controller.last_error, error=True)
            elif self.controller.load_warnings:
                self._set_status(" ".join(self.controller.load_warnings), warning=True)
            else:
                self._set_status(
                    "Loaded {} rule{} from this document.".format(
                        len(self.controller.rules), "" if len(self.controller.rules) == 1 else "s"
                    )
                )

    def _tick(self) -> None:
        self._switch_document()
        report = self.controller.scan()
        if report.message or report.warnings or report.missing_ids:
            self._show_report(report)
            self.refresh_tree()

    def _set_status(self, text: str, warning: bool = False, error: bool = False) -> None:
        prefix = "Error: " if error else "Warning: " if warning else ""
        self.status_label.setText(prefix + text)

    def _show_report(self, report: ScanReport) -> None:
        parts: List[str] = []
        if report.message:
            parts.append(report.message)
        parts.extend(report.warnings)
        if report.missing_ids:
            parts.append(
                "{} linked layer{} missing; use Rebind after recreating them.".format(
                    len(report.missing_ids), " is" if len(report.missing_ids) == 1 else "s are"
                )
            )
        if parts:
            self._set_status(" ".join(parts), warning=bool(report.warnings or report.missing_ids))

    def _selected_rule_index(self) -> Optional[int]:
        items = self.rule_tree.selectedItems()
        if not items:
            return None
        value = items[0].data(0, USER_ROLE)
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        return index if 0 <= index < len(self.controller.rules) else None

    def _selected_refs(self) -> List[NodeRef]:
        nodes = selected_nodes(self.app)
        unique = []
        seen = set()
        for node in nodes:
            ref = node_ref(node)
            if ref.node_id not in seen:
                seen.add(ref.node_id)
                unique.append(ref)
        return unique

    def _save_and_refresh(self, enforce: bool = False) -> bool:
        try:
            self.controller.save()
        except StorageError as exc:
            QMessageBox.critical(self, "Could not save rules", str(exc))
            return False
        if enforce:
            self._show_report(self.controller.enforce_now())
        self.refresh_tree()
        return True

    def add_rule(self) -> None:
        refs = self._selected_refs()
        if len(refs) < 2:
            QMessageBox.information(
                self,
                "Select layers first",
                "Select at least two layers in Krita's Layers docker, then try again.",
            )
            return
        dialog = RuleDialog(refs, parent=self)
        if exec_dialog(dialog) != ACCEPTED:
            return
        self.controller.rules.append(dialog.build_rule())
        if not self._save_and_refresh(enforce=True):
            self.controller.rules.pop()

    def edit_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        existing = self.controller.rules[index]
        dialog = RuleDialog(list(existing.members), existing=existing, parent=self)
        if exec_dialog(dialog) != ACCEPTED:
            return
        old = existing
        self.controller.rules[index] = dialog.build_rule()
        if not self._save_and_refresh(enforce=True):
            self.controller.rules[index] = old

    def rebind_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        refs = self._selected_refs()
        rule = self.controller.rules[index]
        if len(refs) < 2 or (rule.kind.value == "inverse" and len(refs) != 2):
            QMessageBox.information(
                self,
                "Invalid selection",
                "Select at least two layers; inverse pairs require exactly two.",
            )
            return
        old_members = rule.members
        old_fallback = rule.fallback_id
        rule.members = refs
        if rule.kind.value == "exclusive" and not rule.allow_none:
            rule.fallback_id = refs[0].node_id
        if not self._save_and_refresh(enforce=True):
            rule.members = old_members
            rule.fallback_id = old_fallback

    def remove_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        rule = self.controller.rules[index]
        answer = QMessageBox.question(
            self,
            "Remove rule",
            "Remove the rule '{}'? This only removes the link; it does not delete layers.".format(
                rule.name
            ),
        )
        if answer != YES:
            return
        removed = self.controller.rules.pop(index)
        if not self._save_and_refresh():
            self.controller.rules.insert(index, removed)

    def toggle_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        rule = self.controller.rules[index]
        rule.enabled = not rule.enabled
        if not self._save_and_refresh(enforce=rule.enabled):
            rule.enabled = not rule.enabled

    def move_rule(self, offset: int) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        target = index + offset
        if target < 0 or target >= len(self.controller.rules):
            return
        self.controller.rules[index], self.controller.rules[target] = (
            self.controller.rules[target],
            self.controller.rules[index],
        )
        if self._save_and_refresh():
            self.rule_tree.setCurrentItem(self.rule_tree.topLevelItem(target))

    def enforce_now(self) -> None:
        self._show_report(self.controller.enforce_now())
        self.refresh_tree()

    def _set_paused(self, paused: bool) -> None:
        self.controller.paused = bool(paused)
        self._set_status("Automatic rules paused." if paused else "Automatic rules resumed.")
        if not paused:
            self.controller.snapshot()

    def _set_interval(self, value: int) -> None:
        self.timer.setInterval(value)
        self.app.writeSetting("sprite_visibility_rules", "poll_interval_ms", str(value))

    def refresh_tree(self) -> None:
        selected_index = self._selected_rule_index()
        self.rule_tree.clear()
        missing = set()
        if self.controller.document is not None:
            nodes, _states = self.controller._nodes_and_states()
            missing = self.controller.tracked_ids().difference(nodes.keys())
        conflicts = self.controller.conflicts()

        for index, rule in enumerate(self.controller.rules):
            missing_count = sum(member.node_id in missing for member in rule.members)
            conflict_count = sum(member.node_id in conflicts for member in rule.members)
            statuses = []
            if not rule.enabled:
                statuses.append("Disabled")
            if missing_count:
                statuses.append("{} missing".format(missing_count))
            if conflict_count:
                statuses.append("Overlaps")
            if not statuses:
                statuses.append("Ready")
            item = QTreeWidgetItem(
                [
                    rule.name,
                    rule.kind.label,
                    str(len(rule.members)),
                    ", ".join(statuses),
                ]
            )
            item.setData(0, USER_ROLE, index)
            self.rule_tree.addTopLevelItem(item)
        self.rule_tree.resizeColumnToContents(0)
        self.rule_tree.resizeColumnToContents(1)
        if selected_index is not None and selected_index < self.rule_tree.topLevelItemCount():
            self.rule_tree.setCurrentItem(self.rule_tree.topLevelItem(selected_index))
