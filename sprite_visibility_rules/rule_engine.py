# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic, Krita-independent visibility rule engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .models import RuleKind, VisibilityRule


@dataclass(frozen=True)
class CompiledRule:
    rule: VisibilityRule
    member_ids: Tuple[str, ...]
    member_set: FrozenSet[str]


@dataclass(frozen=True)
class CompiledRuleSet:
    rules: Tuple[CompiledRule, ...]
    rules_by_member: Mapping[str, Tuple[int, ...]]


@dataclass
class EnforcementResult:
    states: Dict[str, bool]
    changes: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    cycle_detected: bool = False
    passes: int = 0


def _ordered_unique(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _choose_driver(
    member_set: Set[str],
    trigger_order: Sequence[str],
    states: Mapping[str, bool],
    active_id: Optional[str],
) -> Optional[str]:
    candidates = [
        node_id for node_id in trigger_order if node_id in member_set and node_id in states
    ]
    if active_id in candidates:
        return active_id
    if candidates:
        return candidates[-1]
    return None


def _apply_exclusive(
    rule: VisibilityRule,
    member_ids: Sequence[str],
    states: MutableMapping[str, bool],
    driver: str,
) -> List[str]:
    changed: List[str] = []
    available = [node_id for node_id in member_ids if node_id in states]
    if len(available) < 2:
        return changed

    if states.get(driver, False):
        for node_id in available:
            wanted = node_id == driver
            if states[node_id] != wanted:
                states[node_id] = wanted
                changed.append(node_id)
        return changed

    visible = [node_id for node_id in available if states[node_id]]
    if len(visible) > 1:
        for node_id in visible[1:]:
            states[node_id] = False
            changed.append(node_id)
        return changed

    if not visible and not rule.allow_none:
        fallback = rule.fallback_id if rule.fallback_id in available else available[0]
        if not states[fallback]:
            states[fallback] = True
            changed.append(fallback)
    return changed


def _apply_linked(
    member_ids: Sequence[str],
    states: MutableMapping[str, bool],
    driver: str,
) -> List[str]:
    changed: List[str] = []
    wanted = states[driver]
    for node_id in member_ids:
        if node_id in states and states[node_id] != wanted:
            states[node_id] = wanted
            changed.append(node_id)
    return changed


def _apply_inverse(
    member_ids: Sequence[str],
    states: MutableMapping[str, bool],
    driver: str,
) -> List[str]:
    changed: List[str] = []
    available = [node_id for node_id in member_ids if node_id in states]
    if len(available) != 2 or driver not in available:
        return changed
    other = available[1] if driver == available[0] else available[0]
    wanted = not states[driver]
    if states[other] != wanted:
        states[other] = wanted
        changed.append(other)
    return changed


def compile_rules(rules: Sequence[VisibilityRule]) -> CompiledRuleSet:
    compiled_rules: List[CompiledRule] = []
    rules_by_member: Dict[str, List[int]] = {}

    for rule in rules:
        if not rule.enabled:
            continue
        rule_index = len(compiled_rules)
        member_ids = tuple(member.node_id for member in rule.members)
        compiled_rules.append(
            CompiledRule(rule=rule, member_ids=member_ids, member_set=frozenset(member_ids))
        )
        for node_id in member_ids:
            rules_by_member.setdefault(node_id, []).append(rule_index)

    return CompiledRuleSet(
        rules=tuple(compiled_rules),
        rules_by_member={
            node_id: tuple(rule_indices) for node_id, rule_indices in rules_by_member.items()
        },
    )


def enforce_rules(
    observed_states: Mapping[str, bool],
    changed_order: Sequence[str],
    rules: Sequence[VisibilityRule],
    active_id: Optional[str] = None,
    max_passes: int = 12,
    compiled: Optional[CompiledRuleSet] = None,
) -> EnforcementResult:
    base = dict(observed_states)
    working = dict(observed_states)
    triggers = [node_id for node_id in _ordered_unique(changed_order) if node_id in working]
    if not triggers:
        return EnforcementResult(states=working)

    compiled_rules = compiled if compiled is not None else compile_rules(rules)
    seen_signatures: Set[Tuple[Tuple[str, bool], ...]] = set()
    warnings: List[str] = []

    for pass_number in range(1, max_passes + 1):
        signature = tuple(working.items())
        if signature in seen_signatures:
            return EnforcementResult(
                states=base,
                changes={},
                warnings=[
                    "Conflicting rules formed a visibility cycle; no automatic changes were applied."
                ],
                cycle_detected=True,
                passes=pass_number - 1,
            )
        seen_signatures.add(signature)

        candidate_indices = sorted(
            {
                rule_index
                for trigger in triggers
                for rule_index in compiled_rules.rules_by_member.get(trigger, ())
            }
        )
        next_triggers: List[str] = []
        for rule_index in candidate_indices:
            compiled_rule = compiled_rules.rules[rule_index]
            rule = compiled_rule.rule
            member_ids = compiled_rule.member_ids
            driver = _choose_driver(compiled_rule.member_set, triggers, working, active_id)
            if driver is None:
                continue
            if rule.kind == RuleKind.EXCLUSIVE:
                changed = _apply_exclusive(rule, member_ids, working, driver)
            elif rule.kind == RuleKind.LINKED:
                changed = _apply_linked(member_ids, working, driver)
            elif rule.kind == RuleKind.INVERSE:
                changed = _apply_inverse(member_ids, working, driver)
            else:
                warnings.append("Unknown rule type in '{}'.".format(rule.name))
                changed = []
            next_triggers.extend(changed)

        next_triggers = _ordered_unique(next_triggers)
        if not next_triggers:
            changes = {
                node_id: state for node_id, state in working.items() if base.get(node_id) != state
            }
            return EnforcementResult(
                states=working,
                changes=changes,
                warnings=warnings,
                passes=pass_number,
            )
        triggers = next_triggers

    return EnforcementResult(
        states=base,
        changes={},
        warnings=[
            "Rules did not stabilize after {} passes; no automatic changes were applied.".format(
                max_passes
            )
        ],
        cycle_detected=True,
        passes=max_passes,
    )


def normalize_rules(
    observed_states: Mapping[str, bool],
    rules: Sequence[VisibilityRule],
    active_id: Optional[str] = None,
    compiled: Optional[CompiledRuleSet] = None,
) -> EnforcementResult:
    trigger_order: List[str] = []
    if active_id is not None:
        trigger_order.append(active_id)
    for rule in rules:
        if not rule.enabled:
            continue
        trigger_order.extend(member.node_id for member in rule.members)
    return enforce_rules(
        observed_states,
        _ordered_unique(trigger_order),
        rules,
        active_id,
        compiled=compiled,
    )
