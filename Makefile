PYTHON ?= python3
PYTHONPATH := src

.PHONY: verify test test-search search-12 search-11 cnf-12 cnf-11

verify:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/verify_code.py data/baseline_code_12.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

test-search:
	cargo test --manifest-path search/Cargo.toml

search-12:
	cargo run --release --manifest-path search/Cargo.toml -- --size 12 --restarts 50 --steps 20000

search-11:
	cargo run --release --manifest-path search/Cargo.toml -- --size 11 --restarts 200 --steps 100000

cnf-12:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_cnf.py --limit 12 --output artifacts/k3-7-3-at-most-12.cnf

cnf-11:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_cnf.py --limit 11 --output artifacts/k3-7-3-at-most-11.cnf
