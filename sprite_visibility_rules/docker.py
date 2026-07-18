# SPDX-License-Identifier: GPL-3.0-or-later
"""Sprite Visibility Rules docker."""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Set

from krita import DockWidget, Krita

from .controller import ScanReport, VisibilityController
from .dialogs import RuleDialog
from .event_broker import get_input_event_broker
from .krita_adapter import node_ref, selected_nodes_for_canvas
from .models import NodeRef
from .qt_compat import (
    ACCEPTED,
    MOUSE_BUTTON_RELEASE,
    SELECT_ROWS,
    SHORTCUT_EVENT,
    SINGLE_SELECTION,
    USER_ROLE,
    YES,
    QAbstractItemView,
    QApplication,
    QByteArray,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    exec_dialog,
)
from .scheduler import INPUT_SETTLE_MS, MINIMUM_FALLBACK_POLL_MS, ScanScheduler
from .storage import StorageError
from .version import __version__


class SpriteVisibilityRulesDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Visibility Rules")
        self.app = Krita.instance()
        self.controller = VisibilityController(QByteArray)
        self._canvas = None
        self._scan_running = False
        self._last_missing_ids: Set[str] = set()

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
        self.interval_spin.setRange(MINIMUM_FALLBACK_POLL_MS, 1000)
        self.interval_spin.setSingleStep(25)
        stored_interval = int(
            self.app.readSetting("sprite_visibility_rules", "poll_interval_ms", "125")
        )
        self.interval_spin.setValue(
            max(MINIMUM_FALLBACK_POLL_MS, min(1000, stored_interval))
        )
        settings_row.addWidget(self.pause_checkbox)
        settings_row.addWidget(QLabel("Fallback poll ms:", root))
        settings_row.addWidget(self.interval_spin)
        layout.addLayout(settings_row)

        self.status_label = QLabel(
            "Ready — plugin v{}; input scans wait for Krita to settle.".format(
                __version__
            ),
            root,
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setWidget(root)

        self.scheduler = ScanScheduler(
            self,
            lambda check_document: self._scan_once(check_document),
            interval_ms=self.interval_spin.value(),
            settle_ms=INPUT_SETTLE_MS,
        )
        # Kept as stable aliases for diagnostics and existing smoke tests.
        self.timer = self.scheduler.fallback_timer
        self._input_settle_timer = self.scheduler.settle_timer

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

        self._input_broker = None
        qt_application = QApplication.instance()
        if qt_application is not None:
            self._input_broker = get_input_event_broker(qt_application)
            self._input_broker.register(self)

        self._switch_document()

    def canvasChanged(self, canvas):
        self._canvas = canvas
        self._switch_document()

    def _current_document(self):
        if self._canvas is not None:
            try:
                view = self._canvas.view()
                if view is not None:
                    return view.document()
            except Exception:
                pass
        return self.app.activeDocument()

    def _switch_document(self) -> None:
        document = self._current_document()
        changed = self.controller.set_document(document)
        self._update_monitoring_state()
        if not changed:
            return

        if document is None:
            self.document_label.setText("No document")
        else:
            name = str(document.name() or document.fileName() or "Untitled")
            self.document_label.setText("Document: {}".format(name))
        self._last_missing_ids = set(self.controller.last_missing_ids)
        self.refresh_tree(missing=self._last_missing_ids)
        if self.controller.last_error:
            self._set_status(self.controller.last_error, error=True)
        elif self.controller.load_warnings:
            self._set_status(" ".join(self.controller.load_warnings), warning=True)
        else:
            self._set_status(
                "Loaded {} rule{} from this document.".format(
                    len(self.controller.rules),
                    "" if len(self.controller.rules) == 1 else "s",
                )
            )

    def _update_monitoring_state(self, refresh_snapshot: bool = False) -> None:
        should_monitor = (
            self.controller.document is not None
            and not self.controller.paused
            and self.controller.has_enabled_rules()
        )
        if should_monitor and refresh_snapshot:
            self.controller.snapshot(force_resolve=True)
        self.scheduler.set_active(should_monitor)

    def _is_same_window(self, watched) -> bool:
        try:
            watched_window = watched.window()
            docker_window = self.window()
        except Exception:
            return True
        return watched_window == docker_window

    def _belongs_to_this_docker(self, watched) -> bool:
        current = watched
        root_widget = self.widget()
        for _depth in range(20):
            if current is self or current is root_widget:
                return True
            parent_widget = getattr(current, "parentWidget", None)
            if parent_widget is None:
                return False
            current = parent_widget()
            if current is None:
                return False
        return False

    @staticmethod
    def _is_item_view_or_child(watched) -> bool:
        current = watched
        for _depth in range(10):
            if isinstance(current, QAbstractItemView):
                return True
            parent_widget = getattr(current, "parentWidget", None)
            if parent_widget is None:
                return False
            current = parent_widget()
            if current is None:
                return False
        return False

    def _input_should_wake(self, watched, event) -> bool:
        if not self.scheduler.active or self._belongs_to_this_docker(watched):
            return False
        event_type = event.type()
        if event_type == SHORTCUT_EVENT:
            return self._is_same_window(watched)
        if event_type != MOUSE_BUTTON_RELEASE:
            return False
        return self._is_same_window(watched) and self._is_item_view_or_child(watched)

    def request_scan(self) -> None:
        self.scheduler.request_after_input()

    def _scan_once(self, check_document: bool) -> None:
        if self._scan_running:
            self.scheduler.request_after_input()
            return
        self._scan_running = True
        try:
            if check_document:
                self._switch_document()
            report = self.controller.scan()
            missing_changed = report.missing_ids != self._last_missing_ids
            if report.message or report.warnings or report.missing_ids:
                self._show_report(report)
            elif missing_changed:
                self._set_status("All linked layers are available.")
            if missing_changed:
                self._last_missing_ids = set(report.missing_ids)
                self.refresh_tree(missing=self._last_missing_ids)
        finally:
            self._scan_running = False

    def _set_status(
        self, text: str, warning: bool = False, error: bool = False
    ) -> None:
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
                    len(report.missing_ids),
                    " is" if len(report.missing_ids) == 1 else "s are",
                )
            )
        if parts:
            self._set_status(
                " ".join(parts), warning=bool(report.warnings or report.missing_ids)
            )

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
        nodes = selected_nodes_for_canvas(self._canvas, self.app)
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
        report = self.controller.enforce_now() if enforce else ScanReport()
        if enforce:
            self._show_report(report)
        self._last_missing_ids = set(self.controller.last_missing_ids)
        self.refresh_tree(missing=self._last_missing_ids)
        self._update_monitoring_state()
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
        index = self.controller.add_rule(dialog.build_rule())
        if not self._save_and_refresh(enforce=True):
            self.controller.remove_rule(index)

    def edit_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        existing = self.controller.rules[index]
        dialog = RuleDialog(list(existing.members), existing=existing, parent=self)
        if exec_dialog(dialog) != ACCEPTED:
            return
        previous = self.controller.replace_rule(index, dialog.build_rule())
        if not self._save_and_refresh(enforce=True):
            self.controller.replace_rule(index, previous)

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
        fallback_id = rule.fallback_id
        if rule.kind.value == "exclusive" and not rule.allow_none:
            fallback_id = refs[0].node_id
        rebound = replace(rule, members=refs, fallback_id=fallback_id)
        previous = self.controller.replace_rule(index, rebound)
        if not self._save_and_refresh(enforce=True):
            self.controller.replace_rule(index, previous)

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
        removed = self.controller.remove_rule(index)
        if not self._save_and_refresh():
            self.controller.insert_rule(index, removed)

    def toggle_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        previous = self.controller.set_rule_enabled(
            index, not self.controller.rules[index].enabled
        )
        if not self._save_and_refresh(enforce=self.controller.rules[index].enabled):
            self.controller.set_rule_enabled(index, previous)

    def move_rule(self, offset: int) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        target = index + offset
        if not self.controller.move_rule(index, target):
            return
        if self._save_and_refresh():
            self.rule_tree.setCurrentItem(self.rule_tree.topLevelItem(target))
        else:
            self.controller.move_rule(target, index)
            self.refresh_tree(missing=self._last_missing_ids)

    def enforce_now(self) -> None:
        report = self.controller.enforce_now()
        self._show_report(report)
        self._last_missing_ids = set(report.missing_ids)
        self.refresh_tree(missing=self._last_missing_ids)

    def _set_paused(self, paused: bool) -> None:
        self.controller.paused = bool(paused)
        self._set_status(
            "Automatic rules paused." if paused else "Automatic rules resumed."
        )
        self._update_monitoring_state(refresh_snapshot=not paused)

    def _set_interval(self, value: int) -> None:
        self.scheduler.set_interval(value)
        self.app.writeSetting("sprite_visibility_rules", "poll_interval_ms", str(value))

    def refresh_tree(self, missing: Optional[Set[str]] = None) -> None:
        selected_index = self._selected_rule_index()
        self.rule_tree.clear()
        missing_ids = set(
            self.controller.last_missing_ids if missing is None else missing
        )
        conflicts = self.controller.conflicts()

        for index, rule in enumerate(self.controller.rules):
            missing_count = sum(
                member.node_id in missing_ids for member in rule.members
            )
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
        if (
            selected_index is not None
            and selected_index < self.rule_tree.topLevelItemCount()
        ):
            self.rule_tree.setCurrentItem(self.rule_tree.topLevelItem(selected_index))
