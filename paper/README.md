# Technical Report

The manuscript is `main.tex`.

Build the PDF from the repository root:

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

The manuscript's primary theorem is replayed independently with:

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
