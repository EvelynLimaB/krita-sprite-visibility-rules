import unittest
from unittest.mock import patch

from sprite_visibility_rules import krita_adapter


class FakeUuid:
    def __init__(self, value):
        self.value = str(value)

    def toString(self):
        return self.value


class FakeNode:
    def __init__(self, node_id):
        self.node_id = node_id

    def uniqueId(self):
        return FakeUuid(self.node_id)

    def childNodes(self):
        return []


class LookupDocument:
    def __init__(self, nodes):
        self.nodes = {node.node_id: node for node in nodes}
        self.lookup_calls = []

    def nodeByUniqueID(self, node_id):
        value = node_id.toString()
        self.lookup_calls.append(value)
        return self.nodes.get(value)

    def rootNode(self):
        raise AssertionError("tree traversal should not run when UUID lookup succeeds")


class TraversalDocument:
    def __init__(self, nodes):
        self.root = FakeNode("root")
        self.root.childNodes = lambda: list(nodes)

    def rootNode(self):
        return self.root


class FakeView:
    def __init__(self, nodes):
        self.nodes = nodes

    def selectedNodes(self):
        return list(self.nodes)


class FakeCanvas:
    def __init__(self, nodes, broken=False):
        self.nodes = nodes
        self.broken = broken

    def view(self):
        if self.broken:
            raise RuntimeError("closed canvas")
        return FakeView(self.nodes)


class FakeWindow:
    def __init__(self, nodes):
        self.nodes = nodes

    def activeView(self):
        return FakeView(self.nodes)


class FakeApplication:
    def __init__(self, nodes):
        self.nodes = nodes

    def activeWindow(self):
        return FakeWindow(self.nodes)


class KritaAdapterTests(unittest.TestCase):
    def test_public_uuid_lookup_avoids_layer_tree_walk(self):
        first = FakeNode("a")
        second = FakeNode("b")
        document = LookupDocument([first, second])
        with patch.object(krita_adapter, "QUuid", FakeUuid):
            found = krita_adapter.resolve_tracked_nodes(document, {"a", "missing"})
        self.assertEqual(found, {"a": first})
        self.assertCountEqual(document.lookup_calls, ["a", "missing"])

    def test_tree_walk_remains_available_without_qt_uuid(self):
        first = FakeNode("a")
        document = TraversalDocument([first])
        with patch.object(krita_adapter, "QUuid", None):
            found = krita_adapter.resolve_tracked_nodes(document, {"a"})
        self.assertEqual(found, {"a": first})

    def test_canvas_selection_wins_over_another_active_window(self):
        canvas_node = FakeNode("canvas")
        other_node = FakeNode("other")
        selected = krita_adapter.selected_nodes_for_canvas(
            FakeCanvas([canvas_node]), FakeApplication([other_node])
        )
        self.assertEqual(selected, [canvas_node])

    def test_active_window_is_a_safe_fallback_for_closed_canvas(self):
        other_node = FakeNode("other")
        selected = krita_adapter.selected_nodes_for_canvas(
            FakeCanvas([], broken=True), FakeApplication([other_node])
        )
        self.assertEqual(selected, [other_node])


if __name__ == "__main__":
    unittest.main()
