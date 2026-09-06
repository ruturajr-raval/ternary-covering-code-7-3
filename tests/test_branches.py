import json
import os
import subprocess
import sys
import unittest
from itertools import combinations
from pathlib import Path

from ternary_covering_code.branches import (
    BRANCH_ASSUMPTIONS,
    allowed_centers,
    antipode,
    branch_diameters,
    canonical_diameter_pair,
    covering_diameter_lower_bound,
    diameter_branch,
    diameter_branches,
    normalize_code_on_diameter_pair,
    normalize_diameter_pair,
)
from ternary_covering_code.space import (
    N,
    Q,
    RADIUS,
    WORD_COUNT,
    all_words,
    format_word,
    hamming_distance,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ALLOWED_COUNTS = {
    4: 453,
    5: 1163,
    6: 1933,
    7: 2187,
}


def noncanonical_pair(diameter):
    left = (2, 0, 1, 2, 1, 0, 2)
    differing_positions = (6, 1, 4, 0, 5, 2, 3)[:diameter]
    right = list(left)
    for offset, position in enumerate(differing_positions):
        right[position] = (right[position] + 1 + offset % 2) % Q
    return left, tuple(right)


class DiameterCoverageTests(unittest.TestCase):
    def test_radius_three_cover_diameters_are_exhausted(self):
        self.assertEqual(covering_diameter_lower_bound(), N - RADIUS)
        self.assertEqual(branch_diameters(), (4, 5, 6, 7))
        self.assertEqual(
            branch_diameters(),
            tuple(range(covering_diameter_lower_bound(), N + 1)),
        )

        zero = (0,) * N
        far_word = antipode(zero)
        self.assertEqual(hamming_distance(zero, far_word), N)
        possible_covering_centers = tuple(
            word
            for word in all_words()
            if hamming_distance(word, far_word) <= RADIUS
        )
        self.assertTrue(possible_covering_centers)
        self.assertTrue(
            all(
                hamming_distance(zero, center) >= N - RADIUS
                for center in possible_covering_centers
            )
        )

    def test_assumptions_distinguish_filter_from_full_branch(self):
        combined = " ".join(BRANCH_ASSUMPTIONS).lower()
        self.assertIn("cover", combined)
        self.assertIn("necessary", combined)
        self.assertIn("pairwise", combined)

    def test_diameter_four_full_support_count(self):
        full_support = tuple(
            word for word in all_words() if all(symbol != 0 for symbol in word)
        )
        self.assertEqual(len(full_support), 128)

        for center in all_words():
            if hamming_distance(center, (0,) * N) > 4:
                continue
            covered = sum(
                hamming_distance(center, word) <= RADIUS
                for word in full_support
            )
            self.assertLessEqual(covered, 8)
            if covered:
                self.assertEqual(
                    sum(symbol != 0 for symbol in center),
                    4,
                )

        minimum_code_size = 1 + (len(full_support) + 7) // 8
        self.assertEqual(minimum_code_size, 17)


class PairNormalizationTests(unittest.TestCase):
    def test_diameter_types_are_strict(self):
        for invalid in (True, 4.0):
            with self.assertRaises(TypeError):
                canonical_diameter_pair(invalid)
            with self.assertRaises(TypeError):
                allowed_centers(invalid)

    def test_canonical_pairs_have_requested_distances(self):
        for diameter in branch_diameters():
            left, right = canonical_diameter_pair(diameter)
            self.assertEqual(left, (0,) * N)
            self.assertEqual(
                right,
                (1,) * diameter + (0,) * (N - diameter),
            )
            self.assertEqual(hamming_distance(left, right), diameter)

    def test_normalization_is_a_bijection_and_preserves_anchor_distances(self):
        words = all_words()
        for diameter in branch_diameters():
            left, right = noncanonical_pair(diameter)
            certificate = normalize_diameter_pair(left, right)
            self.assertEqual(certificate.diameter, diameter)
            self.assertEqual(
                (
                    certificate.isometry.apply(left),
                    certificate.isometry.apply(right),
                ),
                canonical_diameter_pair(diameter),
            )

            images = tuple(certificate.isometry.apply(word) for word in words)
            self.assertEqual(len(set(images)), WORD_COUNT)
            canonical_left, canonical_right = certificate.canonical_pair
            for word, image in zip(words, images):
                self.assertEqual(certificate.isometry.invert(image), word)
                self.assertEqual(
                    hamming_distance(word, left),
                    hamming_distance(image, canonical_left),
                )
                self.assertEqual(
                    hamming_distance(word, right),
                    hamming_distance(image, canonical_right),
                )

    def test_code_normalization_assigns_each_supported_diameter(self):
        for diameter in branch_diameters():
            left, right = noncanonical_pair(diameter)
            forward = normalize_code_on_diameter_pair((left, right))
            reverse = normalize_code_on_diameter_pair((right, left))
            self.assertEqual(forward.diameter, diameter)
            self.assertEqual(forward.centers, canonical_diameter_pair(diameter))
            self.assertEqual(reverse.centers, forward.centers)
            self.assertTrue(
                diameter_branch(diameter).code_is_admissible(forward.centers)
            )


class AllowedCenterTests(unittest.TestCase):
    def test_allowed_centers_are_complete_and_deterministic(self):
        words = all_words()
        self.assertEqual(
            tuple(branch.diameter for branch in diameter_branches()),
            branch_diameters(),
        )
        for diameter, expected_count in EXPECTED_ALLOWED_COUNTS.items():
            left, right = canonical_diameter_pair(diameter)
            independently_filtered = tuple(
                center
                for center in words
                if hamming_distance(center, left) <= diameter
                and hamming_distance(center, right) <= diameter
            )
            generated = allowed_centers(diameter)
            self.assertEqual(generated, independently_filtered)
            self.assertEqual(len(generated), expected_count)
            self.assertEqual(len(set(generated)), expected_count)
            self.assertEqual(generated, tuple(sorted(generated)))
            self.assertIn(left, generated)
            self.assertIn(right, generated)

    def test_anchor_filter_does_not_replace_pairwise_constraints(self):
        branch = diameter_branch(4)
        incompatible_pair = next(
            (left, right)
            for left, right in combinations(branch.allowed_centers, 2)
            if hamming_distance(left, right) > branch.diameter
        )
        self.assertTrue(
            all(branch.center_is_allowed(center) for center in incompatible_pair)
        )
        self.assertFalse(
            branch.code_is_admissible(branch.anchors + incompatible_pair)
        )
        self.assertTrue(branch.code_is_admissible(branch.anchors))


class BranchGeneratorTests(unittest.TestCase):
    def test_cli_json_is_deterministic_and_complete(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        command = [
            sys.executable,
            str(ROOT / "tools" / "generate_branches.py"),
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
        self.assertEqual(
            payload["coverage_argument"]["covered_diameters"],
            list(branch_diameters()),
        )
        self.assertEqual(
            payload["coverage_argument"]["diameter_lower_bound"],
            N - RADIUS,
        )
        self.assertEqual(len(payload["branches"]), 4)
        for record in payload["branches"]:
            diameter = record["diameter"]
            self.assertEqual(
                record["allowed_center_count"],
                EXPECTED_ALLOWED_COUNTS[diameter],
            )
            self.assertEqual(
                record["allowed_centers"],
                [
                    format_word(center)
                    for center in allowed_centers(diameter)
                ],
            )
            self.assertEqual(
                record["anchors"],
                [
                    format_word(anchor)
                    for anchor in canonical_diameter_pair(diameter)
                ],
            )
            self.assertTrue(
                record["selected_center_constraints"]["anchors_required"]
            )
            self.assertEqual(
                record["selected_center_constraints"][
                    "maximum_pairwise_distance"
                ],
                diameter,
            )


if __name__ == "__main__":
    unittest.main()
