# Release Notes

## [v0.2.1](https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.1) - 2026-09-07

### Archival Patch

- Added an explicitly named compiled PDF, deterministic paper-source archive,
  and `SHA256SUMS` for GitHub and Zenodo archival.
- Updated citation, release, and archive metadata to version DOI
  `10.5281/zenodo.22647770` and concept DOI
  `10.5281/zenodo.22452732`.
- This is an archival and documentation patch. The theorem, proof,
  certificates, data, exact counts, and computations are unchanged from
  `v0.2.0`.

## [v0.2.0](https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.0) - 2026-09-06

### Result

For each of eight seven-word subcores obtained by deleting one word from the
explicit eight-word core `C0`, every set of at most four added centers leaves
at least six radius-3 holes, and equality is attained. Consequently, no
covering code of size at most 11 contains one of these subcores or an
isometric copy.

The global interval remains

```text
11 <= K_3(7,3) <= 12.
```

### Verification

Independent Rust and C++20 exhaustive verifiers cover all four deletion-orbit
representatives and reproduce:

```text
9,500,440 pair entries
347,365 eligible first-pair queries
minimum residual 6 in every deletion orbit
```

Exact counts are recorded in `evidence/seven-core-results.json`, fresh outputs
are checked by `tools/verify_seven_core_outputs.py`, and tracked release files
are bound by `release-manifest.sha256`.

### Supporting Results

- The full eight-word core has exact three-center residual minimum six.
- Exactly eight minimizing triples occur in four stabilizer classes.
- Strict one-center and two-center replacement neighborhoods are classified
  for four specified six-hole near-cover classes.
- Every diameter-at-most-4 radius-3 ternary length-7 cover has at least 17
  centers.

### Scope

This release does not construct an 11-word cover, exclude every 11-word cover,
independently certify the historical lower bound 11, or change the global
interval. The eight excluded subcores are not claimed to occur in every
hypothetical 11-word cover. No external mathematical review is claimed.

### Release And Archive

- Tagged release:
  `https://github.com/ruturajr-raval/ternary-covering-code-7-3/releases/tag/v0.2.0`
- Release commit:
  `e9fbec7c28e0e6a386953f0e0f242582de7802bb`
- Version DOI: `10.5281/zenodo.22452733`
- Stable concept DOI: `10.5281/zenodo.22452732`
- Zenodo snapshot:
  `ruturajr-raval/ternary-covering-code-7-3-v0.2.0.zip`
- Zenodo snapshot SHA-256:
  `6cea2392f585cb91f7a8d30a6934755e5da5c0244056938f3d48e1bc1501e2d0`
