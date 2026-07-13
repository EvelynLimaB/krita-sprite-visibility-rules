import unittest

from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule
from sprite_visibility_rules.storage import StorageError, deserialize_rules, serialize_rules


class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        rule = VisibilityRule(
            "eyes",
            RuleKind.EXCLUSIVE,
            [NodeRef("a", "Open"), NodeRef("b", "Closed")],
            allow_none=False,
            fallback_id="a",
        )
        loaded = deserialize_rules(serialize_rules([rule]))
        self.assertEqual(len(loaded.rules), 1)
        self.assertEqual(loaded.rules[0].to_dict(), rule.to_dict())

    def test_malformed_json_is_rejected(self):
        with self.assertRaises(StorageError):
            deserialize_rules(b"not-json")

    def test_unknown_schema_is_rejected(self):
        with self.assertRaises(StorageError):
            deserialize_rules(b'{"schema_version":999,"rules":[]}')

    def test_invalid_rule_is_skipped_with_warning(self):
        loaded = deserialize_rules(
            b'{"schema_version":1,"rules":[{"type":"inverse","name":"bad","members":[]}]}'
        )
        self.assertEqual(loaded.rules, [])
        self.assertTrue(loaded.warnings)


if __name__ == "__main__":
    unittest.main()
