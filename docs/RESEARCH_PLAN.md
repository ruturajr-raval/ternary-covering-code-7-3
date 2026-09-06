# Research Plan

Status date: 2026-09-06

## Completed Phase 1 - Baseline

- Reconstruct and verify a 12-word radius-3 cover.
- Build direct and generated-ball verifiers.
- Generate a deterministic anchored set-cover CNF.
- Validate the cardinality encoding on exhaustive small cases.
- Reproduce a 12-word cover by independent local search.

## Completed Phase 2 - Near-Cover Frontier

- Run deterministic 11-word construction searches.
- Retain four six-hole near-covers with hashes and exact metrics.
- Add an exchange search with exhaustive two-center repair scans.
- Normalize the six-word holes and classify the retained code-hole pairs.

## Completed Phase 3 - Initial Structural Results

- Prove every diameter-at-most-4 radius-3 cover has at least 17 centers.
- Generate exact diameter 5, 6, and 7 branches.
- Generate complete third-center orbit partitions and certificate-safe CNFs.
- Identify the shared eight-word core of four non-isometric near-covers.
- Prove its exact three-center completion minimum six.
- Enumerate all eight minimizing triples and four stabilizer classes.
- Exhaustively classify strict one-center and two-center replacement
  neighborhoods.

## Completed Phase 4 - Stronger Subcore Exclusion

- Delete each word of the eight-word core and partition the eight resulting
  seven-word subcores into four stabilizer orbits.
- Derive the exact pair-averaging reduction for four added centers.
- Build every one of the 2,375,110 unordered pair unions per representative.
- Prove that no representative admits residual at most five.
- Exhibit a residual-six four-center witness for every representative.
- Reproduce the exclusion search and all theorem-defining counts in
  independent Rust and C++20 implementations.
- Verify the same published equality witnesses directly in both
  implementations.
- Validate both reductions against direct exhaustive synthetic controls.

## Completed Phase 5 - Release

- Completed the technical report and archival metadata.
- Published the audited source in the research and result repositories.
- Passed all required CI jobs on the audited release commit.
- Completed repository-level claim, implementation, and reproducibility
  audits.
- Published and protected the `v0.2.0` release.
- Archived the exact release through Zenodo at version DOI
  `10.5281/zenodo.22452733`.
- Added the version and concept DOIs to maintained citation metadata and
  reran current-main CI.
- Kept the immutable release tag fixed after archival.

## Next Mathematical Phase

1. Import the seven-word exclusions into the exact diameter branches.
2. Discover and certify additional recurrent forbidden subcores.
3. Build a global canonical classification of candidate 11-word structures.
4. Independently certify the historical lower bound 11.
5. Continue nonlinear construction search for an 11-word cover.
6. Pursue complete proof-producing exclusion if no construction appears.

## Kill And Claim Criteria

- A timeout is never an exclusion.
- A repeated local-search minimum is never a lower bound.
- A SAT result without a checked model or proof is not retained as a theorem.
- A local theorem is stated only for its explicit fixed object or branch.
- The global value changes only after a verified 11-word construction or a
  complete checked exclusion of every 11-word code.
