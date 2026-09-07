import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = (
    "Seven-Word Subcore Exclusions and a Six-Hole Plateau in the "
    "Ternary Covering Problem K_3(7,3)"
)
VERSION = "0.2.1"
VERSION_DOI = "10.5281/zenodo.22647770"
ORCID = "0000-0003-4930-8981"


class PublicationMetadataTests(unittest.TestCase):
    def test_title_version_and_author_are_consistent(self):
        zenodo = json.loads(
            (ROOT / ".zenodo.json").read_text(encoding="ascii")
        )
        cff = (ROOT / "CITATION.cff").read_text(encoding="ascii")
        metadata = (ROOT / "paper" / "ARXIV_METADATA.md").read_text(
            encoding="ascii"
        )
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="ascii")
        cargo = (ROOT / "search" / "Cargo.toml").read_text(encoding="ascii")

        self.assertEqual(zenodo["title"], TITLE)
        self.assertIn(f'title: "{TITLE}"', cff)
        self.assertIn(TITLE, metadata)
        self.assertEqual(zenodo["version"], VERSION)
        self.assertIn(f"version: {VERSION}", cff)
        self.assertIn(VERSION_DOI, cff)
        self.assertIn(VERSION_DOI, metadata)
        self.assertRegex(
            pyproject,
            rf'(?m)^version = "{re.escape(VERSION)}"$',
        )
        self.assertRegex(
            cargo,
            rf'(?m)^version = "{re.escape(VERSION)}"$',
        )
        self.assertEqual(zenodo["creators"][0]["orcid"], ORCID)
        self.assertIn(ORCID, cff)
        self.assertIn(ORCID, metadata)

    def test_primary_counts_are_consistent(self):
        evidence = json.loads(
            (ROOT / "evidence" / "seven-core-results.json").read_text(
                encoding="ascii"
            )
        )
        publication_text = "\n".join(
            (ROOT / path).read_text(encoding="ascii")
            for path in (
                "README.md",
                "docs/CLAIMS.md",
                "paper/main.tex",
                "paper/ARXIV_METADATA.md",
                ".zenodo.json",
                "CITATION.cff",
            )
        )
        pair_entries = f'{evidence["totals"]["pair_entries_built"]:,}'
        eligible_pairs = (
            f'{evidence["totals"]["eligible_first_pairs_queried"]:,}'
        )
        self.assertGreaterEqual(publication_text.count(pair_entries), 4)
        self.assertGreaterEqual(publication_text.count(eligible_pairs), 4)

    def test_archival_patch_verification_state_is_honest(self):
        release = json.loads(
            (ROOT / "release.json").read_text(encoding="ascii")
        )
        report = release["technical_report"]
        verification = release["verification"]
        self.assertIn("previous_v0_2_0_ci", report)
        self.assertTrue(
            verification["local_index_manifest_replay_passes"]
        )
        self.assertFalse(
            verification["published_v0_2_1_archive_replay_passes"]
        )

    def test_publication_files_have_no_local_or_visibility_traces(self):
        paths = (
            "README.md",
            "CITATION.cff",
            ".zenodo.json",
            "release.json",
            "docs/CLAIMS.md",
            "docs/PRIOR_ART.md",
            "docs/RESEARCH_PLAN.md",
            "docs/SEVEN_WORD_SUBCORE_THEOREM.md",
            "docs/FIXED_CORE_THEOREM.md",
            "paper/main.tex",
            "paper/ARXIV_METADATA.md",
            "paper/README.md",
            "research/claim.yaml",
        )
        forbidden = (
            "\u2014",
            "/" + "Users" + "/",
            "ruturajr" + "-innovation",
            "research" + "-workbench",
            "private " + "repository",
            "private " + "repo",
            "private" + "_",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{relative}: {token}")


if __name__ == "__main__":
    unittest.main()
