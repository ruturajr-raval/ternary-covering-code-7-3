"""Certificate-safe CNF branches for the first occupied third-center orbit.

Fix a canonical diameter pair and order its third-center orbits as in
``orbits.third_center_orbits``.  The default branch for orbit ``i`` is

``base AND OR(orbit_i) AND AND(NOT orbit_j for j < i)``.

It includes the complete exact-diameter CNF unchanged, requires at least one
literal from orbit ``i``, and forbids every center in each earlier orbit.
These literal branches are pairwise disjoint and cover every base assignment
that selects a non-anchor center.  No variable renaming is needed, so their
verified UNSAT proofs can be combined with a direct branch-coverage check.

An explicit ``representative`` mode is retained for experimental search.  It
replaces the orbit disjunction with a unit clause for the canonical
representative.  Its completeness relies on symmetry renaming.  The base
sequential-counter auxiliaries are order-sensitive and are not renamed here,
so representative-mode proofs are not directly certificate-composable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from . import branch_cnf, orbits
from .space import N, Q, RADIUS, Word, format_word


Clause = branch_cnf.Clause
LITERAL_MODE = "literal"
REPRESENTATIVE_MODE = "representative"
BRANCH_MODES = (LITERAL_MODE, REPRESENTATIVE_MODE)


@dataclass(frozen=True)
class OrbitBranchClauseCounts:
    """Exact clause accounting for one first-occupied-orbit branch."""

    base: branch_cnf.ClauseCounts
    selected_orbit_requirement: int
    earlier_orbit_exclusions: int

    @property
    def base_total(self) -> int:
        return self.base.total

    @property
    def symmetry_breaking(self) -> int:
        return (
            self.selected_orbit_requirement
            + self.earlier_orbit_exclusions
        )

    @property
    def total(self) -> int:
        return self.base_total + self.symmetry_breaking


@dataclass(frozen=True)
class FirstOccupiedOrbitBranchFormula:
    """A diameter CNF refined by one first-occupied-orbit condition."""

    base_formula: branch_cnf.DiameterBranchFormula
    mode: str
    orbit_index: int
    orbit_count: int
    orbit: orbits.StabilizerOrbit
    orbit_variables: Tuple[int, ...]
    representative_variable: int
    selected_orbit_clause: Clause
    earlier_orbit_count: int
    earlier_orbit_variables: Tuple[int, ...]
    clause_counts: OrbitBranchClauseCounts
    clauses: Tuple[Clause, ...]

    @property
    def diameter(self) -> int:
        return self.base_formula.diameter

    @property
    def limit(self) -> int:
        return self.base_formula.limit

    @property
    def primary_variable_count(self) -> int:
        return self.base_formula.primary_variable_count

    @property
    def variable_count(self) -> int:
        return self.base_formula.variable_count

    @property
    def representative(self) -> Word:
        return self.orbit.representative

    @property
    def earlier_orbit_center_count(self) -> int:
        return len(self.earlier_orbit_variables)

    @property
    def proof_composition_safe(self) -> bool:
        return self.mode == LITERAL_MODE

    @property
    def representative_fixed(self) -> bool:
        return self.mode == REPRESENTATIVE_MODE


def _validate_strict_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")


def _validate_orbit_index(orbit_index: int, orbit_count: int) -> None:
    if not 0 <= orbit_index < orbit_count:
        raise ValueError(
            "Orbit index must be in "
            f"0..{orbit_count - 1}, found {orbit_index}."
        )


def _validate_mode(mode: str) -> None:
    if not isinstance(mode, str):
        raise TypeError("Branch mode must be a string.")
    if mode not in BRANCH_MODES:
        raise ValueError(
            f"Branch mode must be one of {BRANCH_MODES}, found {mode!r}."
        )


def _orbit_variables(
    orbit: orbits.StabilizerOrbit,
) -> Tuple[int, ...]:
    return tuple(
        sorted(
            branch_cnf.primary_variable(center)
            for center in orbits.orbit_members(orbit)
        )
    )


def first_occupied_orbit_branch_formula(
    diameter: int,
    orbit_index: int,
    limit: int,
    mode: str = LITERAL_MODE,
) -> FirstOccupiedOrbitBranchFormula:
    """Build one exact first-occupied third-center orbit branch."""

    _validate_strict_integer("Branch diameter", diameter)
    _validate_strict_integer("Orbit index", orbit_index)
    _validate_strict_integer("Center limit", limit)
    _validate_mode(mode)
    base_formula = branch_cnf.diameter_branch_formula(diameter, limit)
    orbit_family = orbits.third_center_orbits(diameter)
    _validate_orbit_index(orbit_index, len(orbit_family))

    selected_orbit = orbit_family[orbit_index]
    selected_orbit_variables = _orbit_variables(selected_orbit)
    representative_variable = branch_cnf.primary_variable(
        selected_orbit.representative
    )
    earlier_orbit_variables = tuple(
        variable
        for earlier_orbit in orbit_family[:orbit_index]
        for variable in _orbit_variables(earlier_orbit)
    )

    if representative_variable not in selected_orbit_variables:
        raise AssertionError(
            "The canonical representative is absent from its orbit."
        )
    if len(set(earlier_orbit_variables)) != len(
        earlier_orbit_variables
    ):
        raise AssertionError("Earlier third-center orbits overlap.")
    if representative_variable in earlier_orbit_variables:
        raise AssertionError(
            "The selected representative occurs in an earlier orbit."
        )

    if mode == LITERAL_MODE:
        selected_orbit_clause = selected_orbit_variables
    else:
        selected_orbit_clause = (representative_variable,)
    if not selected_orbit_clause:
        raise AssertionError("A third-center orbit must be nonempty.")

    requirement_clauses = (selected_orbit_clause,)
    exclusion_clauses = tuple(
        (-variable,) for variable in earlier_orbit_variables
    )
    clauses = (
        base_formula.clauses
        + requirement_clauses
        + exclusion_clauses
    )
    counts = OrbitBranchClauseCounts(
        base=base_formula.clause_counts,
        selected_orbit_requirement=len(requirement_clauses),
        earlier_orbit_exclusions=len(exclusion_clauses),
    )
    if counts.total != len(clauses):
        raise AssertionError("Clause accounting does not match the formula.")

    return FirstOccupiedOrbitBranchFormula(
        base_formula=base_formula,
        mode=mode,
        orbit_index=orbit_index,
        orbit_count=len(orbit_family),
        orbit=selected_orbit,
        orbit_variables=selected_orbit_variables,
        representative_variable=representative_variable,
        selected_orbit_clause=selected_orbit_clause,
        earlier_orbit_count=orbit_index,
        earlier_orbit_variables=earlier_orbit_variables,
        clause_counts=counts,
        clauses=clauses,
    )


def write_orbit_branch_dimacs(
    path: Path,
    formula: FirstOccupiedOrbitBranchFormula,
) -> None:
    """Write one first-occupied-orbit branch as deterministic DIMACS."""

    counts = formula.clause_counts
    base = counts.base
    signature = formula.orbit.signature
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(
            f"c q={Q} n={N} radius={RADIUS} "
            f"diameter={formula.diameter} limit={formula.limit}\n"
        )
        handle.write(
            "c branch=first-occupied-third-center-orbit "
            f"mode={formula.mode} "
            f"orbit-index-zero-based={formula.orbit_index} "
            f"orbit-count={formula.orbit_count}\n"
        )
        handle.write(
            "c primary-variable=base-3-word-value+1 "
            f"primary-variables={formula.primary_variable_count}\n"
        )
        handle.write(
            f"c selected-orbit={formula.orbit_index} "
            f"representative={format_word(formula.representative)} "
            f"representative-variable={formula.representative_variable} "
            f"orbit-size={formula.orbit.size} "
            f"requirement-literals={len(formula.selected_orbit_clause)}\n"
        )
        handle.write(
            "c orbit-signature differing-symbol-counts="
            f"{','.join(str(value) for value in signature.differing_symbol_counts)} "
            f"equal-nonzero-weight={signature.equal_nonzero_weight}\n"
        )
        handle.write(
            f"c earlier-orbits={formula.earlier_orbit_count} "
            "earlier-orbit-centers="
            f"{formula.earlier_orbit_center_count}\n"
        )
        proof_composition = (
            "direct-literal-partition"
            if formula.proof_composition_safe
            else "experimental-symmetry-renaming-not-directly-composable"
        )
        handle.write(
            f"c proof-composition={proof_composition}\n"
        )
        handle.write(
            f"c base-clause-counts anchors={base.anchors} "
            f"forbidden-centers={base.forbidden_centers} "
            f"incompatible-pairs={base.incompatible_pairs} "
            f"covering={base.covering} cardinality={base.cardinality} "
            f"total={base.total}\n"
        )
        handle.write(
            "c branch-clause-counts selected-orbit-requirement="
            f"{counts.selected_orbit_requirement} "
            f"earlier-orbit-exclusions={counts.earlier_orbit_exclusions} "
            f"total={counts.symmetry_breaking}\n"
        )
        handle.write(
            f"p cnf {formula.variable_count} {counts.total}\n"
        )
        for clause in formula.clauses:
            handle.write(" ".join(str(literal) for literal in clause))
            handle.write(" 0\n")
