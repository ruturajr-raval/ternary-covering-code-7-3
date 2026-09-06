#!/usr/bin/env python3

"""Emit deterministic JSON records for all diameter-pair branches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from ternary_covering_code.branches import (
    BRANCH_ASSUMPTIONS,
    branch_diameters,
    covering_diameter_lower_bound,
    diameter_branches,
)
from ternary_covering_code.space import N, Q, RADIUS, format_word


def build_payload() -> Dict[str, Any]:
    branches = []
    for branch in diameter_branches():
        branches.append(
            {
                "diameter": branch.diameter,
                "anchors": [
                    format_word(anchor) for anchor in branch.anchors
                ],
                "allowed_center_count": len(branch.allowed_centers),
                "allowed_centers": [
                    format_word(center) for center in branch.allowed_centers
                ],
                "selected_center_constraints": {
                    "anchors_required": True,
                    "maximum_pairwise_distance": branch.diameter,
                },
            }
        )

    return {
        "schema": "ternary-covering-code-diameter-branches-v1",
        "parameters": {
            "alphabet_size": Q,
            "length": N,
            "covering_radius": RADIUS,
        },
        "assumptions": list(BRANCH_ASSUMPTIONS),
        "coverage_argument": {
            "diameter_lower_bound": covering_diameter_lower_bound(),
            "diameter_upper_bound": N,
            "covered_diameters": list(branch_diameters()),
            "lower_bound_reason": (
                "A word at distance 7 from any chosen center must be covered "
                "within distance 3, forcing another center at distance at "
                "least 4."
            ),
        },
        "branches": branches,
    }


def render_payload() -> str:
    return json.dumps(build_payload(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Enumerate canonical diameter-pair branches for K_3(7,3)."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this path instead of standard output.",
    )
    args = parser.parse_args()

    rendered = render_payload()
    if args.output is None:
        sys.stdout.write(rendered)
        return

    with args.output.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(rendered)
    print(f"output={args.output} branches={len(branch_diameters())}")


if __name__ == "__main__":
    main()
