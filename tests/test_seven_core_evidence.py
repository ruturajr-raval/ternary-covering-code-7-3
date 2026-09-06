import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evidence" / "seven-core-results.json"


class SevenCoreEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(RESULTS.read_text(encoding="ascii"))

    def test_geometry_and_claim_scope(self):
        self.assertEqual(self.report["space"]["ambient_words"], 3**7)
        self.assertEqual(self.report["space"]["ball_size"], 379)
        self.assertEqual(self.report["theorem"]["fixed_subcore_size"], 7)
        self.assertEqual(self.report["theorem"]["maximum_added_centers"], 4)
        self.assertEqual(self.report["theorem"]["minimum_residual"], 6)
        self.assertFalse(self.report["theorem"]["global_bound_improved"])

    def test_orbits_cover_all_deletions(self):
        representatives = self.report["representatives"]
        orbit_sizes = [
            len(representative["orbit_members"])
            for representative in representatives
        ]
        self.assertEqual(orbit_sizes, [3, 1, 3, 1])
        members = {
            member
            for representative in representatives
            for member in representative["orbit_members"]
        }
        self.assertEqual(members, set(self.report["core"]))
        self.assertEqual(sum(orbit_sizes), 8)

    def test_pair_counts_and_thresholds(self):
        representatives = self.report["representatives"]
        for representative in representatives:
            candidate_count = representative["candidate_centers"]
            self.assertEqual(candidate_count, 2180)
            self.assertEqual(
                representative["unordered_candidate_pairs"],
                candidate_count * (candidate_count - 1) // 2,
            )
            self.assertEqual(
                representative["first_pair_threshold"],
                (representative["initial_holes"] - 5 + 1) // 2,
            )
            self.assertEqual(representative["minimum_residual"], 6)

        self.assertEqual(
            sum(
                representative["unordered_candidate_pairs"]
                for representative in representatives
            ),
            self.report["totals"]["pair_entries_built"],
        )
        self.assertEqual(
            sum(
                representative["eligible_first_pairs"]
                for representative in representatives
            ),
            self.report["totals"]["eligible_first_pairs_queried"],
        )

    def test_witnesses_have_expected_shape(self):
        expected_holes = self.report["witness_holes"]
        self.assertEqual(len(expected_holes), 6)
        self.assertEqual(len(set(expected_holes)), 6)
        for representative in self.report["representatives"]:
            additions = representative["witness_additions"]
            self.assertEqual(len(additions), 4)
            self.assertEqual(len(set(additions)), 4)
            self.assertEqual(additions[0], representative["deleted_word"])


if __name__ == "__main__":
    unittest.main()
