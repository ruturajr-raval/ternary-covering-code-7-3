# Technical Report

The manuscript is `main.tex` in this directory.

From an extracted release source archive, build the PDF with Tectonic 0.16.9
or a compatible release:

```bash
mkdir -p build/paper
SOURCE_DATE_EPOCH=1788739200 FORCE_SOURCE_DATE=1 \
  tectonic -X compile paper/main.tex \
    --outdir build/paper --keep-logs
```

From a full repository checkout, the equivalent project command is:

```bash
make paper-build
```

Build the deterministic source archive:

```bash
make paper-bundle
```

The archive is written to:

```text
dist/paper/ternary-covering-code-7-3-source.tar.gz
```

Build the paper-inclusive archival release set with:

```bash
make release-assets
```

The versioned PDF, source archive, and `SHA256SUMS` are written to
`dist/release/`.

A full repository checkout additionally supports independent theorem replay:

```bash
make seven-core-direct-single
make seven-core-independent
```

The complete repository result replay is:

```bash
make verify-result
```

Verify the release manifest with:

```bash
make verify-release-manifest
```

In a Git checkout this also binds the manifest to the Git index. In a source
archive without `.git`, it verifies every listed file hash. Use
`python3 tools/verify_checksum_manifest.py --listed-only` to request that
file-only mode explicitly.

`ARXIV_METADATA.md` records optional preprint-submission metadata.
`RIGHTS.md` records authorship and licensing boundaries.
