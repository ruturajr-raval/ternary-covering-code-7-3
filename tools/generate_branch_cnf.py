#!/usr/bin/env python3

"""Generate one exact canonical diameter-branch CNF."""

from __future__ import annotations

import argparse
from pathlib import Path

from ternary_covering_code.branch_cnf import (
    diameter_branch_formula,
    write_branch_dimacs,
)
from ternary_covering_code.branches import branch_diameters


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an exact at-most-k CNF for one K_3(7,3) "
            "diameter branch."
        )
    )
    parser.add_argument(
        "--diameter",
        required=True,
        type=int,
        choices=branch_diameters(),
    )
    parser.add_argument("--limit", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    formula = diameter_branch_formula(
        diameter=args.diameter,
        limit=args.limit,
    )
    write_branch_dimacs(args.output, formula)
    counts = formula.clause_counts
    print(
        f"output={args.output} diameter={formula.diameter} "
        f"limit={formula.limit} variables={formula.variable_count} "
        f"clauses={counts.total} anchors={counts.anchors} "
        f"forbidden-centers={counts.forbidden_centers} "
        f"incompatible-pairs={counts.incompatible_pairs} "
        f"covering={counts.covering} cardinality={counts.cardinality}"
    )


if __name__ == "__main__":
    main()
