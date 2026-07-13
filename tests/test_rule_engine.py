import unittest

from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule
from sprite_visibility_rules.rule_engine import enforce_rules, normalize_rules


def refs(*names):
    return [NodeRef(name, name) for name in names]


class RuleEngineTests(unittest.TestCase):
    def test_inverse_show_a_hides_b(self):
        rule = VisibilityRule("pair", RuleKind.INVERSE, refs("a", "b"))
        result = enforce_rules({"a": True, "b": True}, ["a"], [rule], active_id="a")
        self.assertEqual(result.changes, {"b": False})

    def test_inverse_hide_a_shows_b(self):
        rule = VisibilityRule("pair", RuleKind.INVERSE, refs("a", "b"))
        result = enforce_rules({"a": False, "b": False}, ["a"], [rule], active_id="a")
        self.assertEqual(result.changes, {"b": True})

    def test_inverse_is_symmetric(self):
        rule = VisibilityRule("pair", RuleKind.INVERSE, refs("a", "b"))
        result = enforce_rules({"a": True, "b": True}, ["b"], [rule], active_id="b")
        self.assertEqual(result.changes, {"a": False})

    def test_linked_propagates_visibility(self):
        rule = VisibilityRule("shadows", RuleKind.LINKED, refs("a", "b", "c"))
        result = enforce_rules({"a": False, "b": True, "c": True}, ["a"], [rule], active_id="a")
        self.assertEqual(result.changes, {"b": False, "c": False})

    def test_exclusive_show_hides_others(self):
        rule = VisibilityRule("eyes", RuleKind.EXCLUSIVE, refs("a", "b", "c"))
        result = enforce_rules({"a": True, "b": True, "c": False}, ["b"], [rule], active_id="b")
        self.assertEqual(result.states, {"a": False, "b": True, "c": False})

    def test_exclusive_can_allow_none(self):
        rule = VisibilityRule("eyes", RuleKind.EXCLUSIVE, refs("a", "b"), allow_none=True)
        result = enforce_rules({"a": False, "b": False}, ["a"], [rule], active_id="a")
        self.assertFalse(result.changes)

    def test_strict_exclusive_restores_fallback(self):
        rule = VisibilityRule(
            "eyes", RuleKind.EXCLUSIVE, refs("a", "b"), allow_none=False, fallback_id="b"
        )
        result = enforce_rules({"a": False, "b": False}, ["a"], [rule], active_id="a")
        self.assertEqual(result.changes, {"b": True})

    def test_disabled_rule_does_nothing(self):
        rule = VisibilityRule("pair", RuleKind.INVERSE, refs("a", "b"), enabled=False)
        result = enforce_rules({"a": True, "b": True}, ["a"], [rule])
        self.assertEqual(result.changes, {})

    def test_missing_member_does_not_crash(self):
        rule = VisibilityRule("eyes", RuleKind.EXCLUSIVE, refs("a", "missing"))
        result = enforce_rules({"a": True}, ["a"], [rule])
        self.assertEqual(result.changes, {})

    def test_cascade_between_rules(self):
        inverse = VisibilityRule("inverse", RuleKind.INVERSE, refs("a", "b"))
        linked = VisibilityRule("linked", RuleKind.LINKED, refs("b", "c"))
        result = enforce_rules(
            {"a": True, "b": True, "c": True}, ["a"], [inverse, linked], active_id="a"
        )
        self.assertEqual(result.states, {"a": True, "b": False, "c": False})

    def test_cycle_is_detected_without_plugin_changes(self):
        linked = VisibilityRule("same", RuleKind.LINKED, refs("a", "b"))
        inverse = VisibilityRule("opposite", RuleKind.INVERSE, refs("a", "b"))
        result = enforce_rules(
            {"a": True, "b": True}, ["a"], [linked, inverse], active_id="a", max_passes=8
        )
        self.assertTrue(result.cycle_detected)
        self.assertEqual(result.changes, {})
        self.assertEqual(result.states, {"a": True, "b": True})

    def test_normalize_repairs_invalid_inverse_state(self):
        rule = VisibilityRule("pair", RuleKind.INVERSE, refs("a", "b"))
        result = normalize_rules({"a": True, "b": True}, [rule], active_id="a")
        self.assertEqual(result.states, {"a": True, "b": False})


if __name__ == "__main__":
    unittest.main()
