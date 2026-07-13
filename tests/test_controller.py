import unittest
from unittest.mock import patch

from sprite_visibility_rules.controller import VisibilityController
from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule
from sprite_visibility_rules.storage import ANNOTATION_TYPE, serialize_rules


class FakeUuid:
    def __init__(self, value):
        self.value = value

    def toString(self):
        return self.value


class FakeNode:
    def __init__(self, node_id, name, visible=True, children=None):
        self.node_id = node_id
        self._name = name
        self._visible = visible
        self._children = children or []
        self.set_calls = 0

    def uniqueId(self):
        return FakeUuid(self.node_id)

    def name(self):
        return self._name

    def visible(self):
        return self._visible

    def setVisible(self, value):
        self.set_calls += 1
        self._visible = bool(value)

    def childNodes(self):
        return list(self._children)


class FakeDocument:
    def __init__(self, nodes):
        self.nodes = {node.node_id: node for node in nodes}
        self.root = FakeNode("root", "root", children=nodes)
        self.annotations = {}
        self.modified = False
        self.refreshes = 0
        self.active = nodes[0]

    def rootNode(self):
        return self.root

    def activeNode(self):
        return self.active

    def annotationTypes(self):
        return list(self.annotations)

    def annotation(self, key):
        return self.annotations[key]

    def setAnnotation(self, key, description, value):
        self.annotations[key] = bytes(value)

    def setModified(self, value):
        self.modified = bool(value)

    def refreshProjection(self):
        self.refreshes += 1


def resolve_fake(document, tracked_ids):
    return {
        node_id: document.nodes[node_id] for node_id in tracked_ids if node_id in document.nodes
    }


class ControllerTests(unittest.TestCase):
    def test_normal_eye_click_is_detected_inverse_applied_and_projection_refreshed(self):
        a = FakeNode("a", "Jacket on", True)
        b = FakeNode("b", "Jacket off", False)
        doc = FakeDocument([a, b])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule("jacket", RuleKind.INVERSE, [NodeRef("a", "A"), NodeRef("b", "B")])
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ) as resolver:
            controller.snapshot(force_resolve=True)
            a.setVisible(False)
            report = controller.scan()
        self.assertTrue(b.visible())
        self.assertEqual(report.changed_count, 1)
        self.assertEqual(doc.refreshes, 1)
        self.assertEqual(resolver.call_count, 1)

    def test_linked_batch_refreshes_projection_only_once(self):
        a = FakeNode("a", "A", True)
        b = FakeNode("b", "B", True)
        c = FakeNode("c", "C", True)
        doc = FakeDocument([a, b, c])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule(
                "linked",
                RuleKind.LINKED,
                [NodeRef("a", "A"), NodeRef("b", "B"), NodeRef("c", "C")],
            )
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ):
            controller.snapshot(force_resolve=True)
            a.setVisible(False)
            report = controller.scan()
        self.assertFalse(b.visible())
        self.assertFalse(c.visible())
        self.assertEqual(report.changed_count, 2)
        self.assertEqual(doc.refreshes, 1)

    def test_hot_scan_reuses_node_wrappers_and_avoids_second_resolve(self):
        a = FakeNode("a", "A", True)
        b = FakeNode("b", "B", False)
        doc = FakeDocument([a, b])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule("pair", RuleKind.INVERSE, [NodeRef("a", "A"), NodeRef("b", "B")])
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ) as resolver:
            controller.snapshot(force_resolve=True)
            a.setVisible(False)
            controller.scan()
            b.setVisible(False)
            controller.scan()
        self.assertEqual(resolver.call_count, 1)
        self.assertEqual(doc.refreshes, 2)

    def test_first_snapshot_never_changes_document(self):
        a = FakeNode("a", "A", True)
        b = FakeNode("b", "B", True)
        doc = FakeDocument([a, b])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule("pair", RuleKind.INVERSE, [NodeRef("a", "A"), NodeRef("b", "B")])
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ):
            controller.previous_states = {}
            controller.scan()
        self.assertTrue(a.visible())
        self.assertTrue(b.visible())
        self.assertEqual(doc.refreshes, 0)

    def test_distinct_documents_with_same_root_uuid_reload_rules(self):
        first_node = FakeNode("a", "First", True)
        second_node = FakeNode("b", "Second", True)
        first = FakeDocument([first_node])
        second = FakeDocument([second_node])
        self.assertEqual(first.root.uniqueId().toString(), second.root.uniqueId().toString())

        first_rule = VisibilityRule(
            "First rule", RuleKind.LINKED, [NodeRef("a", "A"), NodeRef("missing-a", "A2")]
        )
        second_rule = VisibilityRule(
            "Second rule", RuleKind.LINKED, [NodeRef("b", "B"), NodeRef("missing-b", "B2")]
        )
        first.annotations[ANNOTATION_TYPE] = serialize_rules([first_rule])
        second.annotations[ANNOTATION_TYPE] = serialize_rules([second_rule])

        controller = VisibilityController(bytes)
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ):
            self.assertTrue(controller.set_document(first))
            self.assertEqual(controller.rules[0].name, "First rule")
            self.assertTrue(controller.set_document(second))
            self.assertEqual(controller.rules[0].name, "Second rule")

    def test_same_document_wrapper_does_not_reload_unsaved_docker_edits(self):
        a = FakeNode("a", "A", True)
        doc = FakeDocument([a])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule(
                "Unsaved docker edit",
                RuleKind.LINKED,
                [NodeRef("a", "A"), NodeRef("missing", "Missing")],
            )
        ]
        self.assertFalse(controller.set_document(doc))
        self.assertEqual(controller.rules[0].name, "Unsaved docker edit")

    def test_rules_are_embedded_and_document_marked_modified(self):
        a = FakeNode("a", "A", True)
        b = FakeNode("b", "B", False)
        doc = FakeDocument([a, b])
        controller = VisibilityController(bytes)
        controller.set_document(doc)
        controller.rules = [
            VisibilityRule("pair", RuleKind.INVERSE, [NodeRef("a", "A"), NodeRef("b", "B")])
        ]
        with patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        ):
            controller.save()
        self.assertTrue(doc.annotations)
        self.assertTrue(doc.modified)


if __name__ == "__main__":
    unittest.main()
