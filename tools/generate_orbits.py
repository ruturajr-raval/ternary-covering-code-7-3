#!/usr/bin/env python3

"""Emit deterministic third-center orbit data for every diameter branch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from ternary_covering_code.branches import (
    allowed_centers,
    branch_diameters,
    canonical_diameter_pair,
)
from ternary_covering_code.orbits import (
    StabilizerOrbit,
    allowed_center_orbits,
    orbit_members,
    stabilizer_order,
    third_center_orbits,
)
from ternary_covering_code.space import N, Q, RADIUS, format_word


def orbit_record(
    orbit: StabilizerOrbit,
    include_members: bool,
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "representative": format_word(orbit.representative),
        "orbit_size": orbit.size,
        "signature": {
            "differing_symbol_counts": list(
                orbit.signature.differing_symbol_counts
            ),
            "equal_nonzero_weight": (
                orbit.signature.equal_nonzero_weight
            ),
        },
        "contains_anchor": orbit.contains_anchor,
        "eligible_as_distinct_third_center": not orbit.contains_anchor,
    }
    if include_members:
        record["members"] = [
            format_word(member) for member in orbit_members(orbit)
        ]
    return record


def build_payload(include_members: bool = False) -> Dict[str, Any]:
    branches = []
    for diameter in branch_diameters():
        centers = allowed_centers(diameter)
        orbits = allowed_center_orbits(diameter)
        third_orbits = third_center_orbits(diameter)
        branches.append(
            {
                "diameter": diameter,
                "anchors": [
                    format_word(anchor)
                    for anchor in canonical_diameter_pair(diameter)
                ],
                "allowed_center_count": len(centers),
                "allowed_center_orbit_count": len(orbits),
                "distinct_third_center_count": len(centers) - 2,
                "third_center_orbit_count": len(third_orbits),
                "pointwise_stabilizer_order": stabilizer_order(diameter),
                "orbits": [
                    orbit_record(orbit, include_members)
                    for orbit in orbits
                ],
            }
        )

    return {
        "schema": "ternary-covering-code-third-center-orbits-v1",
        "parameters": {
            "alphabet_size": Q,
            "length": N,
            "covering_radius": RADIUS,
        },
        "stabilizer": {
            "kind": "pointwise stabilizer of the ordered anchor pair",
            "coordinate_blocks": [
                "The first d coordinates may be permuted.",
                "The final 7-d coordinates may be permuted.",
            ],
            "symbol_action": (
                "First-block symbols are fixed. In each final coordinate, "
                "symbols 1 and 2 may be exchanged independently."
            ),
            "complete_invariants": [
                "counts of symbols 0, 1, and 2 in the first d coordinates",
                "nonzero weight in the final 7-d coordinates",
            ],
        },
        "scope": {
            "proved": (
                "The listed orbits partition every center satisfying both "
                "canonical-anchor distance constraints."
            ),
            "not_proved": (
                "An orbit representative need not extend to a covering "
                "code. Later selected centers must also satisfy all "
                "pairwise branch-distance constraints."
            ),
        },
        "members_included": include_members,
        "branches": branches,
    }


def render_payload(include_members: bool = False) -> str:
    return (
        json.dumps(
            build_payload(include_members=include_members),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Enumerate pointwise anchor-stabilizer orbits for the third "
            "center in every K_3(7,3) diameter branch."
        )
    )
    parser.add_argument(
        "--include-members",
        action="store_true",
        help="Include every allowed center in its orbit record.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this path instead of standard output.",
    )
    args = parser.parse_args()

    rendered = render_payload(include_members=args.include_members)
    if args.output is None:
        sys.stdout.write(rendered)
        return

    with args.output.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(rendered)
    print(f"output={args.output} branches={len(branch_diameters())}")


if __name__ == "__main__":
    main()
