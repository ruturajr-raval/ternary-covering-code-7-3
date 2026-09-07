import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.build_paper_bundle import MEMBERS, build_bundle
from tools.build_release_manifest import (
    build_manifest,
    git_index_available,
    index_blob,
    sha256_bytes,
    working_tree_paths,
)
from tools.verify_checksum_manifest import parse_manifest, verify_entries
from tools.verify_seven_core_outputs import (
    parse_key_value_output,
    validate_output,
)


ROOT = Path(__file__).resolve().parents[1]


class PaperBundleTests(unittest.TestCase):
    def test_bundle_is_deterministic_and_allowlisted(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".paper-bundle-test-",
        ) as temporary_directory:
            first = Path(temporary_directory) / "first.tar.gz"
            second = Path(temporary_directory) / "second.tar.gz"
            build_bundle(first)
            build_bundle(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            with tarfile.open(first, mode="r:gz") as archive:
                members = archive.getmembers()
                self.assertEqual(
                    tuple(member.name for member in members),
                    tuple(path.as_posix() for path in MEMBERS),
                )
                for member in members:
                    self.assertTrue(member.isfile())
                    self.assertEqual(member.mode, 0o644)
                    self.assertEqual(member.mtime, 0)
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    extracted = archive.extractfile(member)
                    self.assertIsNotNone(extracted)
                    self.assertEqual(
                        extracted.read(),
                        (ROOT / member.name).read_bytes(),
                    )


class ChecksumManifestTests(unittest.TestCase):
    def test_working_tree_paths_include_untracked_nonignored_file(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            payload = Path(temporary_directory) / "payload.txt"
            payload.write_text("working tree\n", encoding="ascii")
            paths = working_tree_paths(ROOT / "release-manifest.sha256")
            self.assertIn(payload.relative_to(ROOT), paths)

    def test_index_blob_matches_tracked_file(self):
        if not git_index_available():
            self.skipTest("Git index is unavailable in a source archive.")
        payload = index_blob(Path("LICENSE"))
        self.assertEqual(
            sha256_bytes(payload),
            hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest(),
        )

    def test_manifest_builder_is_deterministic(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            directory = Path(temporary_directory)
            first_payload = directory / "first.txt"
            second_payload = directory / "second.txt"
            first_payload.write_text("first\n", encoding="ascii")
            second_payload.write_text("second\n", encoding="ascii")
            relative_paths = (
                first_payload.relative_to(ROOT),
                second_payload.relative_to(ROOT),
            )
            first_manifest = directory / "first.sha256"
            second_manifest = directory / "second.sha256"
            build_manifest(first_manifest, relative_paths)
            build_manifest(second_manifest, relative_paths)
            self.assertEqual(
                first_manifest.read_bytes(),
                second_manifest.read_bytes(),
            )
            self.assertEqual(
                verify_entries(parse_manifest(first_manifest)),
                (),
            )

    def test_manifest_parser_and_verifier(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            directory = Path(temporary_directory)
            payload = directory / "payload.txt"
            payload.write_text("verified\n", encoding="ascii")
            relative = payload.relative_to(ROOT)
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest = directory / "manifest.sha256"
            manifest.write_text(
                f"{digest}  {relative.as_posix()}\n",
                encoding="ascii",
            )
            self.assertEqual(
                verify_entries(parse_manifest(manifest)),
                (),
            )
            payload.write_text("changed\n", encoding="ascii")
            self.assertEqual(len(verify_entries(parse_manifest(manifest))), 1)

    def test_manifest_rejects_parent_paths(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            manifest = Path(temporary_directory) / "manifest.sha256"
            manifest.write_text(
                f"{'0' * 64}  ../outside\n",
                encoding="ascii",
            )
            with self.assertRaises(ValueError):
                parse_manifest(manifest)


class SevenCoreOutputTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads(
            (ROOT / "evidence" / "seven-core-results.json").read_text(
                encoding="ascii"
            )
        )

    def valid_output(self):
        evidence = self.evidence
        lines = [
            f'ambient_words={evidence["space"]["ambient_words"]}',
            f'ball_size={evidence["space"]["ball_size"]}',
            f'core={",".join(evidence["core"])}',
            (
                "core_stabilizer="
                f'{evidence["symmetry"]["core_stabilizer_order"]}'
            ),
            (
                "deletion_orbit_count="
                f'{len(evidence["symmetry"]["deletion_orbit_sizes"])}'
            ),
            "self_tests=passed",
            (
                "self_test_pair_queries="
                f'{evidence["controls"]["cpp20"]["pair_queries"]}'
            ),
            (
                "self_test_four_sets="
                f'{evidence["controls"]["cpp20"]["four_center_sets"]}'
            ),
            (
                "self_test_four_center_minimum="
                f'{evidence["controls"]["cpp20"]["four_center_minimum"]}'
            ),
        ]
        for row in evidence["representatives"]:
            lines.extend(
                (
                    "",
                    f'representative={row["deleted_word"]}',
                    f'orbit_size={len(row["orbit_members"])}',
                    f'orbit_members={",".join(row["orbit_members"])}',
                    f'seven_core_holes={row["initial_holes"]}',
                    f'candidate_centers={row["candidate_centers"]}',
                    (
                        "unordered_candidate_pairs="
                        f'{row["unordered_candidate_pairs"]}'
                    ),
                    f'first_pair_threshold={row["first_pair_threshold"]}',
                    f'eligible_first_pairs={row["eligible_first_pairs"]}',
                    f'queried_first_pairs={row["eligible_first_pairs"]}',
                    (
                        "first_pair_drift_hash_fnv64="
                        f'{row["first_pair_drift_hash_fnv64"]}'
                    ),
                    f'minimum_residual={row["minimum_residual"]}',
                    f'witness_additions={",".join(row["witness_additions"])}',
                    (
                        "witness_holes="
                        f'{",".join(evidence["witness_holes"])}'
                    ),
                    "completion_with_residual_at_most_5=none",
                )
            )
        lines.extend(
            (
                "",
                "VERIFIED CONCLUSION",
                (
                    "representatives_verified="
                    f'{len(evidence["representatives"])}'
                ),
                (
                    "deletions_covered_by_orbits="
                    f'{evidence["symmetry"]["deletions_covered"]}'
                ),
                (
                    "total_pair_entries_built="
                    f'{evidence["totals"]["pair_entries_built"]}'
                ),
                (
                    "total_eligible_first_pairs_queried="
                    f'{evidence["totals"]["eligible_first_pairs_queried"]}'
                ),
                (
                    "all_four_representative_minima="
                    f'{evidence["theorem"]["minimum_residual"]}'
                ),
                (
                    "scope="
                    "the_eight_seven_word_subcores_and_their_isometric_copies"
                ),
            )
        )
        return "\n".join(lines) + "\n"

    def validate_text(self, text):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".seven-core-output-test-",
        ) as temporary_directory:
            output = Path(temporary_directory) / "output.txt"
            output.write_text(text, encoding="ascii")
            return validate_output(output, self.evidence)

    def test_key_value_sections_are_separated(self):
        header, reports, conclusion = parse_key_value_output(
            "\n".join(
                (
                    "ambient_words=2187",
                    "",
                    "representative=0000011",
                    "minimum_residual=6",
                    "",
                    "VERIFIED CONCLUSION",
                    "total_pair_entries_built=9500440",
                )
            )
        )
        self.assertEqual(header, {"ambient_words": "2187"})
        self.assertEqual(
            reports,
            [{"representative": "0000011", "minimum_residual": "6"}],
        )
        self.assertEqual(
            conclusion,
            {"total_pair_entries_built": "9500440"},
        )

    def test_complete_output_is_accepted(self):
        self.assertEqual(self.validate_text(self.valid_output()), ())

    def test_missing_conclusion_is_rejected(self):
        text = self.valid_output().split("VERIFIED CONCLUSION", 1)[0]
        errors = self.validate_text(text)
        self.assertTrue(
            any("conclusion representatives_verified" in error for error in errors)
        )
        self.assertTrue(any("conclusion scope" in error for error in errors))

    def test_queried_pair_count_mismatch_is_rejected(self):
        text = self.valid_output().replace(
            "queried_first_pairs=86319",
            "queried_first_pairs=0",
            1,
        )
        errors = self.validate_text(text)
        self.assertTrue(
            any("queried_first_pairs" in error for error in errors)
        )

    def test_cpp_control_count_mismatch_is_rejected(self):
        text = self.valid_output().replace(
            "self_test_pair_queries=27984",
            "self_test_pair_queries=0",
            1,
        )
        errors = self.validate_text(text)
        self.assertTrue(
            any("C++ self-test pair queries" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
