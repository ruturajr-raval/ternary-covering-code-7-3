# arXiv Submission Metadata

## Title

Seven-Word Subcore Exclusions and a Six-Hole Plateau in the Ternary Covering Problem K_3(7,3)

## Author

Ruturaj R Raval

Affiliation: Independent Researcher

ORCID: 0000-0003-4930-8981

## Abstract

Let K_3(7,3) be the minimum cardinality of a radius-three covering code in the ternary Hamming space {0,1,2}^7. The established global interval remains 11 <= K_3(7,3) <= 12. This report proves scoped structural exclusions based on an explicit eight-word core C. For each c in C, every set of at most four centers added to the seven-word subcore C without c leaves at least six words uncovered, and equality is attained. Consequently, no covering code of size at most eleven contains any of these eight subcores or an isometric copy. The order-18 stabilizer of C reduces the eight deletions to four representatives. Independent Rust and C++20 verifiers solve all four completion problems by exact pair reduction, building 9,500,440 pair entries and querying 347,365 eligible first pairs. The full eight-word core is also classified exactly: its three-center minimum is six, attained by eight triples in four stabilizer classes. Exact local replacement results and a direct diameter bound provide further structural constraints. The global interval is unchanged.

## Categories

Primary: math.CO

Cross-list: cs.IT

## Comments

Contains a seven-word subcore exclusion theorem, an exact eight-word core completion classification, a direct diameter bound, exact finite replacement-neighborhood results, independent Rust and C++20 primary verifiers, and complete reproducibility commands. The global interval 11 <= K_3(7,3) <= 12 remains unchanged.

## Keywords

covering codes; ternary codes; Hamming space; exact enumeration; computational combinatorics; finite verification; symmetry reduction; meet-in-the-middle

## License

arXiv.org perpetual, non-exclusive license

## Source Package

Upload the LaTeX source and only the files required to compile it. The paper uses no external bibliography, figures, or generated tables.

## Claim Boundary

- Claimed: exact residual-six four-center minimum for all eight stated seven-word subcores and every isometric copy.
- Claimed: exclusion of those subcores from every size-at-most-eleven cover.
- Claimed: exact residual-six three-center minimum for the full eight-word core.
- Claimed: exactly eight unordered three-center additions attain residual six for the full core.
- Claimed: four stabilizer classes among those optimal triples.
- Claimed: exact strict one-center and two-center replacement results for four specified six-hole near-cover classes.
- Claimed: every radius-three ternary length-seven cover of diameter at most four has at least seventeen centers.
- Not claimed: a new global lower bound, a new global upper bound, an eleven-word cover, or a complete exclusion of eleven-word covers.
- Not claimed: an r=5 CNF unsatisfiability result or checked proof.

## Data And Code

The accompanying source repository contains the independent Rust and C++20 subcore verifiers, the Python and Rust full-core verifiers, retained near-cover data, exact manifests, tests, and replay commands. Cite the versioned repository release together with its archival DOI when those identifiers are assigned.
