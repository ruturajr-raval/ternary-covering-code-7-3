#!/usr/bin/env python3

"""Generate one first-occupied third-center orbit CNF branch."""

from __future__ import annotations

import argparse
from pathlib import Path

from ternary_covering_code.branches import branch_diameters
from ternary_covering_code.orbit_branch_cnf import (
    BRANCH_MODES,
    LITERAL_MODE,
    first_occupied_orbit_branch_formula,
    write_orbit_branch_dimacs,
)
from ternary_covering_code.space import format_word


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an exact at-most-k K_3(7,3) diameter CNF refined "
            "by a literal first-occupied third-center orbit."
        )
    )
    parser.add_argument(
        "--diameter",
        required=True,
        type=int,
        choices=branch_diameters(),
    )
    parser.add_argument(
        "--orbit-index",
        required=True,
        type=int,
        help="Zero-based index in the ordered third-center orbit list.",
    )
    parser.add_argument("--limit", required=True, type=int)
    parser.add_argument(
        "--mode",
        choices=BRANCH_MODES,
        default=LITERAL_MODE,
        help=(
            "Use certificate-safe literal partitioning by default. "
            "Representative mode is experimental search-only symmetry "
            "fixing."
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    formula = first_occupied_orbit_branch_formula(
        diameter=args.diameter,
        orbit_index=args.orbit_index,
        limit=args.limit,
        mode=args.mode,
    )
    write_orbit_branch_dimacs(args.output, formula)
    counts = formula.clause_counts
    print(
        f"output={args.output} diameter={formula.diameter} "
        f"orbit-index={formula.orbit_index} "
        f"orbit-count={formula.orbit_count} "
        f"mode={formula.mode} "
        f"representative={format_word(formula.representative)} "
        f"limit={formula.limit} variables={formula.variable_count} "
        f"clauses={counts.total} base-clauses={counts.base_total} "
        "selected-orbit-requirement="
        f"{counts.selected_orbit_requirement} "
        f"earlier-orbit-exclusions="
        f"{counts.earlier_orbit_exclusions} "
        "proof-composition-safe="
        f"{str(formula.proof_composition_safe).lower()}"
    )


if __name__ == "__main__":
    main()
