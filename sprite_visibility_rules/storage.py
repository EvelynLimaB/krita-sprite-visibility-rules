# SPDX-License-Identifier: GPL-3.0-or-later
"""JSON schema and Krita document-annotation persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Sequence

from .models import VisibilityRule, validate_rules
from .version import SCHEMA_VERSION, __version__

ANNOTATION_TYPE = "org.evelynlimab.krita.sprite_visibility_rules"
ANNOTATION_DESCRIPTION = "Sprite Visibility Rules configuration"


class StorageError(ValueError):
    pass


@dataclass
class LoadedRules:
    rules: List[VisibilityRule]
    warnings: List[str]


def serialize_rules(rules: Sequence[VisibilityRule]) -> bytes:
    errors = validate_rules(rules)
    if errors:
        raise StorageError("Invalid rules: " + " ".join(errors))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plugin_version": __version__,
        "rules": [rule.to_dict() for rule in rules],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def deserialize_rules(raw: bytes) -> LoadedRules:
    if not raw:
        return LoadedRules(rules=[], warnings=[])
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StorageError(
            "The embedded visibility-rules data is not valid JSON: {}".format(exc)
        ) from exc
    if not isinstance(payload, dict):
        raise StorageError("The embedded visibility-rules data must be a JSON object.")
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise StorageError(
            "Unsupported rule schema version {!r}; this plugin supports version {}.".format(
                version, SCHEMA_VERSION
            )
        )
    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        raise StorageError("The 'rules' field must be a list.")

    rules: List[VisibilityRule] = []
    warnings: List[str] = []
    for index, value in enumerate(raw_rules, start=1):
        try:
            if not isinstance(value, dict):
                raise TypeError("rule is not an object")
            rule = VisibilityRule.from_dict(value)
            problems = rule.validate()
            if problems:
                warnings.append("Rule {} skipped: {}".format(index, " ".join(problems)))
                continue
            rules.append(rule)
        except (KeyError, TypeError, ValueError) as exc:
            warnings.append("Rule {} skipped: {}".format(index, exc))
    return LoadedRules(rules=rules, warnings=warnings)


def _qbytearray_to_bytes(value: Any) -> bytes:
    try:
        return bytes(value)
    except TypeError:
        data = value.data() if hasattr(value, "data") else value
        return bytes(data)


def load_from_document(document: Any) -> LoadedRules:
    try:
        types = list(document.annotationTypes())
    except Exception as exc:
        raise StorageError("Krita did not expose document annotations: {}".format(exc)) from exc
    if ANNOTATION_TYPE not in types:
        return LoadedRules(rules=[], warnings=[])
    try:
        raw = _qbytearray_to_bytes(document.annotation(ANNOTATION_TYPE))
    except Exception as exc:
        raise StorageError("Could not read embedded visibility rules: {}".format(exc)) from exc
    return deserialize_rules(raw)


def save_to_document(document: Any, rules: Sequence[VisibilityRule], qbytearray_class: Any) -> None:
    raw = serialize_rules(rules)
    try:
        document.setAnnotation(
            ANNOTATION_TYPE,
            ANNOTATION_DESCRIPTION,
            qbytearray_class(raw),
        )
        document.setModified(True)
    except Exception as exc:
        raise StorageError(
            "Could not embed visibility rules in this document: {}".format(exc)
        ) from exc
