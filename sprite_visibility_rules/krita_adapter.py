# SPDX-License-Identifier: GPL-3.0-or-later
"""Thin adapters around Krita's libkis Python objects."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

try:
    from .qt_compat import QUuid
except ImportError:  # Pure engine tests can run without Qt installed.
    QUuid = None

from .models import NodeRef


def uuid_string(value: Any) -> str:
    if hasattr(value, "toString"):
        return str(value.toString())
    return str(value)


def node_ref(node: Any) -> NodeRef:
    return NodeRef(node_id=uuid_string(node.uniqueId()), name=str(node.name()))


def walk_nodes(root: Any) -> Iterable[Any]:
    stack = list(reversed(list(root.childNodes())))
    while stack:
        node = stack.pop()
        yield node
        children = list(node.childNodes())
        stack.extend(reversed(children))


def resolve_tracked_nodes(document: Any, tracked_ids: Set[str]) -> Dict[str, Any]:
    """Resolve tracked nodes efficiently, with a compatibility fallback.

    Krita 6 exposes ``Document.nodeByUniqueID(QUuid)``. Using it prevents an
    automatic rule set with only a few members from walking a large layer tree
    eight times per second. Older/fake API surfaces fall back to traversal.
    """

    if not tracked_ids:
        return {}

    lookup = getattr(document, "nodeByUniqueID", None)
    if callable(lookup) and QUuid is not None:
        found: Dict[str, Any] = {}
        lookup_failed = False
        for node_id in tracked_ids:
            try:
                node = lookup(QUuid(node_id))
            except Exception:
                # A downstream build may expose the method with a binding that
                # rejects PyQt's QUuid. The public tree API remains a safe path.
                lookup_failed = True
                break
            if node is not None:
                found[node_id] = node
        if not lookup_failed:
            return found

    found = {}
    unresolved = set(tracked_ids)
    for node in walk_nodes(document.rootNode()):
        node_id = uuid_string(node.uniqueId())
        if node_id in unresolved:
            found[node_id] = node
            unresolved.remove(node_id)
            if not unresolved:
                break
    return found


def selected_nodes(application: Any) -> List[Any]:
    window = application.activeWindow()
    if window is None:
        return []
    view = window.activeView()
    if view is None:
        return []
    return list(view.selectedNodes())


def active_node_id(document: Any) -> Optional[str]:
    node = document.activeNode()
    return uuid_string(node.uniqueId()) if node is not None else None
