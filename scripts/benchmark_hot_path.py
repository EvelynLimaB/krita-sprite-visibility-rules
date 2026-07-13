#!/usr/bin/env python3
"""Synthetic benchmark for the pure visibility-rule hot path.

This is not a Krita rendering benchmark. It isolates rule dispatch so changes
can be compared on the same machine without depending on canvas size or GPU.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule  # noqa: E402
from sprite_visibility_rules.rule_engine import compile_rules, enforce_rules  # noqa: E402


def build_case(rule_count: int, members_per_rule: int):
    rules = []
    states = {}
    for rule_index in range(rule_count):
        member_ids = [
            "rule-{}-member-{}".format(rule_index, member_index)
            for member_index in range(members_per_rule)
        ]
        rules.append(
            VisibilityRule(
                "Rule {}".format(rule_index),
                RuleKind.LINKED,
                [NodeRef(node_id, node_id) for node_id in member_ids],
            )
        )
        states.update({node_id: True for node_id in member_ids})
    states["rule-0-member-0"] = False
    return states, rules


def benchmark(rule_count: int, members_per_rule: int, iterations: int) -> float:
    states, rules = build_case(rule_count, members_per_rule)
    compiled = compile_rules(rules)
    samples = []
    for _repeat in range(7):
        started = time.perf_counter_ns()
        for _iteration in range(iterations):
            enforce_rules(
                states,
                ["rule-0-member-0"],
                rules,
                active_id="rule-0-member-0",
                compiled=compiled,
            )
        samples.append((time.perf_counter_ns() - started) / iterations)
    return statistics.median(samples) / 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--members", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=2000)
    args = parser.parse_args()

    print("Synthetic rule-dispatch median, microseconds per visibility event")
    for rule_count in (10, 50, 100, 250):
        value = benchmark(rule_count, args.members, args.iterations)
        print("{:>4} rules: {:>9.2f} us".format(rule_count, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
