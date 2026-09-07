PYTHON ?= python3
PYTHONPATH := src
CXX ?= c++
CXXFLAGS ?= -O3 -DNDEBUG -std=c++20 -pthread -Wall -Wextra -Wpedantic -Wconversion -Wshadow
SANITIZER_FLAGS ?= -O1 -g -std=c++20 -pthread -Wall -Wextra -Wpedantic -Wconversion -Wshadow -fsanitize=address,undefined -fno-omit-frame-pointer
TECTONIC ?= tectonic
SOURCE_DATE_EPOCH ?= 1788739200

.PHONY: verify test test-search lint-search verify-result verify-evidence verify-seven-core-outputs replay-seven-core plateau core-direct core-direct-single seven-core-direct seven-core-direct-single seven-core-independent seven-core-independent-self-test seven-core-independent-clang-self-test seven-core-independent-sanitizer-self-test paper-build paper-bundle release-assets verify-release-assets archival-release release-manifest verify-release-manifest search-12 search-11 search-exchange cnf-12 cnf-11 branch-cnf orbit-cnf core-cnf orbits

verify:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/verify_code.py data/baseline_code_12.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

test-search:
	cargo test --locked --manifest-path search/Cargo.toml

lint-search:
	cargo fmt --manifest-path search/Cargo.toml -- --check
	cargo clippy --locked --release --manifest-path search/Cargo.toml --all-targets -- -D warnings

verify-result: verify verify-evidence plateau core-direct-single core-direct replay-seven-core seven-core-independent-clang-self-test seven-core-independent-sanitizer-self-test

verify-evidence:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest tests.test_seven_core_evidence -v

verify-seven-core-outputs:
	$(PYTHON) tools/verify_seven_core_outputs.py \
		build/results/seven-core-rust-single.txt \
		build/results/seven-core-rust-parallel.txt \
		build/results/seven-core-cpp.txt

replay-seven-core: build/seven-core-independent
	mkdir -p build/results
	SEVEN_CORE_DIRECT_WORKERS=1 cargo run --locked --release --manifest-path search/Cargo.toml --bin seven_core_direct > build/results/seven-core-rust-single.txt
	cat build/results/seven-core-rust-single.txt
	cargo run --locked --release --manifest-path search/Cargo.toml --bin seven_core_direct > build/results/seven-core-rust-parallel.txt
	cat build/results/seven-core-rust-parallel.txt
	build/seven-core-independent --self-test-only
	build/seven-core-independent --workers 2 > build/results/seven-core-cpp.txt
	cat build/results/seven-core-cpp.txt
	$(PYTHON) tools/verify_seven_core_outputs.py \
		build/results/seven-core-rust-single.txt \
		build/results/seven-core-rust-parallel.txt \
		build/results/seven-core-cpp.txt

plateau:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/analyze_plateau.py

core-direct:
	cargo run --locked --release --manifest-path search/Cargo.toml --bin core_direct

core-direct-single:
	CORE_DIRECT_WORKERS=1 cargo run --locked --release --manifest-path search/Cargo.toml --bin core_direct

seven-core-direct:
	cargo run --locked --release --manifest-path search/Cargo.toml --bin seven_core_direct

seven-core-direct-single:
	SEVEN_CORE_DIRECT_WORKERS=1 cargo run --locked --release --manifest-path search/Cargo.toml --bin seven_core_direct

build/seven-core-independent: src/seven_core_independent.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@

seven-core-independent: build/seven-core-independent
	build/seven-core-independent

seven-core-independent-self-test: build/seven-core-independent
	build/seven-core-independent --self-test-only

build/seven-core-independent-clang: src/seven_core_independent.cpp
	mkdir -p build
	clang++ $(CXXFLAGS) $< -o $@

seven-core-independent-clang-self-test: build/seven-core-independent-clang
	build/seven-core-independent-clang --self-test-only

build/seven-core-independent-sanitizer: src/seven_core_independent.cpp
	mkdir -p build
	$(CXX) $(SANITIZER_FLAGS) $< -o $@

seven-core-independent-sanitizer-self-test: build/seven-core-independent-sanitizer
	build/seven-core-independent-sanitizer --self-test-only

paper-build:
	mkdir -p build/paper
	SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) FORCE_SOURCE_DATE=1 \
		TECTONIC_CACHE_DIR=build/tectonic-cache \
		$(TECTONIC) -X compile paper/main.tex \
		--outdir build/paper --keep-logs

paper-bundle:
	$(PYTHON) tools/build_paper_bundle.py

release-assets:
	$(PYTHON) tools/build_archival_release.py

verify-release-assets:
	$(PYTHON) tools/build_archival_release.py --verify

archival-release: paper-build paper-bundle release-assets verify-release-assets

release-manifest:
	$(PYTHON) tools/build_release_manifest.py --working-tree

verify-release-manifest:
	$(PYTHON) tools/verify_checksum_manifest.py

search-12:
	cargo run --locked --release --manifest-path search/Cargo.toml -- --size 12 --restarts 50 --steps 20000

search-11:
	cargo run --locked --release --manifest-path search/Cargo.toml -- --size 11 --restarts 32 --steps 15000

search-exchange:
	cargo run --locked --release --manifest-path search/Cargo.toml --bin exchange -- --seed 1 --restarts 4 --rounds 330 --pair-passes 2

cnf-12:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_cnf.py --limit 12 --output artifacts/k3-7-3-at-most-12.cnf

cnf-11:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_cnf.py --limit 11 --output artifacts/k3-7-3-at-most-11.cnf

branch-cnf:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_branch_cnf.py --diameter 5 --limit 11 --output artifacts/k3-7-3-d5-k11.cnf

orbit-cnf:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_orbit_branch_cnf.py --diameter 5 --orbit-index 0 --limit 11 --output artifacts/k3-7-3-d5-orbit0-k11.cnf

core-cnf:
	mkdir -p artifacts
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_core_completion_cnf.py --residual-limit 5 --output artifacts/k3-7-3-core-residual-at-most-5.cnf

orbits:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_orbits.py
