# SPDX-License-Identifier: GPL-3.0-or-later
"""Thin adapters around Krita's libkis Python objects."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

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
    if not tracked_ids:
        return {}
    found: Dict[str, Any] = {}
    for node in walk_nodes(document.rootNode()):
        node_id = uuid_string(node.uniqueId())
        if node_id in tracked_ids:
            found[node_id] = node
            if len(found) == len(tracked_ids):
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
