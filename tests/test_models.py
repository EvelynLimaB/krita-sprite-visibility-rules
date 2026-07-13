import unittest

from sprite_visibility_rules.models import (
    NodeRef,
    RuleKind,
    VisibilityRule,
    find_membership_conflicts,
)


def ref(name):
    return NodeRef(name, name)


class ModelTests(unittest.TestCase):
    def test_inverse_requires_exactly_two_members(self):
        rule = VisibilityRule("bad", RuleKind.INVERSE, [ref("a"), ref("b"), ref("c")])
        self.assertTrue(any("exactly two" in item for item in rule.validate()))

    def test_strict_exclusive_requires_fallback(self):
        rule = VisibilityRule("eyes", RuleKind.EXCLUSIVE, [ref("a"), ref("b")], allow_none=False)
        self.assertTrue(any("fallback" in item for item in rule.validate()))

    def test_membership_conflict_is_reported(self):
        a = VisibilityRule("one", RuleKind.LINKED, [ref("a"), ref("b")])
        b = VisibilityRule("two", RuleKind.INVERSE, [ref("b"), ref("c")])
        self.assertEqual(find_membership_conflicts([a, b]), {"b": ["one", "two"]})


if __name__ == "__main__":
    unittest.main()
