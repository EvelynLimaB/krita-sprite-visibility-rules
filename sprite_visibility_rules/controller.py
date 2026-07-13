# SPDX-License-Identifier: GPL-3.0-or-later
"""Krita-facing document controller and polling coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from .krita_adapter import active_node_id, resolve_tracked_nodes
from .models import VisibilityRule, find_membership_conflicts
from .rule_engine import enforce_rules, normalize_rules
from .storage import StorageError, load_from_document, save_to_document


@dataclass
class ScanReport:
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    missing_ids: Set[str] = field(default_factory=set)
    changed_count: int = 0
    cycle_detected: bool = False


class VisibilityController:
    def __init__(self, qbytearray_class: Any):
        self.qbytearray_class = qbytearray_class
        self.document: Any = None
        self.rules: List[VisibilityRule] = []
        self.previous_states: Dict[str, bool] = {}
        self.paused = False
        self.load_warnings: List[str] = []
        self.last_error = ""

    def set_document(self, document: Any) -> bool:
        # Krita may hand Python a fresh wrapper for the same underlying
        # document. The libkis Document equality operator compares the actual
        # document, while object identity or root-node UUIDs can confuse
        # duplicated/cloned files. Refresh the wrapper without reloading only
        # when Krita says both wrappers represent the same document.
        if self.document is None and document is None:
            return False
        if self.document is not None and document is not None:
            try:
                if bool(document == self.document):
                    self.document = document
                    return False
            except Exception:
                pass

        self.document = document
        self.previous_states = {}
        self.rules = []
        self.load_warnings = []
        self.last_error = ""
        if document is None:
            return True
        try:
            loaded = load_from_document(document)
            self.rules = loaded.rules
            self.load_warnings = loaded.warnings
        except StorageError as exc:
            self.last_error = str(exc)
        self.snapshot()
        return True

    def ordered_tracked_ids(self) -> List[str]:
        ordered: List[str] = []
        seen: Set[str] = set()
        for rule in self.rules:
            if not rule.enabled:
                continue
            for member in rule.members:
                if member.node_id not in seen:
                    seen.add(member.node_id)
                    ordered.append(member.node_id)
        return ordered

    def tracked_ids(self) -> Set[str]:
        return set(self.ordered_tracked_ids())

    def _nodes_and_states(self):
        if self.document is None:
            return {}, {}
        nodes = resolve_tracked_nodes(self.document, self.tracked_ids())
        states = {node_id: bool(node.visible()) for node_id, node in nodes.items()}
        return nodes, states

    def snapshot(self) -> None:
        _, states = self._nodes_and_states()
        self.previous_states = states

    def save(self) -> None:
        if self.document is None:
            raise StorageError("Open a Krita document before editing rules.")
        save_to_document(self.document, self.rules, self.qbytearray_class)
        self.snapshot()

    def scan(self) -> ScanReport:
        report = ScanReport()
        if self.document is None or self.paused or not self.rules:
            return report
        nodes, states = self._nodes_and_states()
        tracked = self.tracked_ids()
        report.missing_ids = tracked.difference(nodes.keys())

        if not self.previous_states:
            self.previous_states = states
            return report

        changed_order = [
            node_id
            for node_id in self.ordered_tracked_ids()
            if node_id in states
            and node_id in self.previous_states
            and self.previous_states[node_id] != states[node_id]
        ]
        # Newly restored/recreated tracked nodes are snapshotted, not interpreted
        # as a visibility click.
        if not changed_order:
            self.previous_states = states
            return report

        result = enforce_rules(
            states,
            changed_order,
            self.rules,
            active_id=active_node_id(self.document),
        )
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report

        for node_id, wanted in result.changes.items():
            node = nodes.get(node_id)
            if node is not None and bool(node.visible()) != wanted:
                node.setVisible(wanted)
                report.changed_count += 1
        if report.changed_count:
            self.document.refreshProjection()
            report.message = "Applied {} linked visibility change{}.".format(
                report.changed_count, "" if report.changed_count == 1 else "s"
            )
        # Read back actual states because Krita or another plugin may reject or
        # alter a requested visibility transition.
        _, final_states = self._nodes_and_states()
        self.previous_states = final_states
        return report

    def enforce_now(self) -> ScanReport:
        report = ScanReport()
        if self.document is None:
            report.warnings.append("Open a Krita document first.")
            return report
        nodes, states = self._nodes_and_states()
        report.missing_ids = self.tracked_ids().difference(nodes.keys())
        result = normalize_rules(states, self.rules, active_node_id(self.document))
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report
        for node_id, wanted in result.changes.items():
            node = nodes.get(node_id)
            if node is not None and bool(node.visible()) != wanted:
                node.setVisible(wanted)
                report.changed_count += 1
        if report.changed_count:
            self.document.refreshProjection()
            report.message = "Normalized {} layer visibility state{}.".format(
                report.changed_count, "" if report.changed_count == 1 else "s"
            )
        self.snapshot()
        return report

    def conflicts(self):
        return find_membership_conflicts(self.rules)
