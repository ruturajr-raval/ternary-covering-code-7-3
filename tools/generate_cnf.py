#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from ternary_covering_code.cnf import covering_formula, write_dimacs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    formula = covering_formula(limit=args.limit, anchor_zero=True)
    write_dimacs(args.output, formula, limit=args.limit)
    print(
        f"output={args.output} variables={formula.variable_count} "
        f"clauses={len(formula.clauses)}"
    )


if __name__ == "__main__":
    main()
