# Claim Boundary

Status date: 2026-09-06

## Established

- The audited public interval is `11 <= K_3(7,3) <= 12`.
- The repository contains an independently reconstructed 12-word radius-3
  cover, verified by direct distance enumeration and explicit ball union.
- Every radius-3 ternary length-7 cover of diameter at most 4 contains at
  least 17 centers.
- The order-18 stabilizer of the explicit eight-word core `C0` partitions
  its eight seven-word deletions into four orbits of sizes `3,1,3,1`.
- For every seven-word subcore `S_c = C0 \ {c}`, every set of at most four
  added centers leaves at least six words uncovered.
- Residual six is attained for every deletion orbit. Therefore no radius-3
  covering code of size at most 11 contains any `S_c` or an isometric copy.
- The full eight-word core `C0` has exact three-center completion minimum
  six, attained by exactly eight unordered triples in four stabilizer
  classes.
- Four retained size-11 near-covers are pairwise non-isometric, share `C0`
  after normalization, and leave the same six-word `J(4,2)` hole.
- Exact one-center and two-center replacement analysis checks 520,608,000
  raw two-center candidates and finds 30 plateau-preserving neighbor
  incidences.
- Deterministic diameter branches and certificate-safe third-center orbit
  branches are available for diameters 5, 6, and 7.

## Verification Basis

- The Rust seven-core verifier builds every one of the 2,375,110 unordered
  candidate-pair unions in each representative case and queries every pair
  meeting the proved averaging threshold.
- The independent C++20 verifier reconstructs the geometry and stabilizer
  separately, uses a different pair index, and requires disjoint
  complementary pairs.
- Both seven-core implementations independently reproduce 9,500,440 total
  pair entries, 347,365 eligible first-pair queries, the four exact hole
  counts, and residual minimum six. Each directly verifies the same supplied
  equality witnesses.
- CI parses the fresh one-worker Rust, parallel Rust, and C++20 outputs and
  compares every published count, drift check, orbit member, and witness
  with the checked JSON evidence record.
- Synthetic exhaustive controls compare both optimized four-center
  reductions with direct enumeration, including 63-, 64-, and 65-bit mask
  boundaries.
- The Python eight-core implementation performs exact finite mask analysis.
- The Rust eight-core implementation directly scans all
  `binom(2179,3) = 1,721,956,929` added-center triples.
- The Python and Rust eight-core implementations recover the same eight
  minimizing triples.
- The plateau validator preserves all 520,608,000 raw strict two-center
  candidates through exact mask classes, and exhaustive small-universe tests
  compare its optimized pair reductions with direct enumeration.
- CI runs Python 3.9 and 3.12, Rust formatting and Clippy, Rust tests,
  one-worker and parallel Rust theorem replays, the independent C++20
  controls under two compilers and sanitizers, the optimized C++20 replay,
  the plateau validator, and the technical-report build.

## Not Claimed

- No 11-word covering code has been found.
- No complete exclusion of all 11-word covering codes has been produced.
- The global interval has not changed.
- The historical lower bound 11 has not been independently certified.
- The excluded seven-word subcores are not claimed to occur in every
  hypothetical 11-word cover.
- The four retained near-cover classes are not claimed to classify every
  six-hole or balanced size-11 near-cover.
- The local replacement plateau is not a proof of global optimality.
- No residual-at-most-5 SAT UNSAT result or checked SAT proof is claimed.
- No compact proof certificate independent of the two primary verifier
  implementations is supplied.
- No second full implementation of the supporting 520,608,000-candidate
  replacement computation is claimed.
- Solver timeouts and unsuccessful searches are not mathematical evidence.

## Strongest Supported Claim

For each word `c` of the explicit core `C0`, every set of at most four
centers added to `C0 \ {c}` leaves at least six radius-3 holes, and equality
is attained. Hence no size-at-most-11 covering code contains any of these
eight seven-word subcores or an isometric copy.

## Release Gate

The scoped theorem is significant and independently reproducible. A public
release requires:

1. A committed exact revision.
2. Successful clean CI for that revision.
3. Final documentation and technical-report review.
4. A refreshed novelty audit.
5. A tagged GitHub release and versioned Zenodo archive.
