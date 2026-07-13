# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure data model for visibility rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4


class RuleKind(str, Enum):
    EXCLUSIVE = "exclusive"
    LINKED = "linked"
    INVERSE = "inverse"

    @property
    def label(self) -> str:
        return {
            RuleKind.EXCLUSIVE: "Exclusive set",
            RuleKind.LINKED: "Linked set",
            RuleKind.INVERSE: "Inverse pair",
        }[self]


@dataclass(frozen=True)
class NodeRef:
    node_id: str
    name: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.node_id, "name": self.name}

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "NodeRef":
        return cls(node_id=str(value["id"]), name=str(value.get("name", "Unnamed layer")))


@dataclass
class VisibilityRule:
    name: str
    kind: RuleKind
    members: List[NodeRef]
    rule_id: str = field(default_factory=lambda: str(uuid4()))
    enabled: bool = True
    allow_none: bool = True
    fallback_id: Optional[str] = None

    @property
    def member_ids(self) -> List[str]:
        return [member.node_id for member in self.members]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.rule_id,
            "name": self.name,
            "type": self.kind.value,
            "enabled": self.enabled,
            "members": [member.to_dict() for member in self.members],
            "allow_none": self.allow_none,
            "fallback_id": self.fallback_id,
        }

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "VisibilityRule":
        return cls(
            rule_id=str(value.get("id") or uuid4()),
            name=str(value.get("name", "Unnamed rule")),
            kind=RuleKind(str(value["type"])),
            enabled=bool(value.get("enabled", True)),
            members=[NodeRef.from_dict(item) for item in value.get("members", [])],
            allow_none=bool(value.get("allow_none", True)),
            fallback_id=(
                str(value["fallback_id"]) if value.get("fallback_id") not in (None, "") else None
            ),
        )

    def validate(self) -> List[str]:
        errors: List[str] = []
        ids = self.member_ids
        if not self.name.strip():
            errors.append("Rule name cannot be empty.")
        if len(ids) < 2:
            errors.append("A rule needs at least two layers.")
        if len(set(ids)) != len(ids):
            errors.append("A layer appears more than once in the rule.")
        if self.kind == RuleKind.INVERSE and len(ids) != 2:
            errors.append("An inverse pair must contain exactly two layers.")
        if self.kind == RuleKind.EXCLUSIVE and not self.allow_none:
            if self.fallback_id not in ids:
                errors.append("A strict exclusive set needs a fallback layer from the set.")
        return errors


def validate_rules(rules: Sequence[VisibilityRule]) -> List[str]:
    errors: List[str] = []
    seen_ids = set()
    for index, rule in enumerate(rules, start=1):
        if rule.rule_id in seen_ids:
            errors.append("Rule {} has a duplicate internal ID.".format(index))
        seen_ids.add(rule.rule_id)
        for error in rule.validate():
            errors.append("{}: {}".format(rule.name or "Rule {}".format(index), error))
    return errors


def find_membership_conflicts(rules: Sequence[VisibilityRule]) -> Dict[str, List[str]]:
    """Return nodes used by more than one enabled rule.

    Multiple membership is legal because it enables useful cascades, but it can
    also produce contradictory cycles. The docker surfaces it as a warning.
    """

    memberships: Dict[str, List[str]] = {}
    for rule in rules:
        if not rule.enabled:
            continue
        for member in rule.members:
            memberships.setdefault(member.node_id, []).append(rule.name)
    return {node_id: names for node_id, names in memberships.items() if len(names) > 1}
