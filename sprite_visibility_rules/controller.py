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
        self.rules: List[VisibilityRule] = []
        self.previous_states: Dict[str, bool] = {}
        self.paused = False
        self.load_warnings: List[str] = []
        self.last_error = ""
        self.last_missing_ids: Set[str] = set()

        self._rule_signature: Optional[Tuple[Any, ...]] = None
        self._ordered_ids: Tuple[str, ...] = ()
        self._tracked_id_set: FrozenSet[str] = frozenset()
        self._node_cache: Dict[str, Any] = {}
        self._compiled_rules: CompiledRuleSet = compile_rules(())
        self._last_node_resolve = 0.0

    def _clear_runtime_cache(self) -> None:
        self.previous_states = {}
        self.last_missing_ids = set()
        self._rule_signature = None
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
        self.rules = []
        self.load_warnings = []
        self.last_error = ""
        self._clear_runtime_cache()
        if document is None:
            return True
        try:
            loaded = load_from_document(document)
            self.rules = loaded.rules
            self.load_warnings = loaded.warnings
        except StorageError as exc:
            self.last_error = str(exc)
        self.snapshot(force_resolve=True)
        return True

    def _current_rule_signature(self) -> Tuple[Any, ...]:
        return tuple(
            (
                rule.rule_id,
                rule.enabled,
                rule.kind.value,
                rule.allow_none,
                rule.fallback_id,
                tuple(member.node_id for member in rule.members),
            )
            for rule in self.rules
        )

    def _ensure_rule_index(self) -> None:
        signature = self._current_rule_signature()
        if signature == self._rule_signature:
            return

        ordered: List[str] = []
        seen: Set[str] = set()
        for rule in self.rules:
            if not rule.enabled:
                continue
            for member in rule.members:
                if member.node_id not in seen:
                    seen.add(member.node_id)
                    ordered.append(member.node_id)

        tracked = frozenset(seen)
        tracked_changed = tracked != self._tracked_id_set
        self._rule_signature = signature
        self._ordered_ids = tuple(ordered)
        self._tracked_id_set = tracked
        self._compiled_rules = compile_rules(self.rules)
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
        self._ensure_rule_index()
        save_to_document(self.document, self.rules, self.qbytearray_class)
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

    def scan(self) -> ScanReport:
        report = ScanReport()
        if self.document is None or self.paused or not self.rules:
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
            self.rules,
            active_id=self._active_driver(changed_order),
            compiled=self._compiled_rules,
        )
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report

        self.previous_states = self._apply_changes(nodes, states, result.changes, report)
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
            self.rules,
            self._active_driver(self.ordered_tracked_ids()),
            compiled=self._compiled_rules,
        )
        report.warnings.extend(result.warnings)
        report.cycle_detected = result.cycle_detected
        if result.cycle_detected:
            self.previous_states = states
            return report

        self.previous_states = self._apply_changes(nodes, states, result.changes, report)
        if report.changed_count:
            report.message = "Normalized {} layer visibility state{}.".format(
                report.changed_count, "" if report.changed_count == 1 else "s"
            )
        return report

    def conflicts(self):
        return find_membership_conflicts(self.rules)
