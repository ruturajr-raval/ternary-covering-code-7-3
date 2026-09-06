import json
import os
import subprocess
import sys
import unittest
from collections import defaultdict
from pathlib import Path

from ternary_covering_code.branches import (
    allowed_centers,
    branch_diameters,
    canonical_diameter_pair,
    diameter_branch,
)
from ternary_covering_code.orbits import (
    allowed_center_orbits,
    canonical_orbit_representative,
    orbit_members,
    orbit_size_from_signature,
    stabilizer_order,
    stabilizer_signature,
    third_center_orbits,
)
from ternary_covering_code.space import N, format_word, hamming_distance


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ORBIT_COUNTS = {
    4: (22, 20),
    5: (34, 32),
    6: (43, 41),
    7: (36, 34),
}


def independent_signature(diameter, center):
    differing = center[:diameter]
    equal = center[diameter:]
    return (
        differing.count(0),
        differing.count(1),
        differing.count(2),
        sum(symbol != 0 for symbol in equal),
    )


def generator_images(diameter, center):
    for index in range(diameter - 1):
        image = list(center)
        image[index], image[index + 1] = (
            image[index + 1],
            image[index],
        )
        yield tuple(image)

    for index in range(diameter, N - 1):
        image = list(center)
        image[index], image[index + 1] = (
            image[index + 1],
            image[index],
        )
        yield tuple(image)

    for index in range(diameter, N):
        image = list(center)
        if image[index] == 1:
            image[index] = 2
        elif image[index] == 2:
            image[index] = 1
        yield tuple(image)


class StabilizerOrbitTests(unittest.TestCase):
    def test_diameter_types_are_strict(self):
        for invalid in (True, 4.0):
            with self.assertRaises(TypeError):
                stabilizer_order(invalid)
            with self.assertRaises(TypeError):
                allowed_center_orbits(invalid)

    def test_orbit_counts_are_locked(self):
        for diameter, expected in EXPECTED_ORBIT_COUNTS.items():
            self.assertEqual(
                (
                    len(allowed_center_orbits(diameter)),
                    len(third_center_orbits(diameter)),
                ),
                expected,
            )

    def test_complete_partition_of_every_allowed_center(self):
        for diameter in branch_diameters():
            centers = allowed_centers(diameter)
            center_set = set(centers)
            expanded = {}

            for orbit in allowed_center_orbits(diameter):
                members = orbit_members(orbit)
                self.assertEqual(len(members), orbit.size)
                self.assertEqual(len(set(members)), orbit.size)
                self.assertEqual(orbit.representative, min(members))
                self.assertEqual(
                    orbit.size,
                    orbit_size_from_signature(
                        diameter,
                        orbit.signature,
                    ),
                )
                self.assertEqual(
                    stabilizer_signature(
                        diameter,
                        orbit.representative,
                    ),
                    orbit.signature,
                )
                for member in members:
                    self.assertIn(member, center_set)
                    self.assertNotIn(member, expanded)
                    expanded[member] = orbit.representative

            self.assertEqual(set(expanded), center_set)
            for center in centers:
                self.assertEqual(
                    canonical_orbit_representative(diameter, center),
                    expanded[center],
                )

    def test_complete_invariants_match_independent_buckets(self):
        for diameter in branch_diameters():
            buckets = defaultdict(set)
            for center in allowed_centers(diameter):
                buckets[independent_signature(diameter, center)].add(center)

            actual = {}
            for orbit in allowed_center_orbits(diameter):
                signature = (
                    orbit.signature.differing_zero_count,
                    orbit.signature.differing_one_count,
                    orbit.signature.differing_two_count,
                    orbit.signature.equal_nonzero_weight,
                )
                actual[signature] = set(orbit_members(orbit))

            self.assertEqual(set(actual), set(buckets))
            for signature, members in buckets.items():
                self.assertEqual(actual[signature], members)

    def test_stabilizer_generators_preserve_every_allowed_orbit(self):
        for diameter in branch_diameters():
            centers = allowed_centers(diameter)
            center_set = set(centers)
            anchors = canonical_diameter_pair(diameter)
            for center in centers:
                representative = canonical_orbit_representative(
                    diameter,
                    center,
                )
                for image in generator_images(diameter, center):
                    self.assertIn(image, center_set)
                    self.assertEqual(
                        canonical_orbit_representative(diameter, image),
                        representative,
                    )
                    for anchor in anchors:
                        self.assertEqual(
                            hamming_distance(center, anchor),
                            hamming_distance(image, anchor),
                        )

    def test_third_center_orbits_remove_exactly_the_two_anchors(self):
        for diameter in branch_diameters():
            branch = diameter_branch(diameter)
            anchors = set(branch.anchors)
            full_orbits = allowed_center_orbits(diameter)
            anchor_orbits = tuple(
                orbit for orbit in full_orbits if orbit.contains_anchor
            )
            self.assertEqual(len(anchor_orbits), 2)
            self.assertTrue(all(orbit.size == 1 for orbit in anchor_orbits))
            self.assertEqual(
                {
                    member
                    for orbit in anchor_orbits
                    for member in orbit_members(orbit)
                },
                anchors,
            )

            third_members = {
                member
                for orbit in third_center_orbits(diameter)
                for member in orbit_members(orbit)
            }
            self.assertEqual(
                third_members,
                set(branch.allowed_centers) - anchors,
            )
            for center in third_members:
                self.assertTrue(
                    branch.code_is_admissible(
                        branch.anchors + (center,)
                    )
                )

    def test_orbit_sizes_divide_stabilizer_order(self):
        for diameter in branch_diameters():
            group_order = stabilizer_order(diameter)
            for orbit in allowed_center_orbits(diameter):
                self.assertEqual(group_order % orbit.size, 0)


class OrbitGeneratorTests(unittest.TestCase):
    def test_cli_json_is_deterministic(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        command = [
            sys.executable,
            str(ROOT / "tools" / "generate_orbits.py"),
        ]
        first = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        second = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(first, second)

        payload = json.loads(first)
        self.assertFalse(payload["members_included"])
        self.assertEqual(len(payload["branches"]), 4)
        for record in payload["branches"]:
            diameter = record["diameter"]
            orbits = allowed_center_orbits(diameter)
            self.assertEqual(
                record["allowed_center_count"],
                len(allowed_centers(diameter)),
            )
            self.assertEqual(
                record["allowed_center_orbit_count"],
                len(orbits),
            )
            self.assertEqual(
                record["third_center_orbit_count"],
                len(third_center_orbits(diameter)),
            )
            self.assertEqual(
                record["pointwise_stabilizer_order"],
                stabilizer_order(diameter),
            )
            self.assertEqual(
                [item["representative"] for item in record["orbits"]],
                [format_word(orbit.representative) for orbit in orbits],
            )
            self.assertNotIn("members", record["orbits"][0])

    def test_cli_member_output_exhausts_allowed_centers(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        command = [
            sys.executable,
            str(ROOT / "tools" / "generate_orbits.py"),
            "--include-members",
        ]
        output = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        payload = json.loads(output)
        self.assertTrue(payload["members_included"])
        for record in payload["branches"]:
            diameter = record["diameter"]
            emitted = [
                member
                for orbit in record["orbits"]
                for member in orbit["members"]
            ]
            self.assertEqual(len(emitted), len(set(emitted)))
            self.assertEqual(
                sorted(emitted),
                [
                    format_word(center)
                    for center in allowed_centers(diameter)
                ],
            )


if __name__ == "__main__":
    unittest.main()
