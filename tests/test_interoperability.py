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
        self.active = nodes[0] if nodes else None

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


def ref(node):
    return NodeRef(node.node_id, node.name())


class ExternalPluginCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.resolve_patch = patch(
            "sprite_visibility_rules.controller.resolve_tracked_nodes",
            side_effect=resolve_fake,
        )
        self.resolve_patch.start()
        self.addCleanup(self.resolve_patch.stop)

    @staticmethod
    def controller_for(document, rules):
        controller = VisibilityController(bytes)
        controller.set_document(document)
        controller.rules = rules
        controller.snapshot(force_resolve=True)
        return controller

    def test_layer_visibility_switch_valid_transition_is_left_untouched(self):
        """Adjacent sibling switching may already produce a valid exclusive state."""

        neutral = FakeNode("neutral", "Neutral", True)
        happy = FakeNode("happy", "Happy", False)
        angry = FakeNode("angry", "Angry", False)
        document = FakeDocument([neutral, happy, angry])
        controller = self.controller_for(
            document,
            [
                VisibilityRule(
                    "Eyes",
                    RuleKind.EXCLUSIVE,
                    [ref(neutral), ref(happy), ref(angry)],
                    allow_none=False,
                    fallback_id=neutral.node_id,
                )
            ],
        )

        # Equivalent to Layer Visibility Switch: hide current, select sibling,
        # then show the sibling before returning control to Krita's event loop.
        neutral.setVisible(False)
        document.active = happy
        happy.setVisible(True)
        for node in (neutral, happy, angry):
            node.set_calls = 0

        report = controller.scan()

        self.assertEqual(report.changed_count, 0)
        self.assertEqual(document.refreshes, 0)
        self.assertFalse(neutral.visible())
        self.assertTrue(happy.visible())
        self.assertFalse(angry.visible())
        self.assertEqual(sum(node.set_calls for node in (neutral, happy, angry)), 0)

    def test_sneaky_visibility_untracked_selection_is_ignored(self):
        """Ad-hoc selected-layer commands must not affect unrelated rule state."""

        jacket_on = FakeNode("jacket-on", "Jacket on", True)
        jacket_off = FakeNode("jacket-off", "Jacket off", False)
        guide = FakeNode("guide", "Guide", True)
        notes = FakeNode("notes", "Notes", True)
        document = FakeDocument([jacket_on, jacket_off, guide, notes])
        controller = self.controller_for(
            document,
            [
                VisibilityRule(
                    "Jacket",
                    RuleKind.INVERSE,
                    [ref(jacket_on), ref(jacket_off)],
                )
            ],
        )

        # Equivalent to Sneaky Visibility operating on selected utility layers.
        guide.setVisible(False)
        notes.setVisible(False)
        report = controller.scan()

        self.assertEqual(report.changed_count, 0)
        self.assertEqual(document.refreshes, 0)
        self.assertTrue(jacket_on.visible())
        self.assertFalse(jacket_off.visible())
        self.assertFalse(guide.visible())
        self.assertFalse(notes.visible())

    def test_sneaky_visibility_invalid_multi_layer_result_normalizes_once(self):
        """A multi-selection action may create an invalid exclusive state."""

        neutral = FakeNode("neutral", "Neutral", True)
        happy = FakeNode("happy", "Happy", False)
        angry = FakeNode("angry", "Angry", False)
        document = FakeDocument([neutral, happy, angry])
        controller = self.controller_for(
            document,
            [
                VisibilityRule(
                    "Eyes",
                    RuleKind.EXCLUSIVE,
                    [ref(neutral), ref(happy), ref(angry)],
                    allow_none=False,
                    fallback_id=neutral.node_id,
                )
            ],
        )

        neutral.setVisible(False)
        happy.setVisible(True)
        angry.setVisible(True)
        document.active = angry
        for node in (neutral, happy, angry):
            node.set_calls = 0

        report = controller.scan()

        self.assertEqual(report.changed_count, 1)
        self.assertEqual(document.refreshes, 1)
        self.assertFalse(neutral.visible())
        self.assertFalse(happy.visible())
        self.assertTrue(angry.visible())
        self.assertEqual(sum(node.set_calls for node in (neutral, happy, angry)), 1)

    def test_quicktogglehidden_valid_label_batch_is_left_untouched(self):
        """A complete color-label batch may already satisfy a linked rule."""

        face = FakeNode("face", "Face shadow", True)
        body = FakeNode("body", "Body shadow", True)
        arm = FakeNode("arm", "Arm shadow", True)
        document = FakeDocument([face, body, arm])
        controller = self.controller_for(
            document,
            [VisibilityRule("Shadows", RuleKind.LINKED, [ref(face), ref(body), ref(arm)])],
        )

        # Equivalent to QuickToggleHidden setting every matching label to one state.
        for node in (face, body, arm):
            node.setVisible(False)
            node.set_calls = 0

        report = controller.scan()

        self.assertEqual(report.changed_count, 0)
        self.assertEqual(document.refreshes, 0)
        self.assertTrue(all(not node.visible() for node in (face, body, arm)))
        self.assertEqual(sum(node.set_calls for node in (face, body, arm)), 0)

    def test_partial_external_batch_is_corrected_with_one_refresh(self):
        """Only the minimum dependent correction is written and refreshed once."""

        face = FakeNode("face", "Face shadow", True)
        body = FakeNode("body", "Body shadow", True)
        arm = FakeNode("arm", "Arm shadow", True)
        document = FakeDocument([face, body, arm])
        controller = self.controller_for(
            document,
            [VisibilityRule("Shadows", RuleKind.LINKED, [ref(face), ref(body), ref(arm)])],
        )

        face.setVisible(False)
        body.setVisible(False)
        document.active = face
        for node in (face, body, arm):
            node.set_calls = 0

        report = controller.scan()

        self.assertEqual(report.changed_count, 1)
        self.assertEqual(document.refreshes, 1)
        self.assertTrue(all(not node.visible() for node in (face, body, arm)))
        self.assertEqual(sum(node.set_calls for node in (face, body, arm)), 1)


if __name__ == "__main__":
    unittest.main()
