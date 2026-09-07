# Seven-Word Subcore Exclusions and a Six-Hole Plateau in the Ternary Covering Problem `K_3(7,3)`

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22452732.svg)](https://doi.org/10.5281/zenodo.22452732)

## Project Overview

This repository gives reproducible structural exclusions and exact finite
classifications for the unresolved ternary covering number `K_3(7,3)`. Its
principal result excludes eight explicit seven-word subcores, together with
every isometric copy, from every radius-3 covering code of size at most 11.

| Field | Value |
| --- | --- |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Field | Coding theory, finite geometry, and extremal combinatorics |
| Problem | Determine the ternary covering number `K_3(7,3)` |
| Current result | Eight explicit seven-word subcores and every isometric copy are excluded from all size-at-most-11 covers |
| Result type | Complete scoped forbidden-subcore theorem and exact local classification |
| Release | `v0.2.1` |
| Version DOI | [`10.5281/zenodo.22647770`](https://doi.org/10.5281/zenodo.22647770) |
| Concept DOI | [`10.5281/zenodo.22452732`](https://doi.org/10.5281/zenodo.22452732) |
| License | MIT for project-original material |

## Problem And Background

For a code `D` in the ternary Hamming space `{0,1,2}^7`, its covering radius
is

```text
max_x min_d d_H(x,d),
```

where `d_H` is Hamming distance. The number `K_3(7,3)` is the smallest
cardinality of a code with covering radius at most 3.

The ambient space contains `3^7 = 2,187` words. Every radius-3 Hamming ball
contains 379 words. The global interval is

```text
11 <= K_3(7,3) <= 12.
```

Covering codes ask how sparsely centers can be placed while every ambient
word remains close to at least one center. They connect coding theory,
extremal combinatorics, dominating sets, finite geometry, and exact
optimization.

The `K_3(7,3)` case appeared in published ternary covering-code tables and
the construction literature cited below. Its recorded historical bounds and
dated updates are summarized in the next section.

## Starting Frontier And Longstanding Gap

Gabor Keri's covering-code table records the interval `11..12`. The upper
bound 12 is associated with work of Hamalainen and Rankinen from 1991. The
table change log records the computer-proved lower bound 11 on 2008-10-22.
The one-unit gap had therefore remained open for nearly eighteen years as of
the 2026-09-06 audit.

| Starting item | Status |
| --- | --- |
| Ambient words | 2,187 |
| Radius-3 ball size | 379 |
| Published lower bound | 11 |
| Published upper bound | 12 |
| Exact value | Open |
| Recorded gap | 1 |

This repository starts from the recorded interval. It independently
reconstructs a 12-word cover but does not claim a new global bound or an
independent proof of the historical lower bound.

## Main Result

The project-original contribution is a scoped structural exclusion built on
an independently reconstructed prior 12-word upper-bound construction.

Define the eight-word set

```text
C0 = {
  0000011, 0000102, 0000220, 0002121,
  1111022, 1111110, 1111201, 2222000
}.
```

For each `c` in `C0`, let `S_c = C0 \ {c}`.

> For every `c` in `C0` and every set `T` of at most four ternary
> length-7 words, `S_c union T` leaves at least six ambient words at
> distance greater than 3. Equality is attained.

Consequently, no radius-3 covering code of size at most 11 contains any
`S_c` or an isometric copy of any `S_c`.

The order-18 stabilizer of `C0` partitions its eight deletions into four
orbits. One representative from each orbit was checked exactly:

| Deleted word | Orbit size | Holes of seven-word core | Pair threshold | Eligible first pairs | Minimum residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `0000011` | 3 | 370 | 183 | 86,319 | 6 |
| `0002121` | 1 | 358 | 177 | 81,290 | 6 |
| `1111022` | 3 | 396 | 196 | 82,464 | 6 |
| `2222000` | 1 | 518 | 257 | 97,292 | 6 |

Each case has 2,180 allowed added centers and 2,375,110 unordered center
pairs. Across the four representatives, the verifiers build 9,500,440 pair
entries and query 347,365 eligible first pairs.

For every representative, adding the deleted word and

```text
1112212
2220121
2221212
```

attains the minimum and leaves exactly

```text
0011000
0101000
0110000
1001000
1010000
1100000
```

uncovered.

Three additional exact results accompany the primary theorem:

1. The full core `C0` leaves 253 holes. Every set of at most three added
   centers leaves at least six holes. Exactly eight unordered triples attain
   six, in four stabilizer classes.
2. Four retained size-11 near-covers are pairwise non-isometric, share `C0`
   after normalization, and leave the same six holes. Exact strict
   replacement analysis finds no one-center or two-center improvement below
   six holes within those four classes.
3. Every radius-3 ternary length-7 cover of diameter at most 4 has at least
   17 centers. Every cover with at most 16 centers therefore has diameter 5,
   6, or 7.

## Method And Proof Architecture

### Exact Pair Reduction

Suppose four added centers cover all but at most five holes of a seven-word
core. Every covered hole belongs to at least three of the six unordered
center-pair unions. Some pair must therefore cover at least

```text
ceil((hole_count - 5) / 2)
```

holes.

The verifiers enumerate every pair meeting this threshold and query every
possible complementary pair. This is an exact reduction of the four-center
decision problem, not a heuristic search. Results for fewer than four added
centers follow by padding with additional distinct centers, because adding a
center cannot increase the uncovered set.

### Independent Primary Verifiers

Two separately implemented exhaustive programs establish the primary result:

1. `search/src/bin/seven_core_direct.rs` uses an exact pair-union tree,
   permits overlapping pair witnesses, and safely pads any witness to four
   distinct centers.
2. `src/seven_core_independent.cpp` independently reconstructs the Hamming
   geometry and core stabilizer, uses a different pair-tree layout, and
   requires the queried pairs to be disjoint.

Both implementations reproduce the exclusion result, orbit sizes, hole
counts, thresholds, eligible-pair counts, drift checks, and residual minima.
Their synthetic controls compare the optimized reductions with direct
four-set enumeration. CI captures both verifier outputs and compares every
published count and witness with `evidence/seven-core-results.json`.

### Core Completion, Plateau, And Diameter Arguments

The Python exact-mask implementation and a direct Rust scan independently
check all

```text
binom(2179,3) = 1,721,956,929
```

candidate triples for the full-core completion theorem and recover the same
eight minimizers.

The strict replacement analysis checks 520,608,000 raw two-center candidates,
finds 30 plateau-preserving neighbor incidences, and finds no one-center or
two-center improvement below six holes in the four retained near-cover
classes.

The diameter theorem counts coverage of the 128 full-support words
`{1,2}^7`, giving the lower bound of 17 centers for diameter-at-most-4
covers.

## Verification And Evidence

Independent Rust and C++20 exhaustive verifiers check the primary theorem.
Python and Rust checks cover the full-core theorem, deterministic manifests
bind retained evidence, and CI replays the release targets.

The explicit residual-six equality witness is supplied to both primary
verifiers and checked directly rather than discovered independently by each
implementation. The primary theorem replay is CPU-only. Rebuilding the
pair-union tables is the high-resource step; retained outputs support a
lighter manifest and equality-witness audit.

The evidence map is:

- `docs/SEVEN_WORD_SUBCORE_THEOREM.md` states and proves the primary scoped
  theorem.
- `docs/FIXED_CORE_THEOREM.md` records the exact eight-word completion
  theorem.
- `search/src/bin/seven_core_direct.rs` is the Rust exhaustive verifier.
- `src/seven_core_independent.cpp` is the independent C++20 verifier.
- `evidence/seven-core-results.json` records the exact release counts.
- `tools/verify_seven_core_outputs.py` binds fresh Rust and C++20 outputs to
  the checked result record.
- `data/search/plateau_classes.json` binds the retained near-cover inputs and
  exact plateau outputs.
- `research/EXPERIMENT_LOG.md` records searches, exact computations, and
  negative results.
- `docs/CLAIMS.md` separates established results from nonclaims.
- `docs/PRIOR_ART.md` records the dated literature and novelty audit.
- `paper/main.tex` is the technical report source for the released theorem.

## Reproduction

Verify the retained 12-word cover and run the standard checks:

```bash
make verify
make test
make test-search
make lint-search
```

Build and verify the paper-inclusive release assets with Tectonic 0.16.9:

```bash
make archival-release
```

The Makefile fixes `SOURCE_DATE_EPOCH` to the release date so repeated clean
builds produce the same PDF bytes.

Replay the primary theorem with one worker and in parallel:

```bash
make seven-core-direct-single
make seven-core-direct
make seven-core-independent-self-test
make seven-core-independent
```

Replay the eight-word theorem and the six-hole plateau:

```bash
make core-direct-single
make core-direct
make plateau
```

Run the complete result target:

```bash
make verify-result
```

Verify the release checksum manifest:

```bash
make verify-release-manifest
```

In a Git checkout, manifest verification binds every listed hash to the Git
index. In a GitHub or Zenodo source archive without `.git`, the same command
verifies every listed file hash. The explicit file-only form is:

```bash
python3 tools/verify_checksum_manifest.py --listed-only
```

The optional fixed-core CNF can be generated with:

```bash
make core-cnf
```

No UNSAT status for its residual-at-most-5 instance is part of the release
claim.

## Claims

The repository establishes the following scoped results:

- Eight seven-word subcores and every isometric copy are rigorously excluded
  from every radius-3 cover of size at most 11.
- The four-center minimum residual is exactly six for all eight subcores.
- The three-center completion problem is solved exactly for `C0`.
- Four recurrent six-hole near-cover classes and their strict one-center and
  two-center neighborhoods are classified exactly.
- Every diameter-at-most-4 radius-3 cover has at least 17 centers.
- A reconstructed 12-word cover verifies the recorded upper endpoint.

The subcore theorem and local classifications are complete within their
stated families. The exact value of `K_3(7,3)` remains open.

The next mathematical acceptance gate is either a fully checked exclusion of
at least one complete named diameter-5, diameter-6, or diameter-7 branch
after applying the eight subcore exclusions, or exhaustive verification of
an 11-word cover. Search timeouts and incomplete branch scans do not satisfy
this gate.

## Limitations And Nonclaims

- No 11-word covering code has been found.
- Nonexistence of all 11-word covering codes has not been proved.
- The global lower or upper bound has not changed.
- The historical lower bound 11 has not been independently certified here.
- The eight excluded subcores are not claimed to occur in every hypothetical
  11-word cover.
- The four near-cover classes do not classify all six-hole near-covers.
- No residual-at-most-5 SAT UNSAT result or checked SAT proof is claimed.
- No compact proof certificate independent of the two primary verifier
  implementations is supplied.
- Incomplete searches and solver timeouts are not used as evidence.
- No practical communications-performance improvement is claimed.
- No external mathematical review is claimed.

## Significance And Use

The theorem converts recurrent near-cover structure into certified forbidden
substructures. A complete classification or proof-producing search for an
11-word cover may discard a candidate as soon as it contains one of the eight
subcores up to Hamming-space isometry.

The repository can also be used to:

- benchmark exact covering, domination, SAT, and branch-and-bound methods;
- test symmetry and meet-in-the-middle implementations against fixed counts;
- study the geometry and connectivity of near-optimal covering codes; and
- extend a library of certified forbidden substructures for `K_3(7,3)`.

## Remaining Work And Future Directions

The exact value remains open. The next route is to apply the certified
subcore exclusions inside complete diameter-5, diameter-6, and diameter-7
branches.

1. Apply the seven-word exclusions inside the exact diameter 5, 6, and 7
   branches.
2. Discover and certify additional forbidden subcores.
3. Classify candidate 11-word structures globally under Hamming-space
   isometry.
4. Independently certify the historical lower bound `K_3(7,3) >= 11`.
5. Continue construction search for an 11-word cover.
6. Produce a complete checked exclusion of all 11-word codes if the
   construction route fails.

## Repository Layout

- `docs/SEVEN_WORD_SUBCORE_THEOREM.md` contains the primary theorem.
- `docs/FIXED_CORE_THEOREM.md` contains the full-core completion theorem.
- `search/` contains the Rust exact-search implementation.
- `src/seven_core_independent.cpp` contains the independent C++20 verifier.
- `evidence/seven-core-results.json` contains the primary release counts.
- `data/search/plateau_classes.json` contains the retained plateau inputs and
  outputs.
- `research/EXPERIMENT_LOG.md` records exact computations and searches.
- `docs/CLAIMS.md` and `docs/PRIOR_ART.md` document claim scope and prior art.
- `paper/main.tex` is the released technical report source.
- `dist/release/` contains the versioned compiled PDF, paper-source archive,
  and `SHA256SUMS` for the paper-inclusive archival release.
- `CITATION.cff` contains citation metadata.
- `RELEASE_NOTES.md` records release history.

## Publication Citation And Archive

The public repository is
[`ruturajr-raval/ternary-covering-code-7-3`](https://github.com/ruturajr-raval/ternary-covering-code-7-3).
The paper-inclusive archival release is
[`v0.2.1`](https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.1).
Its release commit is
`3f1f1baf1f9a18944deaed555a241b90f683b7ec`.

The exact archival patch is identified by version DOI
[`10.5281/zenodo.22647770`](https://doi.org/10.5281/zenodo.22647770).
All repository versions are collected under concept DOI
[`10.5281/zenodo.22452732`](https://doi.org/10.5281/zenodo.22452732).

Release `v0.2.1` is an archival and documentation patch. It adds an
explicitly named compiled PDF, a deterministic paper-source archive, and a
checksum file suitable for GitHub and Zenodo. The theorem, proof,
certificates, retained data, and computations are unchanged from `v0.2.0`.
All three assets were downloaded from both public services and verified
against the release checksum file.

The technical report source is [`paper/main.tex`](paper/main.tex). GitHub and
Zenodo are the current dissemination baseline. No preprint-server deposit or
external mathematical review is claimed. Cite the exact `v0.2.1` result with
the version DOI. Citation metadata is in `CITATION.cff`, and release history
is in `RELEASE_NOTES.md`.

## Authorship

Ruturaj R Raval<br>
Independent Researcher<br>
ORCID: [`0000-0003-4930-8981`](https://orcid.org/0000-0003-4930-8981)

## Licensing And Provenance

Project-original software and documentation are released under the MIT
License. Historical papers, tables, and construction files are cited but not
redistributed.

The 12-word baseline was reconstructed independently and is not claimed as a
new construction. The residual-six equality witnesses were supplied to both
primary verifiers and checked directly rather than independently discovered
by each implementation.

## References

- Gabor Keri, [Tables for Bounds on Covering
  Codes](https://old.sztaki.hu/~keri/codes/), ternary table and update log.
- H. Hamalainen and S. Rankinen, [Upper Bounds for Football Pool Problems
  and Mixed Covering Codes](https://doi.org/10.1016/0097-3165(91)90024-B),
  *Journal of Combinatorial Theory, Series A* 56 (1991), 84-95.
- P. R. J. Ostergard and H. O. Hamalainen, [A New Table of Binary/Ternary
  Mixed Covering Codes](https://doi.org/10.1023/A:1008228721072),
  *Designs, Codes and Cryptography* 11 (1997), 151-178.
- D. Gijswijt and S. Polak, [Semidefinite lower bounds for covering
  codes](https://arxiv.org/abs/2504.01932), arXiv:2504.01932v2, 2026.
