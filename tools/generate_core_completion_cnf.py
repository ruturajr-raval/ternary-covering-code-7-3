#!/usr/bin/env python3

"""Generate the independent fixed-core completion CNF."""

from __future__ import annotations

import argparse
from pathlib import Path

from ternary_covering_code.core_completion_cnf import (
    core_completion_formula,
    write_core_completion_dimacs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an at-most-three-center CNF for completion of the "
            "fixed K_3(7,3) plateau core."
        )
    )
    parser.add_argument(
        "--residual-limit",
        required=True,
        type=int,
        help="Maximum number of fixed-core holes allowed to remain.",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    formula = core_completion_formula(args.residual_limit)
    write_core_completion_dimacs(args.output, formula)
    counts = formula.clause_counts
    print(
        f"output={args.output} "
        f"fixed-core-size={len(formula.fixed_core)} "
        f"core-holes={len(formula.core_holes)} "
        f"candidate-centers={len(formula.candidate_centers)} "
        f"added-center-limit={formula.added_center_limit} "
        f"residual-limit={formula.residual_limit} "
        f"variables={formula.variable_count} "
        f"clauses={counts.total} "
        f"fixed-core-exclusions={counts.fixed_core_exclusions} "
        f"residual-covering={counts.residual_covering} "
        "added-center-cardinality="
        f"{counts.added_center_cardinality} "
        "uncovered-hole-cardinality="
        f"{counts.uncovered_hole_cardinality}"
    )


if __name__ == "__main__":
    main()
