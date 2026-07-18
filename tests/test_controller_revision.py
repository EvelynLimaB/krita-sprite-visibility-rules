import unittest
from unittest.mock import patch

from sprite_visibility_rules.controller import VisibilityController
from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule


class FakeUuid:
    def __init__(self, value):
        self.value = value

    def toString(self):
        return self.value


class FakeNode:
    def __init__(self, node_id, visible=True):
        self.node_id = node_id
        self._visible = visible

    def uniqueId(self):
        return FakeUuid(self.node_id)

    def visible(self):
        return self._visible

    def childNodes(self):
        return []


class FakeDocument:
    def __init__(self, nodes):
        self.nodes = {node.node_id: node for node in nodes}
        self.root = FakeNode("root")
        self.root.childNodes = lambda: list(nodes)

    def rootNode(self):
        return self.root

    def activeNode(self):
        return next(iter(self.nodes.values()), None)


def resolve_fake(document, tracked_ids):
    return {
        node_id: document.nodes[node_id] for node_id in tracked_ids if node_id in document.nodes
    }


class ControllerRevisionTests(unittest.TestCase):
    def test_explicit_rule_mutations_rebuild_only_after_revision_changes(self):
        controller = VisibilityController(bytes)
        rule = VisibilityRule(
            "Pair",
            RuleKind.INVERSE,
            [NodeRef("a", "A"), NodeRef("b", "B")],
        )

        with patch(
            "sprite_visibility_rules.controller.compile_rules",
            wraps=lambda rules: object(),
        ) as build:
            controller.replace_rules([rule])
            controller.tracked_ids()
            controller.tracked_ids()
            self.assertEqual(build.call_count, 1)

            controller.set_rule_enabled(0, False)
            self.assertEqual(controller.tracked_ids(), set())
            self.assertEqual(build.call_count, 2)

    def test_canvas_rule_methods_preserve_order_and_revision(self):
        first = VisibilityRule(
            "First",
            RuleKind.LINKED,
            [NodeRef("a", "A"), NodeRef("b", "B")],
        )
        second = VisibilityRule(
            "Second",
            RuleKind.LINKED,
            [NodeRef("c", "C"), NodeRef("d", "D")],
        )
        controller = VisibilityController(bytes)
        start = controller.rules_revision
        controller.add_rule(first)
        controller.add_rule(second)
        self.assertGreater(controller.rules_revision, start)
        self.assertTrue(controller.move_rule(0, 1))
        self.assertEqual([rule.name for rule in controller.rules], ["Second", "First"])
        removed = controller.remove_rule(1)
        controller.insert_rule(0, removed)
        self.assertEqual([rule.name for rule in controller.rules], ["First", "Second"])

    def test_rule_assignment_remains_compatible_with_existing_callers(self):
        nodes = [FakeNode("a"), FakeNode("b", visible=False)]
        document = FakeDocument(nodes)
        controller = VisibilityController(bytes)
        controller.document = document
        controller.rules = [
            VisibilityRule(
                "Pair",
                RuleKind.INVERSE,
                [NodeRef("a", "A"), NodeRef("b", "B")],
            )
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ):
            controller.snapshot(force_resolve=True)
        self.assertEqual(controller.tracked_ids(), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
