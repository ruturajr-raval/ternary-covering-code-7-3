# Research Plan

## Phase 1 - Baseline

- Verify the reconstructed 12-word cover by two implementations.
- Generate the direct set-cover CNF deterministically.
- Validate the cardinality encoding on exhaustive small cases.
- Reproduce the baseline with local search.

## Phase 2 - Construction Search

- Run independent 11-word local-search campaigns.
- Record seeds, budgets, best uncovered counts, and code invariants.
- Add large-neighborhood and orbit-aware moves.
- Cross-check candidates with both verifiers.

## Phase 3 - Structural Reduction

- Fix `0000000` by translation symmetry.
- Branch by a diameter-realizing second codeword.
- Canonicalize third-center orbits under the pair stabilizer.
- Add exact subcube coverage inequalities and distance-distribution filters.

## Phase 4 - Certification

- Generate deterministic SAT cubes.
- Solve with proof-producing solvers.
- Convert retained proofs to LRAT.
- Check proofs with two independent checkers.
- Verify branch completeness and every symmetry map.

## Kill Criteria

- Stop a search method if it produces no measurable frontier improvement
  after its recorded budget.
- Do not treat a timeout as an exclusion.
- Do not publish a negative search without a complete checked certificate.
- Reassess the target if the historical lower bound 11 cannot be independently
  reconstructed or certified.
