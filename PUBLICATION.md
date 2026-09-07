# Release v0.2.1

## Release Identity

| Field | Value |
| --- | --- |
| Title | Seven-Word Subcore Exclusions and a Six-Hole Plateau in the Ternary Covering Problem K_3(7,3) |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Tagged release | [`v0.2.1`](https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.1) |
| Release date | 2026-09-07 |
| Audited release commit | `3f1f1baf1f9a18944deaed555a241b90f683b7ec` |
| Archive status | GitHub release and paper-inclusive Zenodo version published; all three public assets downloaded and verified |
| Underlying mathematical release | `v0.2.0` at commit `e9fbec7c28e0e6a386953f0e0f242582de7802bb` |
| Version DOI | [`10.5281/zenodo.22647770`](https://doi.org/10.5281/zenodo.22647770) |
| Concept DOI | [`10.5281/zenodo.22452732`](https://doi.org/10.5281/zenodo.22452732) |
| Patch scope | Paper-inclusive archival and documentation patch |
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

This release carries forward the complete scoped structural exclusion for
eight seven-word subcores obtained from an explicit eight-word core `C0`.

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

Version `v0.2.1` adds an explicitly named compiled PDF, deterministic
paper-source archive, and `SHA256SUMS`. It is an archival and documentation
patch. The theorem, proof, certificates, retained data, exact counts, and
computations are unchanged from `v0.2.0`.

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

Build and verify the paper-inclusive archival assets with:

```bash
make archival-release
```

The paper build uses Tectonic 0.16.9 and a fixed `SOURCE_DATE_EPOCH`.
Independent clean builds must reproduce the archived PDF hash.

The release also provides:

- an exact staged checksum manifest;
- deterministic manuscript source bundling;
- independent Rust and C++20 theorem verifiers;
- Python and Rust full-core verifiers;
- mutation and exhaustive small-universe controls; and
- clean GitHub Actions runs for the prior `v0.2.0` release and protected tag.

Tracked release files are bound by `release-manifest.sha256`. Exact theorem
counts are recorded in `evidence/seven-core-results.json`, and
`tools/verify_seven_core_outputs.py` compares fresh Rust and C++20 outputs
against that record. Local `v0.2.1` index-bound manifest verification and
source-archive PDF replay pass. Candidate CI `34149337316`, public
main CI `34150876791`, and public tag CI `34150877158` passed. The GitHub and
Zenodo release assets were downloaded independently and verified against
`SHA256SUMS`.

## Release And Archive

- Public repository:
  `https://github.com/ruturajr-raval/ternary-covering-code-7-3`
- GitHub release:
  `https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.1`
- Version DOI: `10.5281/zenodo.22647770`
- Stable concept DOI: `10.5281/zenodo.22452732`

Release assets:

```text
ternary-covering-code-7-3-v0.2.1-paper.pdf
SHA-256 721139ca75410342aa7a74f6680873047f618353c939dfbb9010a57457722ba5

ternary-covering-code-7-3-v0.2.1-paper-source.tar.gz
SHA-256 e5062ed74e255481cc0edbb37c2d7f63202c6f033d2df0b6274e69d374d882f7

SHA256SUMS
SHA-256 f0e01bc27a8caec9fc1d13dbbd75b462a18b1d0d34f0cc150830aa76e2656aa1
```

The preceding v0.2.0 Zenodo repository snapshot is
`ruturajr-raval/ternary-covering-code-7-3-v0.2.0.zip`, with SHA-256
`6cea2392f585cb91f7a8d30a6934755e5da5c0244056938f3d48e1bc1501e2d0`.
The current release record binds the published v0.2.1 paper assets and
preserves the prior snapshot identity for provenance.

## Provenance Boundary

Project-original code, evidence records, and documentation are MIT licensed.
The historical tables and papers are cited rather than redistributed, and the
12-word baseline was reconstructed independently. The residual-six equality
witnesses were supplied to both primary verifiers and checked directly rather
than discovered independently by each implementation.

## Review Status

The underlying scoped theorem passed claim-scope, implementation,
reproducibility, manuscript, and release-metadata review in `v0.2.0`. The
v0.2.1 archival patch passed separate paper-build, source-bundle, checksum,
hosted-CI, and public-download gates. No external mathematical or peer review
is claimed.

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

Release `v0.2.1` records that eight explicit seven-word subcores, together with
every isometric copy, cannot occur in any radius-3 ternary length-7 covering
code of size at most 11. Independent Rust and C++20 exhaustive verifiers check
the complete scoped theorem. The global interval
`11 <= K_3(7,3) <= 12` remains unchanged.

## Citation

Citation metadata is in `CITATION.cff`. Cite the paper-inclusive `v0.2.1`
result using version DOI `10.5281/zenodo.22647770`.
Historical release scope is summarized in `RELEASE_NOTES.md`.
