# Release v0.2.0

## Release Identity

| Field | Value |
| --- | --- |
| Title | Seven-Word Subcore Exclusions and a Six-Hole Plateau in the Ternary Covering Problem K_3(7,3) |
| Tagged release | [`v0.2.0`](https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.0) |
| Release date | 2026-09-06 |
| Audited release commit | `e9fbec7c28e0e6a386953f0e0f242582de7802bb` |
| Version DOI | [`10.5281/zenodo.22452733`](https://doi.org/10.5281/zenodo.22452733) |
| Concept DOI | [`10.5281/zenodo.22452732`](https://doi.org/10.5281/zenodo.22452732) |
| Archive status | Published Zenodo snapshot with archive-mode manifest replay |
| License | MIT for project-original material |

## Background

The ternary covering number `K_3(7,3)` asks for the minimum number of
length-7 ternary words whose radius-3 Hamming balls cover all 2,187 ambient
words. The established interval remains

```text
11 <= K_3(7,3) <= 12.
```

An 11-word cover would determine the value at 11. A complete checked
exclusion of every 11-word cover, together with the verified 12-word
construction, would determine it at 12.

## What This Release Adds

This release proves a complete scoped structural exclusion for eight
seven-word subcores obtained from an explicit eight-word core `C0`.

For every one of those subcores, every set of at most four added centers
leaves at least six radius-3 holes, and equality is attained. Consequently,
no covering code of size at most 11 contains any of the eight subcores or an
isometric copy.

Independent Rust and C++20 verifiers reduce the eight deletions to four
stabilizer orbits and reproduce the exact counts:

```text
9,500,440 pair entries
347,365 eligible first-pair queries
minimum residual 6 in every deletion orbit
```

The release also establishes:

- an exact residual-six three-center minimum for the full eight-word core;
- exactly eight minimizing triples in four stabilizer classes;
- an exact strict replacement plateau for four specified six-hole near-cover
  classes, representing 520,608,000 raw two-center candidates; and
- a direct proof that every diameter-at-most-4 cover requires at least 17
  centers.

## What Is Not Claimed

- No 11-word covering code has been found.
- Nonexistence of all 11-word covering codes has not been proved.
- The global interval `11 <= K_3(7,3) <= 12` is unchanged.
- The historical lower bound 11 is not independently certified here.
- The excluded subcores are not claimed to occur in every hypothetical
  11-word cover.
- The four near-cover classes are not a classification of all six-hole
  near-covers.
- No residual-at-most-5 SAT UNSAT result or checked SAT proof is claimed.
- No external mathematical review is claimed.

## Reproduction

The central result can be replayed with:

```bash
make verify-result
```

The release also provides:

- an exact staged checksum manifest;
- deterministic manuscript source bundling;
- independent Rust and C++20 theorem verifiers;
- Python and Rust full-core verifiers;
- mutation and exhaustive small-universe controls; and
- clean GitHub Actions runs on the release commit and protected tag.

Tracked release files are bound by `release-manifest.sha256`. Exact theorem
counts are recorded in `evidence/seven-core-results.json`, and
`tools/verify_seven_core_outputs.py` compares fresh Rust and C++20 outputs
against that record. The release record confirms that archive-mode manifest
replay passes.

## Release And Archive

- Public repository:
  `https://github.com/ruturajr-raval/ternary-covering-code-7-3`
- GitHub release:
  `https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.0`
- Version DOI: `10.5281/zenodo.22452733`
- Stable concept DOI: `10.5281/zenodo.22452732`
- Release commit:
  `e9fbec7c28e0e6a386953f0e0f242582de7802bb`

Release assets:

```text
main.pdf
SHA-256 35972a51795a10b5f4e2856a2ea770c46e2bfafbd392b710f8a71118194a69b8

ternary-covering-code-7-3-source.tar.gz
SHA-256 7e45f66c0eec4958e9ff2c6130a06df65ee339653c0d4bc9868782b6a16a8b99
```

The Zenodo repository snapshot is
`ruturajr-raval/ternary-covering-code-7-3-v0.2.0.zip`, with SHA-256
`6cea2392f585cb91f7a8d30a6934755e5da5c0244056938f3d48e1bc1501e2d0`.
The release record marks `v0.2.0` as released, records active update and
deletion protection for version tags, and confirms archive-mode manifest
replay.

## Provenance Boundary

Project-original code, evidence records, and documentation are MIT licensed.
The historical tables and papers are cited rather than redistributed, and the
12-word baseline was reconstructed independently. The residual-six equality
witnesses were supplied to both primary verifiers and checked directly rather
than discovered independently by each implementation.

## Review Status

The release passed claim-scope, implementation, reproducibility, manuscript,
and release-metadata review. Clean CI completed on the release commit and
protected tag, and all 10 pages of the hosted PDF were reviewed. No external
mathematical or peer review is claimed.

## Significance

The result converts a recurrent near-cover pattern into exact forbidden
substructures. Exact-cover, SAT, and branch-and-bound searches may reject a
candidate as soon as one of the excluded subcores appears up to Hamming-space
isometry.

The pair-averaging reduction, independent finite verifiers, fixed count
records, and local plateau classification also provide reusable regression
benchmarks for covering, domination, and finite-set completion algorithms.

## Remaining Work And Next Acceptance Gate

A final solution still requires either a verified 11-word construction or a
complete checked exclusion of every 11-word code. The immediate routes are to
certify more forbidden subcores, incorporate all exclusions into the diameter
5, 6, and 7 branches, classify global 11-word structures, and independently
reconstruct the historical lower bound.

The next mathematical acceptance gate is either a fully checked exclusion of
at least one complete named diameter-5, diameter-6, or diameter-7 branch after
applying the eight subcore exclusions, or exhaustive verification of an
11-word cover.

## Public Summary

Release `v0.2.0` proves that eight explicit seven-word subcores, together with
every isometric copy, cannot occur in any radius-3 ternary length-7 covering
code of size at most 11. Independent Rust and C++20 exhaustive verifiers check
the complete scoped theorem. The global interval
`11 <= K_3(7,3) <= 12` remains unchanged.

## Citation

Citation metadata is in `CITATION.cff`. Cite the archived `v0.2.0` result
using version DOI `10.5281/zenodo.22452733`.
Historical release scope is summarized in `RELEASE_NOTES.md`.
