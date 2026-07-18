# SPDX-License-Identifier: GPL-3.0-or-later
"""Krita-facing document controller and polling coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .krita_adapter import active_node_id, resolve_tracked_nodes
from .models import VisibilityRule, find_membership_conflicts
from .rule_engine import CompiledRuleSet, compile_rules, enforce_rules, normalize_rules
from .storage import StorageError, load_from_document, save_to_document

NODE_CACHE_REFRESH_SECONDS = 0.5


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
        self._rules: List[VisibilityRule] = []
        self.previous_states: Dict[str, bool] = {}
        self.paused = False
        self.load_warnings: List[str] = []
        self.last_error = ""
        self.last_missing_ids: Set[str] = set()

        self._rules_revision = 0
        self._indexed_revision = -1
        self._ordered_ids: Tuple[str, ...] = ()
        self._tracked_id_set: FrozenSet[str] = frozenset()
        self._node_cache: Dict[str, Any] = {}
        self._compiled_rules: CompiledRuleSet = compile_rules(())
        self._last_node_resolve = 0.0

    @property
    def rules(self) -> List[VisibilityRule]:
        return self._rules

    @rules.setter
    def rules(self, value: List[VisibilityRule]) -> None:
        self.replace_rules(value)

    @property
    def rules_revision(self) -> int:
        return self._rules_revision

    def _mark_rules_changed(self) -> None:
        self._rules_revision += 1

    def replace_rules(self, rules: List[VisibilityRule]) -> None:
        self._rules = list(rules)
        self._mark_rules_changed()

    def add_rule(self, rule: VisibilityRule) -> int:
        self._rules.append(rule)
        self._mark_rules_changed()
        return len(self._rules) - 1

    def insert_rule(self, index: int, rule: VisibilityRule) -> None:
        self._rules.insert(index, rule)
        self._mark_rules_changed()

    def replace_rule(self, index: int, rule: VisibilityRule) -> VisibilityRule:
        previous = self._rules[index]
        self._rules[index] = rule
        self._mark_rules_changed()
        return previous

    def remove_rule(self, index: int) -> VisibilityRule:
        removed = self._rules.pop(index)
        self._mark_rules_changed()
        return removed

    def set_rule_enabled(self, index: int, enabled: bool) -> bool:
        previous = self._rules[index].enabled
        self._rules[index].enabled = bool(enabled)
        self._mark_rules_changed()
        return previous

    def move_rule(self, index: int, target: int) -> bool:
        if index == target:
            return True
        if min(index, target) < 0 or max(index, target) >= len(self._rules):
            return False
        rule = self._rules.pop(index)
        self._rules.insert(target, rule)
        self._mark_rules_changed()
        return True

    def touch_rules(self) -> None:
        """Invalidate compiled state after an intentional in-place rule edit."""

        self._mark_rules_changed()

    def has_enabled_rules(self) -> bool:
        return any(rule.enabled for rule in self._rules)

    def _clear_runtime_cache(self) -> None:
        self.previous_states = {}
        self.last_missing_ids = set()
        self._indexed_revision = -1
        self._ordered_ids = ()
        self._tracked_id_set = frozenset()
        self._node_cache = {}
        self._compiled_rules = compile_rules(())
        self._last_node_resolve = 0.0

    def set_document(self, document: Any) -> bool:
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
        self._rules = []
        self._mark_rules_changed()
        self.load_warnings = []
        self.last_error = ""
        self._clear_runtime_cache()
        if document is None:
            return True
        try:
            loaded = load_from_document(document)
            self.replace_rules(loaded.rules)
            self.load_warnings = loaded.warnings
        except StorageError as exc:
            self.last_error = str(exc)
        self.snapshot(force_resolve=True)
        return True

    def _ensure_rule_index(self) -> None:
        if self._indexed_revision == self._rules_revision:
            return

        ordered: List[str] = []
        seen: Set[str] = set()
        for rule in self._rules:
            if not rule.enabled:
                continue
            for member in rule.members:
                if member.node_id not in seen:
                    seen.add(member.node_id)
                    ordered.append(member.node_id)

        tracked = frozenset(seen)
        tracked_changed = tracked != self._tracked_id_set
        self._ordered_ids = tuple(ordered)
        self._tracked_id_set = tracked
        self._compiled_rules = compile_rules(self._rules)
        self._indexed_revision = self._rules_revision
        if tracked_changed:
            self._node_cache = {
                node_id: node for node_id, node in self._node_cache.items() if node_id in tracked
            }
            self.previous_states = {
                node_id: state
                for node_id, state in self.previous_states.items()
                if node_id in tracked
            }
            self.last_missing_ids.intersection_update(tracked)
            self._last_node_resolve = 0.0

    def ordered_tracked_ids(self) -> List[str]:
        self._ensure_rule_index()
        return list(self._ordered_ids)

    def tracked_ids(self) -> Set[str]:
        self._ensure_rule_index()
        return set(self._tracked_id_set)

    def invalidate_node_cache(self) -> None:
        self._node_cache = {}
        self._last_node_resolve = 0.0

    def _resolve_nodes(self, force: bool = False) -> Dict[str, Any]:
        self._ensure_rule_index()
        if self.document is None or not self._tracked_id_set:
            self._node_cache = {}
            self.last_missing_ids = set(self._tracked_id_set)
            return {}

        now = monotonic()
        should_resolve = (
            force
            or not self._last_node_resolve
            or now - self._last_node_resolve >= NODE_CACHE_REFRESH_SECONDS
        )
        if should_resolve:
            self._node_cache = resolve_tracked_nodes(self.document, set(self._tracked_id_set))
            self._last_node_resolve = now
            self.last_missing_ids = set(self._tracked_id_set).difference(self._node_cache.keys())
        return {
            node_id: self._node_cache[node_id]
            for node_id in self._ordered_ids
            if node_id in self._node_cache
        }

    def _nodes_and_states(self, force_resolve: bool = False):
        nodes = self._resolve_nodes(force=force_resolve)
        states: Dict[str, bool] = {}
        failed_ids: Set[str] = set()
        for node_id, node in nodes.items():
            try:
                states[node_id] = bool(node.visible())
            except Exception:
                failed_ids.add(node_id)

        if failed_ids and not force_resolve:
            self.invalidate_node_cache()
            return self._nodes_and_states(force_resolve=True)

        if failed_ids:
            for node_id in failed_ids:
                nodes.pop(node_id, None)
                self._node_cache.pop(node_id, None)
            self.last_missing_ids.update(failed_ids)
        else:
            self.last_missing_ids = set(self._tracked_id_set).difference(states.keys())
        return nodes, states

    def snapshot(self, force_resolve: bool = False) -> None:
        _, states = self._nodes_and_states(force_resolve=force_resolve)
        self.previous_states = states

    def save(self) -> None:
        if self.document is None:
            raise StorageError("Open a Krita document before editing rules.")
        # This catches supported in-place edits made before save while normal
        # structural operations use the explicit revision-aware methods above.
        self.touch_rules()
        self._ensure_rule_index()
        save_to_document(self.document, self._rules, self.qbytearray_class)
        self.snapshot(force_resolve=True)

    def _active_driver(self, changed_order: List[str]) -> Optional[str]:
        if not changed_order:
            return None
        if len(changed_order) == 1:
            return changed_order[0]
        return active_node_id(self.document)

    def _apply_changes(
        self,
        nodes: Dict[str, Any],
        states: Dict[str, bool],
        changes: Dict[str, bool],
        report: ScanReport,
    ) -> Dict[str, bool]:
        final_states = dict(states)
        for node_id, wanted in changes.items():
            node = nodes.get(node_id)
            if node is None or states.get(node_id) == wanted:
                continue
            try:
                node.setVisible(wanted)
                actual = bool(node.visible())
            except Exception as exc:
                report.warnings.append(
                    "Could not update linked layer '{}': {}".format(node_id, exc)
                )
                self.invalidate_node_cache()
                continue
            final_states[node_id] = actual
            if actual != states[node_id]:
                report.changed_count += 1
            if actual != wanted:
                report.warnings.append(
                    "Krita did not keep the requested visibility for layer '{}'.".format(node_id)
                )
        return final_states

    def _refresh_projection(self, report: ScanReport) -> None:
        if self.document is None or not report.changed_count:
            return
        try:
            self.document.refreshProjection()
        except Exception as exc:
            report.warnings.append("Could not refresh the Krita projection: {}".format(exc))

    def scan(self) -> ScanReport:
        report = ScanReport()
        if self.document is None or self.paused or not self.has_enabled_rules():
            return report
        nodes, states = self._nodes_and_states()
        report.missing_ids = set(self.last_missing_ids)

        if not self.previous_states:
            self.previous_states = states
            return report

        changed_order = [
            node_id
            for node_id in self._ordered_ids
            if node_id in states
            and node_id in self.previous_states
            and self.previous_states[node_id] != states[node_id]
        ]
        if not changed_order:
            self.previous_states = states
            return report

        result = enforce_rules(
            states,
            changed_order,
            self._rules,
            active_id=self._active_driver(changed_order),
            compiled=self._compiled_rules,
        )
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report

        self.previous_states = self._apply_changes(nodes, states, result.changes, report)
        self._refresh_projection(report)
        if report.changed_count:
            report.message = "Applied {} linked visibility change{}.".format(
                report.changed_count, "" if report.changed_count == 1 else "s"
            )
        return report

    def enforce_now(self) -> ScanReport:
        report = ScanReport()
        if self.document is None:
            report.warnings.append("Open a Krita document first.")
            return report
        nodes, states = self._nodes_and_states(force_resolve=True)
        report.missing_ids = set(self.last_missing_ids)
        result = normalize_rules(
            states,
            self._rules,
            self._active_driver(self.ordered_tracked_ids()),
            compiled=self._compiled_rules,
        )
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report

        self.previous_states = self._apply_changes(nodes, states, result.changes, report)
        self._refresh_projection(report)
        if report.changed_count:
            report.message = "Normalized {} layer visibility state{}.".format(
                report.changed_count, "" if report.changed_count == 1 else "s"
            )
        return report

    def conflicts(self):
        return find_membership_conflicts(self._rules)
