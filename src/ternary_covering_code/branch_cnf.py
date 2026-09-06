"""Exact CNF generation for canonical diameter branches.

Primary variable ``encode(word) + 1`` selects one of the 2,187 ambient
ternary words as a code center.  For a requested diameter ``d`` the formula:

* requires both canonical diameter anchors;
* forbids every center outside distance ``d`` of either anchor;
* forbids every allowed-center pair at distance greater than ``d``;
* includes one radius-3 covering clause for every ambient target; and
* limits the selected centers to at most ``limit``.

The cardinality encoding omits the two forced anchors and therefore applies
an at-most-``limit - 2`` counter to the remaining allowed centers.  Centers
outside the anchor intersection are already forced false, so they do not
need counter variables or pairwise clauses.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Sequence, Tuple

from .branches import branch_diameters, diameter_branch
from .cnf import sequential_at_most
from .space import (
    N,
    Q,
    RADIUS,
    WORD_COUNT,
    all_words,
    ball,
    encode,
    format_word,
    hamming_distance,
)


Clause = Tuple[int, ...]


@dataclass(frozen=True)
class ClauseCounts:
    """Deterministic clause counts by logical constraint group."""

    anchors: int
    forbidden_centers: int
    incompatible_pairs: int
    covering: int
    cardinality: int

    @property
    def total(self) -> int:
        return (
            self.anchors
            + self.forbidden_centers
            + self.incompatible_pairs
            + self.covering
            + self.cardinality
        )


@dataclass(frozen=True)
class DiameterBranchFormula:
    """A complete branch formula and its auditable encoding metadata."""

    diameter: int
    limit: int
    primary_variable_count: int
    variable_count: int
    anchor_variables: Tuple[int, int]
    allowed_center_variables: Tuple[int, ...]
    cardinality_variables: Tuple[int, ...]
    cardinality_limit: int
    clause_counts: ClauseCounts
    clauses: Tuple[Clause, ...]


@dataclass(frozen=True)
class _StaticBranchClauses:
    anchor_variables: Tuple[int, int]
    allowed_center_variables: Tuple[int, ...]
    anchor_clauses: Tuple[Clause, ...]
    forbidden_center_clauses: Tuple[Clause, ...]
    incompatible_pair_clauses: Tuple[Clause, ...]
    covering_clauses: Tuple[Clause, ...]


def primary_variable(word: Sequence[int]) -> int:
    """Return the one-based primary variable for an ambient word."""

    center = tuple(word)
    if len(center) != N:
        raise ValueError(f"Expected a word of length {N}, found {len(center)}.")
    return encode(center) + 1


def _validate_diameter(diameter: int) -> None:
    if isinstance(diameter, bool) or not isinstance(diameter, int):
        raise TypeError("Branch diameter must be an integer.")
    if diameter not in branch_diameters():
        raise ValueError(
            f"Branch diameter must be one of {branch_diameters()}, "
            f"found {diameter}."
        )


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("Center limit must be an integer.")
    if limit < 0:
        raise ValueError("Center limit must be nonnegative.")


@lru_cache(maxsize=None)
def _static_branch_clauses(diameter: int) -> _StaticBranchClauses:
    _validate_diameter(diameter)
    branch = diameter_branch(diameter)
    words = all_words()
    allowed_centers = branch.allowed_centers
    allowed_center_set = frozenset(allowed_centers)
    allowed_variables = tuple(
        primary_variable(center) for center in allowed_centers
    )
    allowed_variable_set = frozenset(allowed_variables)
    anchor_variables = tuple(
        primary_variable(anchor) for anchor in branch.anchors
    )

    anchor_clauses = tuple((variable,) for variable in anchor_variables)
    forbidden_center_clauses = tuple(
        (-variable,)
        for variable in range(1, WORD_COUNT + 1)
        if variable not in allowed_variable_set
    )
    incompatible_pair_clauses = tuple(
        (-primary_variable(left), -primary_variable(right))
        for left, right in combinations(allowed_centers, 2)
        if hamming_distance(left, right) > diameter
    )
    covering_clauses = tuple(
        tuple(
            sorted(
                primary_variable(center)
                for center in ball(target, radius=RADIUS, q=Q)
                if center in allowed_center_set
            )
        )
        for target in words
    )

    return _StaticBranchClauses(
        anchor_variables=anchor_variables,
        allowed_center_variables=allowed_variables,
        anchor_clauses=anchor_clauses,
        forbidden_center_clauses=forbidden_center_clauses,
        incompatible_pair_clauses=incompatible_pair_clauses,
        covering_clauses=covering_clauses,
    )


def diameter_branch_formula(
    diameter: int,
    limit: int,
) -> DiameterBranchFormula:
    """Build the exact at-most-``limit`` CNF for one diameter branch."""

    _validate_diameter(diameter)
    _validate_limit(limit)
    static = _static_branch_clauses(diameter)
    anchor_variable_set = frozenset(static.anchor_variables)
    cardinality_variables = tuple(
        variable
        for variable in static.allowed_center_variables
        if variable not in anchor_variable_set
    )
    cardinality_limit = limit - len(static.anchor_variables)
    cardinality_clauses, next_variable, _ = sequential_at_most(
        cardinality_variables,
        cardinality_limit,
        WORD_COUNT + 1,
    )
    frozen_cardinality_clauses = tuple(
        tuple(clause) for clause in cardinality_clauses
    )

    clauses = (
        static.anchor_clauses
        + static.forbidden_center_clauses
        + static.incompatible_pair_clauses
        + static.covering_clauses
        + frozen_cardinality_clauses
    )
    counts = ClauseCounts(
        anchors=len(static.anchor_clauses),
        forbidden_centers=len(static.forbidden_center_clauses),
        incompatible_pairs=len(static.incompatible_pair_clauses),
        covering=len(static.covering_clauses),
        cardinality=len(frozen_cardinality_clauses),
    )
    if counts.total != len(clauses):
        raise AssertionError("Clause accounting does not match the formula.")

    return DiameterBranchFormula(
        diameter=diameter,
        limit=limit,
        primary_variable_count=WORD_COUNT,
        variable_count=next_variable - 1,
        anchor_variables=static.anchor_variables,
        allowed_center_variables=static.allowed_center_variables,
        cardinality_variables=cardinality_variables,
        cardinality_limit=cardinality_limit,
        clause_counts=counts,
        clauses=clauses,
    )


def write_branch_dimacs(
    path: Path,
    formula: DiameterBranchFormula,
) -> None:
    """Write a branch formula in deterministic DIMACS CNF format."""

    branch = diameter_branch(formula.diameter)
    counts = formula.clause_counts
    anchors = ",".join(format_word(anchor) for anchor in branch.anchors)
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(
            f"c q={Q} n={N} radius={RADIUS} diameter={formula.diameter} "
            f"limit={formula.limit}\n"
        )
        handle.write(
            "c primary-variable=base-3-word-value+1 "
            f"primary-variables={formula.primary_variable_count}\n"
        )
        handle.write(
            f"c anchors={anchors} "
            f"allowed-centers={len(formula.allowed_center_variables)}\n"
        )
        handle.write(
            f"c clause-counts anchors={counts.anchors} "
            f"forbidden-centers={counts.forbidden_centers} "
            f"incompatible-pairs={counts.incompatible_pairs} "
            f"covering={counts.covering} "
            f"cardinality={counts.cardinality}\n"
        )
        handle.write(
            f"p cnf {formula.variable_count} {counts.total}\n"
        )
        for clause in formula.clauses:
            handle.write(" ".join(str(literal) for literal in clause))
            handle.write(" 0\n")
