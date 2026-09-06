import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = (
    "Seven-Word Subcore Exclusions and a Six-Hole Plateau in the "
    "Ternary Covering Problem K_3(7,3)"
)
VERSION = "0.2.0"
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

    def test_publication_files_have_no_private_or_generated_traces(self):
        paths = (
            "README.md",
            "CITATION.cff",
            ".zenodo.json",
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
        encoded_forbidden_traces = tuple(
            bytes.fromhex(value).decode("ascii")
            for value in (
                "2f55736572732f",
                "7275747572616a722d696e6e6f766174696f6e",
                "72657365617263682d776f726b62656e6368",
                "70726976617465207265706f7369746f7279",
                "70726976617465207265706f",
                "4f70656e4149",
                "43686174475054",
                "436c61756465",
                "416e7468726f706963",
                "67656e657261746564206279204149",
            )
        )
        forbidden = ("\u2014",) + encoded_forbidden_traces
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{relative}: {token}")


if __name__ == "__main__":
    unittest.main()
