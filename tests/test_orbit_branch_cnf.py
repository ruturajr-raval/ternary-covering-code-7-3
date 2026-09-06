import os
import subprocess
import sys
import tempfile
import unittest
from itertools import product
from pathlib import Path

from ternary_covering_code import branch_cnf, orbits
from ternary_covering_code.branches import (
    branch_diameters,
    diameter_branch,
)
from ternary_covering_code.orbit_branch_cnf import (
    LITERAL_MODE,
    REPRESENTATIVE_MODE,
    first_occupied_orbit_branch_formula,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_K11_TOTALS = {
    4: (
        51127, 51131, 51155, 51159, 51165, 51201, 51273, 51285,
        51357, 51363, 51367, 51391, 51403, 51475, 51487, 51559,
        51563, 51567, 51573, 51577,
    ),
    5: (
        181237, 181242, 181262, 181267, 181277, 181317, 181357,
        181377, 181457, 181467, 181477, 181517, 181557, 181587,
        181707, 181827, 181857, 181977, 181987, 181992, 182012,
        182032, 182112, 182142, 182262, 182282, 182362, 182367,
        182372, 182382, 182392, 182397,
    ),
    6: (
        148135, 148141, 148153, 148159, 148174, 148204, 148234,
        148294, 148309, 148329, 148369, 148429, 148549, 148609,
        148729, 148749, 148764, 148794, 148854, 148974, 149064,
        149244, 149304, 149424, 149439, 149445, 149457, 149487,
        149547, 149607, 149727, 149787, 149907, 149937, 149997,
        150003, 150009, 150024, 150044, 150059, 150065,
    ),
    7: (
        43669, 43676, 43683, 43704, 43746, 43767, 43802, 43907,
        44012, 44047, 44082, 44222, 44432, 44572, 44607, 44628,
        44733, 44943, 45153, 45258, 45279, 45286, 45328, 45433,
        45573, 45678, 45720, 45727, 45734, 45755, 45790, 45825,
        45846, 45853,
    ),
}


def variables_for_orbit(orbit):
    return tuple(
        sorted(
            branch_cnf.primary_variable(center)
            for center in orbits.orbit_members(orbit)
        )
    )


def clauses_hold(clauses, true_variables):
    selected = frozenset(true_variables)
    return all(
        any(
            (literal > 0 and literal in selected)
            or (literal < 0 and -literal not in selected)
            for literal in clause
        )
        for clause in clauses
    )


class OrbitBranchCNFCountTests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self):
        for invalid_diameter in (True, 4.0, 3, 8):
            expected_error = (
                TypeError
                if isinstance(invalid_diameter, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                first_occupied_orbit_branch_formula(
                    invalid_diameter,
                    orbit_index=0,
                    limit=11,
                )

        for invalid_limit in (True, 11.0, -1):
            expected_error = (
                TypeError
                if isinstance(invalid_limit, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                first_occupied_orbit_branch_formula(
                    4,
                    orbit_index=0,
                    limit=invalid_limit,
                )

        orbit_count = len(orbits.third_center_orbits(4))
        for invalid_index in (True, 0.0, -1, orbit_count):
            expected_error = (
                TypeError
                if isinstance(invalid_index, (bool, float))
                else ValueError
            )
            with self.assertRaises(expected_error):
                first_occupied_orbit_branch_formula(
                    4,
                    orbit_index=invalid_index,
                    limit=11,
                )

        for invalid_mode, expected_error in (
            (None, TypeError),
            (False, TypeError),
            ("symmetry", ValueError),
        ):
            with self.assertRaises(expected_error):
                first_occupied_orbit_branch_formula(
                    4,
                    orbit_index=0,
                    limit=11,
                    mode=invalid_mode,
                )

    def test_every_k11_clause_count_is_exact(self):
        for diameter, expected_totals in EXPECTED_K11_TOTALS.items():
            orbit_family = orbits.third_center_orbits(diameter)
            self.assertEqual(len(orbit_family), len(expected_totals))
            earlier_center_count = 0

            for orbit_index, expected_total in enumerate(
                expected_totals
            ):
                formula = first_occupied_orbit_branch_formula(
                    diameter,
                    orbit_index=orbit_index,
                    limit=11,
                )
                counts = formula.clause_counts

                self.assertEqual(
                    counts.selected_orbit_requirement,
                    1,
                )
                self.assertEqual(
                    counts.earlier_orbit_exclusions,
                    earlier_center_count,
                )
                self.assertEqual(
                    formula.earlier_orbit_center_count,
                    earlier_center_count,
                )
                self.assertEqual(counts.total, expected_total)
                self.assertEqual(len(formula.clauses), expected_total)
                self.assertEqual(
                    formula.variable_count,
                    formula.base_formula.variable_count,
                )
                self.assertEqual(formula.mode, LITERAL_MODE)
                self.assertTrue(formula.proof_composition_safe)
                earlier_center_count += orbit_family[orbit_index].size


class OrbitBranchCNFSemanticTests(unittest.TestCase):
    def test_base_diameter_formula_is_preserved_exactly(self):
        for diameter in branch_diameters():
            orbit_count = len(orbits.third_center_orbits(diameter))
            for orbit_index in (0, orbit_count // 2, orbit_count - 1):
                formula = first_occupied_orbit_branch_formula(
                    diameter,
                    orbit_index=orbit_index,
                    limit=11,
                )
                base = branch_cnf.diameter_branch_formula(
                    diameter,
                    limit=11,
                )

                self.assertEqual(formula.base_formula, base)
                self.assertEqual(
                    formula.clauses[:len(base.clauses)],
                    base.clauses,
                )
                self.assertEqual(
                    formula.clause_counts.base,
                    base.clause_counts,
                )
                self.assertEqual(
                    formula.base_formula.cardinality_limit,
                    9,
                )
                self.assertEqual(
                    formula.base_formula.cardinality_variables,
                    base.cardinality_variables,
                )

    def test_literal_orbit_clauses_are_exact_and_deterministic(self):
        for diameter in branch_diameters():
            orbit_family = orbits.third_center_orbits(diameter)
            earlier_variables = ()

            for orbit_index, orbit in enumerate(orbit_family):
                first = first_occupied_orbit_branch_formula(
                    diameter,
                    orbit_index=orbit_index,
                    limit=11,
                )
                second = first_occupied_orbit_branch_formula(
                    diameter,
                    orbit_index=orbit_index,
                    limit=11,
                )
                current_variables = variables_for_orbit(orbit)
                expected_representative = (
                    branch_cnf.primary_variable(orbit.representative)
                )
                expected_suffix = (
                    (current_variables,)
                    + tuple(
                        (-variable,)
                        for variable in earlier_variables
                    )
                )

                self.assertEqual(first, second)
                self.assertEqual(first.orbit_index, orbit_index)
                self.assertEqual(first.orbit_count, len(orbit_family))
                self.assertEqual(first.orbit, orbit)
                self.assertEqual(first.mode, LITERAL_MODE)
                self.assertEqual(
                    first.orbit_variables,
                    current_variables,
                )
                self.assertEqual(
                    first.representative_variable,
                    expected_representative,
                )
                self.assertEqual(
                    first.selected_orbit_clause,
                    current_variables,
                )
                self.assertEqual(
                    first.earlier_orbit_count,
                    orbit_index,
                )
                self.assertEqual(
                    first.earlier_orbit_variables,
                    earlier_variables,
                )
                self.assertEqual(
                    first.clauses[len(first.base_formula.clauses):],
                    expected_suffix,
                )
                self.assertIn(
                    expected_representative,
                    current_variables,
                )
                self.assertNotIn(
                    expected_representative,
                    earlier_variables,
                )
                earlier_variables += current_variables

    def test_orbit_branches_are_complete_and_pairwise_disjoint(self):
        for diameter in branch_diameters():
            branch = diameter_branch(diameter)
            anchor_set = set(branch.anchors)
            orbit_family = orbits.third_center_orbits(diameter)
            owner = {}

            for orbit_index, orbit in enumerate(orbit_family):
                members = orbits.orbit_members(orbit)
                self.assertEqual(orbit.representative, min(members))
                for center in members:
                    self.assertNotIn(center, owner)
                    owner[center] = orbit_index
                    self.assertEqual(
                        orbits.canonical_orbit_representative(
                            diameter,
                            center,
                        ),
                        orbit.representative,
                    )

            self.assertEqual(
                set(owner),
                set(branch.allowed_centers) - anchor_set,
            )

            for later_index in range(len(orbit_family)):
                later = first_occupied_orbit_branch_formula(
                    diameter,
                    orbit_index=later_index,
                    limit=11,
                )
                expected_earlier = {
                    variable
                    for earlier_orbit in orbit_family[:later_index]
                    for variable in variables_for_orbit(earlier_orbit)
                }
                self.assertEqual(
                    set(later.earlier_orbit_variables),
                    expected_earlier,
                )
                for earlier_index in range(later_index):
                    self.assertTrue(
                        set(
                            variables_for_orbit(
                                orbit_family[earlier_index]
                            )
                        ).issubset(expected_earlier)
                    )

    def test_base_formula_requires_a_non_anchor_center(self):
        for diameter in branch_diameters():
            formula = branch_cnf.diameter_branch_formula(
                diameter,
                limit=11,
            )
            counts = formula.clause_counts
            covering_start = (
                counts.anchors
                + counts.forbidden_centers
                + counts.incompatible_pairs
            )
            covering_end = covering_start + counts.covering
            covering_clauses = formula.clauses[
                covering_start:covering_end
            ]
            anchor_variables = set(formula.anchor_variables)

            self.assertTrue(
                any(
                    anchor_variables.isdisjoint(clause)
                    for clause in covering_clauses
                )
            )

    def test_reduced_primary_assignments_have_one_literal_branch(self):
        diameter = 4
        orbit_family = orbits.third_center_orbits(diameter)
        active_orbits = orbit_family[:3]
        active_variables = tuple(
            variable
            for orbit in active_orbits
            for variable in variables_for_orbit(orbit)[:2]
        )
        conditions = []
        for orbit_index in range(len(orbit_family)):
            formula = first_occupied_orbit_branch_formula(
                diameter,
                orbit_index=orbit_index,
                limit=11,
            )
            conditions.append(
                formula.clauses[len(formula.base_formula.clauses):]
            )

        for values in product((False, True), repeat=len(active_variables)):
            selected = {
                variable
                for variable, value in zip(active_variables, values)
                if value
            }
            occupied = [
                orbit_index
                for orbit_index, orbit in enumerate(active_orbits)
                if selected.intersection(variables_for_orbit(orbit))
            ]
            matching = [
                orbit_index
                for orbit_index, condition in enumerate(conditions)
                if clauses_hold(condition, selected)
            ]
            expected = [] if not occupied else [min(occupied)]
            self.assertEqual(matching, expected)

    def test_representative_mode_is_explicitly_experimental(self):
        literal = first_occupied_orbit_branch_formula(
            4,
            orbit_index=0,
            limit=11,
        )
        representative = first_occupied_orbit_branch_formula(
            4,
            orbit_index=0,
            limit=11,
            mode=REPRESENTATIVE_MODE,
        )
        non_representative = next(
            variable
            for variable in literal.orbit_variables
            if variable != literal.representative_variable
        )
        literal_condition = literal.clauses[
            len(literal.base_formula.clauses):
        ]
        representative_condition = representative.clauses[
            len(representative.base_formula.clauses):
        ]

        self.assertTrue(literal.proof_composition_safe)
        self.assertFalse(literal.representative_fixed)
        self.assertFalse(representative.proof_composition_safe)
        self.assertTrue(representative.representative_fixed)
        self.assertEqual(
            representative.selected_orbit_clause,
            (representative.representative_variable,),
        )
        self.assertTrue(
            clauses_hold(literal_condition, {non_representative})
        )
        self.assertFalse(
            clauses_hold(
                representative_condition,
                {non_representative},
            )
        )
        self.assertEqual(
            literal.clause_counts.total,
            representative.clause_counts.total,
        )


class OrbitBranchCNFCLITests(unittest.TestCase):
    def test_cli_writes_deterministic_dimacs_and_metadata(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".orbit-branch-cnf-test-",
        ) as temporary_directory:
            first_path = Path(temporary_directory) / "first.cnf"
            second_path = Path(temporary_directory) / "second.cnf"
            base_command = [
                sys.executable,
                str(
                    ROOT
                    / "tools"
                    / "generate_orbit_branch_cnf.py"
                ),
                "--diameter",
                "4",
                "--orbit-index",
                "1",
                "--limit",
                "11",
            ]
            first = subprocess.run(
                base_command + ["--output", str(first_path)],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            second = subprocess.run(
                base_command + ["--output", str(second_path)],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first.stdout, second.stdout.replace(
                str(second_path),
                str(first_path),
            ))
            self.assertIn(
                "diameter=4 orbit-index=1 orbit-count=20 "
                "mode=literal "
                "representative=0001001 limit=11 variables=6237 "
                "clauses=51131 base-clauses=51126 "
                "selected-orbit-requirement=1 "
                "earlier-orbit-exclusions=4 "
                "proof-composition-safe=true",
                first.stdout,
            )

            rendered = first_path.read_text(
                encoding="ascii"
            ).splitlines()
            self.assertIn(
                "c branch=first-occupied-third-center-orbit "
                "mode=literal orbit-index-zero-based=1 "
                "orbit-count=20",
                rendered,
            )
            self.assertIn(
                "c selected-orbit=1 representative=0001001 "
                "representative-variable=29 orbit-size=24 "
                "requirement-literals=24",
                rendered,
            )
            self.assertIn(
                "c earlier-orbits=1 earlier-orbit-centers=4",
                rendered,
            )
            self.assertIn(
                "c proof-composition=direct-literal-partition",
                rendered,
            )
            self.assertEqual(rendered[9], "p cnf 6237 51131")
            self.assertEqual(len(rendered), 10 + 51131)

            formula = first_occupied_orbit_branch_formula(
                4,
                orbit_index=1,
                limit=11,
            )
            expected_suffix = [
                " ".join(str(literal) for literal in clause) + " 0"
                for clause in formula.clauses[
                    len(formula.base_formula.clauses):
                ]
            ]
            self.assertEqual(
                rendered[-len(expected_suffix):],
                expected_suffix,
            )


if __name__ == "__main__":
    unittest.main()
