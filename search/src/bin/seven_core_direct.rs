use std::collections::BTreeSet;
use std::env;
use std::process;
use std::thread;
use std::time::Instant;

const Q: usize = 3;
const N: usize = 7;
const RADIUS: usize = 3;
const WORD_COUNT: usize = 2_187;
const BALL_SIZE: usize = 379;
const CORE_SIZE: usize = 8;
const SEVEN_CORE_SIZE: usize = 7;
const ADDED_CENTER_COUNT: usize = 4;
const RESIDUAL_EXCLUSION_LIMIT: usize = 5;
const EXPECTED_MINIMUM_RESIDUAL: usize = 6;
const MAX_HOLE_COUNT: usize = 518;
const MASK_WORDS: usize = MAX_HOLE_COUNT.div_ceil(64);
const MAX_WORKERS: usize = 64;
const LEAF_SIZE: usize = 64;
const EXPECTED_CANONICAL_HOLE_STABILIZER: usize = 2_304;
const EXPECTED_CORE_STABILIZER: usize = 18;
const EXPECTED_CANDIDATE_COUNT: usize = WORD_COUNT - SEVEN_CORE_SIZE;
const EXPECTED_PAIR_COUNT: u64 = 2_375_110;
const FNV_OFFSET: u64 = 1_469_598_103_934_665_603;
const FNV_PRIME: u64 = 1_099_511_628_211;
const NO_NODE: u32 = u32::MAX;
const NO_SPLIT: u16 = u16::MAX;

type Word = [u8; N];

const CORE: [Word; CORE_SIZE] = [
    [0, 0, 0, 0, 0, 1, 1],
    [0, 0, 0, 0, 1, 0, 2],
    [0, 0, 0, 0, 2, 2, 0],
    [0, 0, 0, 2, 1, 2, 1],
    [1, 1, 1, 1, 0, 2, 2],
    [1, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 2, 0, 1],
    [2, 2, 2, 2, 0, 0, 0],
];

const SIX_HOLE_TAIL: [Word; 3] = [
    [1, 1, 1, 2, 2, 1, 2],
    [2, 2, 2, 0, 1, 2, 1],
    [2, 2, 2, 1, 2, 1, 2],
];

const EXPECTED_CANONICAL_HOLE: [Word; EXPECTED_MINIMUM_RESIDUAL] = [
    [0, 0, 1, 1, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 0],
    [1, 0, 0, 1, 0, 0, 0],
    [1, 0, 1, 0, 0, 0, 0],
    [1, 1, 0, 0, 0, 0, 0],
];

#[derive(Clone, Copy)]
struct ExpectedRepresentative {
    representative: Word,
    orbit_size: usize,
    hole_count: usize,
    eligible_first_pairs: usize,
    first_pair_hash: u64,
}

const EXPECTED_REPRESENTATIVES: [ExpectedRepresentative; 4] = [
    ExpectedRepresentative {
        representative: [0, 0, 0, 0, 0, 1, 1],
        orbit_size: 3,
        hole_count: 370,
        eligible_first_pairs: 86_319,
        first_pair_hash: 0x6d1d_0f24_3334_ca67,
    },
    ExpectedRepresentative {
        representative: [0, 0, 0, 2, 1, 2, 1],
        orbit_size: 1,
        hole_count: 358,
        eligible_first_pairs: 81_290,
        first_pair_hash: 0xb34c_3a44_a69f_a433,
    },
    ExpectedRepresentative {
        representative: [1, 1, 1, 1, 0, 2, 2],
        orbit_size: 3,
        hole_count: 396,
        eligible_first_pairs: 82_464,
        first_pair_hash: 0x6cf8_18bc_b931_66ac,
    },
    ExpectedRepresentative {
        representative: [2, 2, 2, 2, 0, 0, 0],
        orbit_size: 1,
        hole_count: 518,
        eligible_first_pairs: 97_292,
        first_pair_hash: 0x3ab5_df94_51d2_515b,
    },
];

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct HoleMask {
    blocks: [u64; MASK_WORDS],
}

impl HoleMask {
    fn full(hole_count: usize) -> Self {
        let mut result = Self::default();
        let block_count = hole_count.div_ceil(64);
        result.blocks[..block_count].fill(u64::MAX);
        if !hole_count.is_multiple_of(64) {
            result.blocks[block_count - 1] = (1u64 << (hole_count % 64)) - 1;
        }
        result
    }

    fn set(&mut self, bit: usize) {
        self.blocks[bit / 64] |= 1u64 << (bit % 64);
    }

    fn contains(&self, bit: usize) -> bool {
        self.blocks[bit / 64] & (1u64 << (bit % 64)) != 0
    }

    fn union(self, other: Self, block_count: usize) -> Self {
        let mut result = Self::default();
        for (target, (left, right)) in result.blocks[..block_count].iter_mut().zip(
            self.blocks[..block_count]
                .iter()
                .zip(&other.blocks[..block_count]),
        ) {
            *target = left | right;
        }
        result
    }

    fn difference(self, covered: Self, block_count: usize) -> Self {
        let mut result = Self::default();
        for (target, (required, available)) in result.blocks[..block_count].iter_mut().zip(
            self.blocks[..block_count]
                .iter()
                .zip(&covered.blocks[..block_count]),
        ) {
            *target = required & !available;
        }
        result
    }

    fn count(self, block_count: usize) -> usize {
        self.blocks[..block_count]
            .iter()
            .map(|block| block.count_ones() as usize)
            .sum()
    }

    fn missing_from(self, available: Self, block_count: usize) -> usize {
        self.blocks[..block_count]
            .iter()
            .zip(&available.blocks[..block_count])
            .map(|(required, present)| (required & !present).count_ones() as usize)
            .sum()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Transform {
    active_permutation: [usize; 4],
    inactive_permutation: [usize; 3],
    complement_active: bool,
    inactive_swaps: u8,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct DeletionOrbit {
    representative: Word,
    members: Vec<Word>,
}

struct SymmetryReport {
    canonical_hole_stabilizer_size: usize,
    core_stabilizer: Vec<Transform>,
    deletion_orbits: Vec<DeletionOrbit>,
}

struct HammingSpace {
    words: Vec<Word>,
}

struct SevenCoreInstance {
    representative: Word,
    holes: Vec<usize>,
    candidate_ids: Vec<usize>,
    candidate_masks: Vec<HoleMask>,
    block_count: usize,
    full_mask: HoleMask,
}

#[derive(Clone, Copy, Debug)]
struct PairEntry {
    mask: HoleMask,
    first: u16,
    second: u16,
}

#[derive(Clone, Copy)]
struct PairNode {
    all: HoleMask,
    any: HoleMask,
    begin: u32,
    end: u32,
    left: u32,
    right: u32,
    split: u16,
}

struct PairIndex {
    entries: Vec<PairEntry>,
    nodes: Vec<PairNode>,
    root: u32,
    block_count: usize,
    full_mask: HoleMask,
}

#[derive(Clone, Copy)]
struct FirstPairQuery {
    first: u16,
    second: u16,
    required: HoleMask,
}

struct FirstPairAccounting {
    all_pairs_scanned: u64,
    threshold: usize,
    hash: u64,
    queries: Vec<FirstPairQuery>,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct QueryStats {
    first_pairs_checked: u64,
    tree_nodes_visited: u64,
    leaf_pair_masks_checked: u64,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct Completion {
    centers: [u16; ADDED_CENTER_COUNT],
    residual: usize,
}

#[derive(Clone, Copy, Debug, Default)]
struct WorkerResult {
    stats: QueryStats,
    best_completion: Option<Completion>,
}

struct RepresentativeResult {
    orbit: DeletionOrbit,
    seven_core_holes: usize,
    candidate_centers: usize,
    pair_unions: usize,
    first_pair_threshold: usize,
    eligible_first_pairs: usize,
    first_pair_hash: u64,
    tree_nodes: usize,
    effective_workers: usize,
    query_stats: QueryStats,
    witness_additions: [Word; ADDED_CENTER_COUNT],
    witness_holes: Vec<Word>,
    build_seconds: f64,
    query_seconds: f64,
    total_seconds: f64,
}

struct Config {
    workers: usize,
}

fn decode(mut value: usize) -> Word {
    let mut word = [0u8; N];
    for position in (0..N).rev() {
        word[position] = (value % Q) as u8;
        value /= Q;
    }
    word
}

fn encode(word: &Word) -> usize {
    word.iter()
        .fold(0usize, |value, symbol| value * Q + *symbol as usize)
}

fn format_word(word: &Word) -> String {
    word.iter()
        .map(|symbol| char::from(b'0' + symbol))
        .collect()
}

fn distance(left: &Word, right: &Word) -> usize {
    left.iter()
        .zip(right)
        .filter(|(left_symbol, right_symbol)| left_symbol != right_symbol)
        .count()
}

fn next_permutation(values: &mut [usize]) -> bool {
    let Some(pivot) = (0..values.len() - 1)
        .rev()
        .find(|&index| values[index] < values[index + 1])
    else {
        return false;
    };
    let successor = (pivot + 1..values.len())
        .rev()
        .find(|&index| values[pivot] < values[index])
        .expect("a permutation successor must exist");
    values.swap(pivot, successor);
    values[pivot + 1..].reverse();
    true
}

fn permutations<const SIZE: usize>() -> Vec<[usize; SIZE]> {
    let mut current = std::array::from_fn(|index| index);
    let mut result = Vec::new();
    loop {
        result.push(current);
        if !next_permutation(&mut current) {
            break;
        }
    }
    result
}

fn apply_transform(word: &Word, transform: Transform) -> Word {
    let mut output = [0u8; N];
    for (output_coordinate, &input_coordinate) in transform.active_permutation.iter().enumerate() {
        let mut symbol = word[input_coordinate];
        if transform.complement_active && symbol < 2 {
            symbol = 1 - symbol;
        }
        output[output_coordinate] = symbol;
    }
    for (output_coordinate, &input_coordinate) in transform.inactive_permutation.iter().enumerate()
    {
        let mut symbol = word[4 + input_coordinate];
        if transform.inactive_swaps & (1u8 << output_coordinate) != 0 && symbol != 0 {
            symbol = 3 - symbol;
        }
        output[4 + output_coordinate] = symbol;
    }
    output
}

fn canonical_hole() -> BTreeSet<Word> {
    EXPECTED_CANONICAL_HOLE.into_iter().collect()
}

fn canonical_hole_isometries() -> Vec<Transform> {
    let active_permutations = permutations::<4>();
    let inactive_permutations = permutations::<3>();
    let expected_hole = canonical_hole();
    let mut transforms = Vec::with_capacity(EXPECTED_CANONICAL_HOLE_STABILIZER);

    for active_permutation in active_permutations {
        for &inactive_permutation in &inactive_permutations {
            for complement_active in [false, true] {
                for inactive_swaps in 0u8..8 {
                    let transform = Transform {
                        active_permutation,
                        inactive_permutation,
                        complement_active,
                        inactive_swaps,
                    };
                    let transformed_hole = expected_hole
                        .iter()
                        .map(|word| apply_transform(word, transform))
                        .collect::<BTreeSet<_>>();
                    assert_eq!(transformed_hole, expected_hole);
                    transforms.push(transform);
                }
            }
        }
    }

    transforms
}

fn analyze_symmetry() -> SymmetryReport {
    let canonical_hole_stabilizer = canonical_hole_isometries();
    assert_eq!(
        canonical_hole_stabilizer.len(),
        EXPECTED_CANONICAL_HOLE_STABILIZER
    );
    let core = CORE.into_iter().collect::<BTreeSet<_>>();
    let core_stabilizer = canonical_hole_stabilizer
        .iter()
        .copied()
        .filter(|&transform| {
            CORE.iter()
                .map(|word| apply_transform(word, transform))
                .collect::<BTreeSet<_>>()
                == core
        })
        .collect::<Vec<_>>();
    assert_eq!(core_stabilizer.len(), EXPECTED_CORE_STABILIZER);

    let mut remaining = core.clone();
    let mut deletion_orbits = Vec::new();
    while let Some(&representative) = remaining.iter().next() {
        let members = core_stabilizer
            .iter()
            .map(|&transform| apply_transform(&representative, transform))
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect::<Vec<_>>();
        assert!(members.iter().all(|member| core.contains(member)));
        for member in &members {
            remaining.remove(member);
        }
        deletion_orbits.push(DeletionOrbit {
            representative,
            members,
        });
    }

    assert_eq!(
        deletion_orbits
            .iter()
            .map(|orbit| orbit.members.len())
            .sum::<usize>(),
        CORE_SIZE
    );
    assert_eq!(deletion_orbits.len(), EXPECTED_REPRESENTATIVES.len());
    for (orbit, expected) in deletion_orbits.iter().zip(EXPECTED_REPRESENTATIVES) {
        assert_eq!(orbit.representative, expected.representative);
        assert_eq!(orbit.members.len(), expected.orbit_size);
    }

    SymmetryReport {
        canonical_hole_stabilizer_size: canonical_hole_stabilizer.len(),
        core_stabilizer,
        deletion_orbits,
    }
}

impl HammingSpace {
    fn new() -> Self {
        let words = (0..WORD_COUNT).map(decode).collect::<Vec<_>>();
        for (id, word) in words.iter().enumerate() {
            assert_eq!(encode(word), id);
        }
        Self { words }
    }

    fn verify_ball_sizes(&self) {
        for center in &self.words {
            let size = self
                .words
                .iter()
                .filter(|point| distance(center, point) <= RADIUS)
                .count();
            assert_eq!(size, BALL_SIZE);
        }
    }

    fn build_seven_core_instance(&self, deleted: Word) -> SevenCoreInstance {
        assert!(CORE.contains(&deleted));
        let deleted_id = encode(&deleted);
        let mut fixed = [false; WORD_COUNT];
        for word in CORE {
            let id = encode(&word);
            if id != deleted_id {
                fixed[id] = true;
            }
        }
        assert_eq!(
            fixed.iter().filter(|&&present| present).count(),
            SEVEN_CORE_SIZE
        );

        let holes = self
            .words
            .iter()
            .enumerate()
            .filter_map(|(point_id, point)| {
                fixed
                    .iter()
                    .enumerate()
                    .filter(|(_, present)| **present)
                    .all(|(center_id, _)| distance(&self.words[center_id], point) > RADIUS)
                    .then_some(point_id)
            })
            .collect::<Vec<_>>();
        assert!(holes.len() <= MAX_HOLE_COUNT);

        let block_count = holes.len().div_ceil(64);
        let mut candidate_ids = Vec::with_capacity(EXPECTED_CANDIDATE_COUNT);
        let mut candidate_masks = Vec::with_capacity(EXPECTED_CANDIDATE_COUNT);
        for (center_id, center) in self.words.iter().enumerate() {
            if fixed[center_id] {
                continue;
            }
            let mut mask = HoleMask::default();
            for (local_point, &point_id) in holes.iter().enumerate() {
                if distance(center, &self.words[point_id]) <= RADIUS {
                    mask.set(local_point);
                }
            }
            candidate_ids.push(center_id);
            candidate_masks.push(mask);
        }
        assert_eq!(candidate_ids.len(), EXPECTED_CANDIDATE_COUNT);
        let full_mask = HoleMask::full(holes.len());

        SevenCoreInstance {
            representative: deleted,
            holes,
            candidate_ids,
            candidate_masks,
            block_count,
            full_mask,
        }
    }
}

impl SevenCoreInstance {
    fn candidate_local_id(&self, center_id: usize) -> usize {
        self.candidate_ids
            .binary_search(&center_id)
            .expect("witness center must be an allowed candidate")
    }

    fn residual_for_local_centers(&self, centers: &[usize]) -> usize {
        let covered = centers.iter().fold(HoleMask::default(), |union, &center| {
            union.union(self.candidate_masks[center], self.block_count)
        });
        self.full_mask.missing_from(covered, self.block_count)
    }

    fn uncovered_words_for_local_centers(
        &self,
        space: &HammingSpace,
        centers: &[usize],
    ) -> Vec<Word> {
        let covered = centers.iter().fold(HoleMask::default(), |union, &center| {
            union.union(self.candidate_masks[center], self.block_count)
        });
        self.holes
            .iter()
            .enumerate()
            .filter_map(|(local_point, &point_id)| {
                (!covered.contains(local_point)).then_some(space.words[point_id])
            })
            .collect()
    }
}

impl PairIndex {
    fn from_candidate_masks(candidate_masks: &[HoleMask], hole_count: usize) -> PairIndex {
        assert!(candidate_masks.len() <= u16::MAX as usize);
        let pair_count = choose_two(candidate_masks.len());
        let block_count = hole_count.div_ceil(64);
        let mut entries = Vec::with_capacity(pair_count as usize);
        for first in 0..candidate_masks.len() - 1 {
            for second in first + 1..candidate_masks.len() {
                entries.push(PairEntry {
                    mask: candidate_masks[first].union(candidate_masks[second], block_count),
                    first: first as u16,
                    second: second as u16,
                });
            }
        }
        assert_eq!(entries.len() as u64, pair_count);

        let mut index = PairIndex {
            entries,
            nodes: Vec::with_capacity(pair_count as usize / LEAF_SIZE * 4),
            root: NO_NODE,
            block_count,
            full_mask: HoleMask::full(hole_count),
        };
        index.root = index.build_node(0, index.entries.len() as u32);
        index
    }

    fn build_node(&mut self, begin: u32, end: u32) -> u32 {
        let mut all = self.full_mask;
        let mut any = HoleMask::default();
        for entry in &self.entries[begin as usize..end as usize] {
            for block in 0..self.block_count {
                all.blocks[block] &= entry.mask.blocks[block];
                any.blocks[block] |= entry.mask.blocks[block];
            }
        }

        let node_id = self.nodes.len() as u32;
        self.nodes.push(PairNode {
            all,
            any,
            begin,
            end,
            left: NO_NODE,
            right: NO_NODE,
            split: NO_SPLIT,
        });
        if end as usize - begin as usize <= LEAF_SIZE {
            return node_id;
        }

        let mut candidate_bits = [0usize; 8];
        let mut candidate_count = 0usize;
        for block in 0..self.block_count {
            let mut varying = any.blocks[block] & !all.blocks[block];
            while varying != 0 && candidate_count < candidate_bits.len() {
                let local_bit = varying.trailing_zeros() as usize;
                candidate_bits[candidate_count] = block * 64 + local_bit;
                candidate_count += 1;
                varying &= varying - 1;
            }
            if candidate_count == candidate_bits.len() {
                break;
            }
        }
        if candidate_count == 0 {
            return node_id;
        }

        let size = end - begin;
        let mut best_split = None;
        let mut best_imbalance = u64::MAX;
        for &bit in &candidate_bits[..candidate_count] {
            let ones = self.entries[begin as usize..end as usize]
                .iter()
                .filter(|entry| entry.mask.contains(bit))
                .count() as u32;
            if ones == 0 || ones == size {
                continue;
            }
            let imbalance = (2 * ones as i64 - size as i64).unsigned_abs();
            if imbalance < best_imbalance {
                best_imbalance = imbalance;
                best_split = Some(bit);
            }
        }
        let Some(split) = best_split else {
            return node_id;
        };

        let middle = partition_by_bit(&mut self.entries, begin as usize, end as usize, split);
        if middle == begin as usize || middle == end as usize {
            return node_id;
        }

        let left = self.build_node(begin, middle as u32);
        let right = self.build_node(middle as u32, end);
        self.nodes[node_id as usize].left = left;
        self.nodes[node_id as usize].right = right;
        self.nodes[node_id as usize].split = split as u16;
        node_id
    }

    fn find_with_missing_at_most(
        &self,
        required: HoleMask,
        limit: usize,
        stats: &mut QueryStats,
    ) -> Option<PairEntry> {
        self.query_node(self.root, required, limit, stats)
    }

    fn query_node(
        &self,
        node_id: u32,
        required: HoleMask,
        limit: usize,
        stats: &mut QueryStats,
    ) -> Option<PairEntry> {
        stats.tree_nodes_visited += 1;
        let node = self.nodes[node_id as usize];
        if required.missing_from(node.any, self.block_count) > limit {
            return None;
        }
        if required.missing_from(node.all, self.block_count) <= limit {
            return Some(self.entries[node.begin as usize]);
        }
        if node.split == NO_SPLIT {
            for entry in &self.entries[node.begin as usize..node.end as usize] {
                stats.leaf_pair_masks_checked += 1;
                if required.missing_from(entry.mask, self.block_count) <= limit {
                    return Some(*entry);
                }
            }
            return None;
        }

        let split = node.split as usize;
        if required.contains(split) {
            self.query_node(node.right, required, limit, stats)
                .or_else(|| self.query_node(node.left, required, limit, stats))
        } else {
            self.query_node(node.left, required, limit, stats)
                .or_else(|| self.query_node(node.right, required, limit, stats))
        }
    }
}

fn partition_by_bit(entries: &mut [PairEntry], begin: usize, end: usize, bit: usize) -> usize {
    let mut left = begin;
    let mut right = end;
    while left < right {
        while left < right && !entries[left].mask.contains(bit) {
            left += 1;
        }
        while left < right && entries[right - 1].mask.contains(bit) {
            right -= 1;
        }
        if left < right {
            entries.swap(left, right - 1);
            left += 1;
            right -= 1;
        }
    }
    left
}

fn choose_two(count: usize) -> u64 {
    count as u64 * (count as u64 - 1) / 2
}

fn first_pair_threshold(hole_count: usize, residual_limit: usize) -> usize {
    (hole_count - residual_limit).div_ceil(2)
}

fn fnv_add(hash: &mut u64, value: u64) {
    *hash ^= value;
    *hash = hash.wrapping_mul(FNV_PRIME);
}

fn build_first_pair_queries(instance: &SevenCoreInstance) -> FirstPairAccounting {
    let threshold = first_pair_threshold(instance.holes.len(), RESIDUAL_EXCLUSION_LIMIT);
    let pair_count = choose_two(instance.candidate_masks.len());
    let mut queries = Vec::new();
    let mut hash = FNV_OFFSET;
    let mut all_pairs_scanned = 0u64;

    for first in 0..instance.candidate_masks.len() - 1 {
        for second in first + 1..instance.candidate_masks.len() {
            all_pairs_scanned += 1;
            let union = instance.candidate_masks[first]
                .union(instance.candidate_masks[second], instance.block_count);
            if union.count(instance.block_count) < threshold {
                continue;
            }
            fnv_add(&mut hash, first as u64);
            fnv_add(&mut hash, second as u64);
            for &block in &union.blocks[..instance.block_count] {
                fnv_add(&mut hash, block);
            }
            queries.push(FirstPairQuery {
                first: first as u16,
                second: second as u16,
                required: instance.full_mask.difference(union, instance.block_count),
            });
        }
    }

    assert_eq!(all_pairs_scanned, pair_count);
    FirstPairAccounting {
        all_pairs_scanned,
        threshold,
        hash,
        queries,
    }
}

fn normalized_completion(
    first_pair: FirstPairQuery,
    second_pair: PairEntry,
    candidate_count: usize,
) -> [u16; ADDED_CENTER_COUNT] {
    let mut centers = Vec::with_capacity(ADDED_CENTER_COUNT);
    for center in [
        first_pair.first,
        first_pair.second,
        second_pair.first,
        second_pair.second,
    ] {
        if !centers.contains(&center) {
            centers.push(center);
        }
    }
    for center in 0..candidate_count as u16 {
        if centers.len() == ADDED_CENTER_COUNT {
            break;
        }
        if !centers.contains(&center) {
            centers.push(center);
        }
    }
    centers.sort_unstable();
    centers
        .try_into()
        .expect("a completion must contain four distinct centers")
}

fn residual_for_completion(
    masks: &[HoleMask],
    centers: [u16; ADDED_CENTER_COUNT],
    full_mask: HoleMask,
    block_count: usize,
) -> usize {
    let covered = centers.iter().fold(HoleMask::default(), |union, &center| {
        union.union(masks[center as usize], block_count)
    });
    full_mask.missing_from(covered, block_count)
}

fn search_worker(
    worker_id: usize,
    worker_count: usize,
    index: &PairIndex,
    queries: &[FirstPairQuery],
    instance: &SevenCoreInstance,
) -> WorkerResult {
    let mut result = WorkerResult::default();
    for query_id in (worker_id..queries.len()).step_by(worker_count) {
        let query = queries[query_id];
        result.stats.first_pairs_checked += 1;
        if let Some(second_pair) = index.find_with_missing_at_most(
            query.required,
            RESIDUAL_EXCLUSION_LIMIT,
            &mut result.stats,
        ) {
            let centers = normalized_completion(query, second_pair, instance.candidate_masks.len());
            let residual = residual_for_completion(
                &instance.candidate_masks,
                centers,
                instance.full_mask,
                instance.block_count,
            );
            assert!(residual <= RESIDUAL_EXCLUSION_LIMIT);
            let completion = Completion { centers, residual };
            if result
                .best_completion
                .is_none_or(|current| completion < current)
            {
                result.best_completion = Some(completion);
            }
        }
    }
    result
}

fn combine_worker_results(partials: Vec<WorkerResult>) -> WorkerResult {
    let mut combined = WorkerResult::default();
    for partial in partials {
        combined.stats.first_pairs_checked += partial.stats.first_pairs_checked;
        combined.stats.tree_nodes_visited += partial.stats.tree_nodes_visited;
        combined.stats.leaf_pair_masks_checked += partial.stats.leaf_pair_masks_checked;
        if let Some(completion) = partial.best_completion {
            if combined
                .best_completion
                .is_none_or(|current| completion < current)
            {
                combined.best_completion = Some(completion);
            }
        }
    }
    combined
}

fn search_queries(
    index: &PairIndex,
    queries: &[FirstPairQuery],
    instance: &SevenCoreInstance,
    requested_workers: usize,
) -> WorkerResult {
    let worker_count = requested_workers
        .clamp(1, MAX_WORKERS)
        .min(queries.len().max(1));
    let partials =
        thread::scope(|scope| {
            let mut handles = Vec::with_capacity(worker_count);
            for worker_id in 0..worker_count {
                handles.push(scope.spawn(move || {
                    search_worker(worker_id, worker_count, index, queries, instance)
                }));
            }
            handles
                .into_iter()
                .map(|handle| handle.join().expect("seven-core worker panicked"))
                .collect()
        });
    combine_worker_results(partials)
}

fn witness_for_instance(
    space: &HammingSpace,
    instance: &SevenCoreInstance,
) -> ([Word; ADDED_CENTER_COUNT], Vec<Word>) {
    let additions = [
        instance.representative,
        SIX_HOLE_TAIL[0],
        SIX_HOLE_TAIL[1],
        SIX_HOLE_TAIL[2],
    ];
    let local_centers = additions
        .iter()
        .map(|word| instance.candidate_local_id(encode(word)))
        .collect::<Vec<_>>();
    assert_eq!(
        local_centers.iter().copied().collect::<BTreeSet<_>>().len(),
        ADDED_CENTER_COUNT
    );
    assert_eq!(
        instance.residual_for_local_centers(&local_centers),
        EXPECTED_MINIMUM_RESIDUAL
    );
    let witness_holes = instance.uncovered_words_for_local_centers(space, &local_centers);
    assert_eq!(witness_holes, EXPECTED_CANONICAL_HOLE);
    (additions, witness_holes)
}

fn verify_representative(
    space: &HammingSpace,
    orbit: &DeletionOrbit,
    expected: ExpectedRepresentative,
    workers: usize,
) -> RepresentativeResult {
    let total_started = Instant::now();
    let instance = space.build_seven_core_instance(orbit.representative);
    assert_eq!(instance.holes.len(), expected.hole_count);
    assert_eq!(instance.candidate_ids.len(), EXPECTED_CANDIDATE_COUNT);
    let (witness_additions, witness_holes) = witness_for_instance(space, &instance);

    let build_started = Instant::now();
    let index = PairIndex::from_candidate_masks(&instance.candidate_masks, instance.holes.len());
    let accounting = build_first_pair_queries(&instance);
    let build_seconds = build_started.elapsed().as_secs_f64();

    assert_eq!(index.entries.len() as u64, EXPECTED_PAIR_COUNT);
    assert_eq!(accounting.all_pairs_scanned, EXPECTED_PAIR_COUNT);
    assert_eq!(accounting.queries.len(), expected.eligible_first_pairs);
    assert_eq!(accounting.hash, expected.first_pair_hash);

    let effective_workers = workers.max(1).min(accounting.queries.len().max(1));
    let query_started = Instant::now();
    let outcome = search_queries(&index, &accounting.queries, &instance, effective_workers);
    let query_seconds = query_started.elapsed().as_secs_f64();
    assert_eq!(
        outcome.stats.first_pairs_checked as usize,
        accounting.queries.len()
    );
    assert!(
        outcome.best_completion.is_none(),
        "a four-center extension with residual at most five was found"
    );

    RepresentativeResult {
        orbit: orbit.clone(),
        seven_core_holes: instance.holes.len(),
        candidate_centers: instance.candidate_ids.len(),
        pair_unions: index.entries.len(),
        first_pair_threshold: accounting.threshold,
        eligible_first_pairs: accounting.queries.len(),
        first_pair_hash: accounting.hash,
        tree_nodes: index.nodes.len(),
        effective_workers,
        query_stats: outcome.stats,
        witness_additions,
        witness_holes,
        build_seconds,
        query_seconds,
        total_seconds: total_started.elapsed().as_secs_f64(),
    }
}

fn parse_worker_count(text: &str) -> Result<usize, String> {
    let workers = text
        .parse::<usize>()
        .map_err(|_| format!("invalid worker count: {text}"))?;
    if workers == 0 {
        return Err("worker count must be positive".to_owned());
    }
    if workers > MAX_WORKERS {
        return Err(format!("worker count must not exceed {MAX_WORKERS}"));
    }
    Ok(workers)
}

fn default_worker_count() -> usize {
    thread::available_parallelism()
        .map(|count| count.get())
        .unwrap_or(1)
        .min(8)
}

fn parse_config() -> Result<Config, String> {
    let mut workers = env::var("SEVEN_CORE_DIRECT_WORKERS")
        .ok()
        .map(|value| parse_worker_count(&value))
        .transpose()?
        .unwrap_or_else(default_worker_count);
    let mut arguments = env::args().skip(1);
    while let Some(argument) = arguments.next() {
        if argument == "--help" || argument == "-h" {
            println!(
                "usage: seven_core_direct [--workers N], 1 <= N <= {MAX_WORKERS}\n\
                 environment: SEVEN_CORE_DIRECT_WORKERS=N"
            );
            process::exit(0);
        }
        if argument == "--workers" {
            let value = arguments
                .next()
                .ok_or_else(|| "--workers requires a value".to_owned())?;
            workers = parse_worker_count(&value)?;
            continue;
        }
        if let Some(value) = argument.strip_prefix("--workers=") {
            workers = parse_worker_count(value)?;
            continue;
        }
        return Err(format!("unknown argument: {argument}"));
    }
    Ok(Config { workers })
}

fn joined_words(words: &[Word]) -> String {
    words.iter().map(format_word).collect::<Vec<_>>().join(",")
}

fn print_result(result: &RepresentativeResult) {
    println!();
    println!(
        "representative={}",
        format_word(&result.orbit.representative)
    );
    println!("orbit_size={}", result.orbit.members.len());
    println!("orbit_members={}", joined_words(&result.orbit.members));
    println!("seven_core_holes={}", result.seven_core_holes);
    println!("candidate_centers={}", result.candidate_centers);
    println!("unordered_candidate_pairs={}", result.pair_unions);
    println!("excluded_residual_range=0..={}", RESIDUAL_EXCLUSION_LIMIT);
    println!("first_pair_threshold={}", result.first_pair_threshold);
    println!("eligible_first_pairs={}", result.eligible_first_pairs);
    println!(
        "first_pair_drift_hash_fnv64=0x{:016x}",
        result.first_pair_hash
    );
    println!("pair_index_nodes={}", result.tree_nodes);
    println!("effective_workers={}", result.effective_workers);
    println!(
        "queried_first_pairs={}",
        result.query_stats.first_pairs_checked
    );
    println!(
        "decision_tree_nodes_visited={}",
        result.query_stats.tree_nodes_visited
    );
    println!(
        "leaf_pair_masks_checked={}",
        result.query_stats.leaf_pair_masks_checked
    );
    println!("completion_with_residual_at_most_5=none");
    println!("minimum_residual={EXPECTED_MINIMUM_RESIDUAL}");
    println!(
        "witness_additions={}",
        joined_words(&result.witness_additions)
    );
    println!("witness_holes={}", joined_words(&result.witness_holes));
    println!("build_seconds={:.3}", result.build_seconds);
    println!("query_seconds={:.3}", result.query_seconds);
    println!("representative_seconds={:.3}", result.total_seconds);
}

fn run(config: Config) {
    let started = Instant::now();
    let space = HammingSpace::new();
    space.verify_ball_sizes();
    let symmetry = analyze_symmetry();

    println!("FINITE EXHAUSTIVE SEVEN-CORE COMPUTATION");
    println!("space=H(7,3)");
    println!("ambient_words={WORD_COUNT}");
    println!("radius={RADIUS}");
    println!("ball_size={BALL_SIZE}");
    println!("core={}", joined_words(&CORE));
    println!(
        "canonical_hole_stabilizer={}",
        symmetry.canonical_hole_stabilizer_size
    );
    println!("core_stabilizer={}", symmetry.core_stabilizer.len());
    println!("deletion_orbit_count={}", symmetry.deletion_orbits.len());
    println!(
        "deletion_orbit_sizes={}",
        symmetry
            .deletion_orbits
            .iter()
            .map(|orbit| orbit.members.len().to_string())
            .collect::<Vec<_>>()
            .join(",")
    );
    println!("requested_workers={}", config.workers);
    println!("pair_reduction=unordered_pair_union_index");
    println!(
        "averaging_rule=every covered point belongs to at least three of the six added-center pairs"
    );
    println!(
        "distinctness_rule=overlapping pair witnesses represent at most four centers and can be padded without losing coverage"
    );

    let mut results = Vec::new();
    for (orbit, expected) in symmetry
        .deletion_orbits
        .iter()
        .zip(EXPECTED_REPRESENTATIVES)
    {
        results.push(verify_representative(
            &space,
            orbit,
            expected,
            config.workers,
        ));
    }
    for result in &results {
        print_result(result);
    }

    println!();
    println!("VERIFIED CONCLUSION");
    println!(
        "Each of the four deletion-orbit representatives has exact four-center minimum residual 6."
    );
    println!(
        "The order-18 core stabilizer partitions all eight core deletions into the four displayed orbits."
    );
    println!(
        "Therefore every seven-word subcore obtained by deleting one core word, and every isometric copy, leaves at least six holes after any four additional distinct centers."
    );
    println!(
        "This is a fixed-subcore statement only and makes no conclusion about codes that contain none of these seven-word subcores."
    );
    println!("representatives_verified={}", results.len());
    println!(
        "deletions_covered_by_orbits={}",
        symmetry
            .deletion_orbits
            .iter()
            .map(|orbit| orbit.members.len())
            .sum::<usize>()
    );
    println!(
        "total_pair_entries_built={}",
        results
            .iter()
            .map(|result| result.pair_unions)
            .sum::<usize>()
    );
    println!(
        "total_eligible_first_pairs_queried={}",
        results
            .iter()
            .map(|result| result.query_stats.first_pairs_checked)
            .sum::<u64>()
    );
    println!("all_four_representative_minima={EXPECTED_MINIMUM_RESIDUAL}");
    println!("scope=the_eight_seven_word_subcores_and_their_isometric_copies");
    println!("total_seconds={:.3}", started.elapsed().as_secs_f64());
}

fn main() {
    match parse_config() {
        Ok(config) => run(config),
        Err(error) => {
            eprintln!("error: {error}");
            process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn synthetic_instance(seed: usize) -> SevenCoreInstance {
        const SYNTHETIC_HOLES: usize = 12;
        const SYNTHETIC_CENTERS: usize = 7;
        let mut state = (seed as u64 + 1).wrapping_mul(0x9e37_79b9_7f4a_7c15);
        let candidate_masks = (0..SYNTHETIC_CENTERS)
            .map(|center| {
                let mut mask = HoleMask::default();
                for point in 0..SYNTHETIC_HOLES {
                    state ^= state << 13;
                    state ^= state >> 7;
                    state ^= state << 17;
                    if (state.wrapping_add((center * 11 + point * 17) as u64) & 7) < 2 {
                        mask.set(point);
                    }
                }
                mask
            })
            .collect::<Vec<_>>();
        SevenCoreInstance {
            representative: [0; N],
            holes: (0..SYNTHETIC_HOLES).collect(),
            candidate_ids: (0..SYNTHETIC_CENTERS).collect(),
            candidate_masks,
            block_count: 1,
            full_mask: HoleMask::full(SYNTHETIC_HOLES),
        }
    }

    fn direct_four_center_decision(instance: &SevenCoreInstance) -> bool {
        let count = instance.candidate_masks.len();
        for first in 0..count - 3 {
            for second in first + 1..count - 2 {
                for third in second + 1..count - 1 {
                    for fourth in third + 1..count {
                        if instance.residual_for_local_centers(&[first, second, third, fourth])
                            <= RESIDUAL_EXCLUSION_LIMIT
                        {
                            return true;
                        }
                    }
                }
            }
        }
        false
    }

    #[test]
    fn hamming_space_geometry_is_reconstructed() {
        let space = HammingSpace::new();
        assert_eq!(space.words.len(), WORD_COUNT);
        for center in [0, 1, 17, 729, WORD_COUNT - 1] {
            let size = space
                .words
                .iter()
                .filter(|point| distance(&space.words[center], point) <= RADIUS)
                .count();
            assert_eq!(size, BALL_SIZE);
        }
    }

    #[test]
    fn stabilizer_and_deletion_orbits_are_exact() {
        let report = analyze_symmetry();
        assert_eq!(
            report.canonical_hole_stabilizer_size,
            EXPECTED_CANONICAL_HOLE_STABILIZER
        );
        assert_eq!(report.core_stabilizer.len(), EXPECTED_CORE_STABILIZER);
        let actual = report
            .deletion_orbits
            .iter()
            .map(|orbit| {
                (
                    format_word(&orbit.representative),
                    orbit.members.iter().map(format_word).collect::<Vec<_>>(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            actual,
            vec![
                (
                    "0000011".to_owned(),
                    vec![
                        "0000011".to_owned(),
                        "0000102".to_owned(),
                        "0000220".to_owned()
                    ]
                ),
                ("0002121".to_owned(), vec!["0002121".to_owned()]),
                (
                    "1111022".to_owned(),
                    vec![
                        "1111022".to_owned(),
                        "1111110".to_owned(),
                        "1111201".to_owned()
                    ]
                ),
                ("2222000".to_owned(), vec!["2222000".to_owned()])
            ]
        );
    }

    #[test]
    fn six_hole_witness_is_valid_for_every_representative() {
        let space = HammingSpace::new();
        for expected in EXPECTED_REPRESENTATIVES {
            let instance = space.build_seven_core_instance(expected.representative);
            assert_eq!(instance.holes.len(), expected.hole_count);
            let (_, holes) = witness_for_instance(&space, &instance);
            assert_eq!(holes, EXPECTED_CANONICAL_HOLE);
        }
    }

    #[test]
    fn pair_index_matches_direct_finite_checks() {
        const SMALL_HOLES: usize = 12;
        let mut center_masks = Vec::new();
        for center in 0..16 {
            let mut mask = HoleMask::default();
            for point in 0..SMALL_HOLES {
                if (center * 5 + point * 7 + center * point) % 11 < 5 {
                    mask.set(point);
                }
            }
            center_masks.push(mask);
        }
        let index = PairIndex::from_candidate_masks(&center_masks, SMALL_HOLES);
        assert!(index.nodes.len() > 1);

        for required_bits in 0u64..1u64 << SMALL_HOLES {
            let mut required = HoleMask::default();
            required.blocks[0] = required_bits;
            for limit in 0..=2 {
                let direct = index
                    .entries
                    .iter()
                    .any(|entry| required.missing_from(entry.mask, 1) <= limit);
                let mut stats = QueryStats::default();
                let indexed = index
                    .find_with_missing_at_most(required, limit, &mut stats)
                    .is_some();
                assert_eq!(indexed, direct);
                assert!(stats.tree_nodes_visited > 0);
            }
        }
    }

    #[test]
    fn masks_and_pair_index_cross_machine_word_boundaries() {
        for hole_count in [63, 64, 65, 127, 128, 129, 517, 518] {
            let full = HoleMask::full(hole_count);
            assert_eq!(full.count(hole_count.div_ceil(64)), hole_count);
            for bit in 0..hole_count {
                assert!(full.contains(bit));
            }
            if hole_count < MAX_HOLE_COUNT {
                assert!(!full.contains(hole_count));
            }
        }

        const HOLES: usize = 65;
        const CENTERS: usize = 12;
        let masks = (0..CENTERS)
            .map(|center| {
                let mut mask = HoleMask::default();
                for point in 0..HOLES {
                    if (center * 13 + point * 17 + center * point) % 23 < 11 {
                        mask.set(point);
                    }
                }
                mask
            })
            .collect::<Vec<_>>();
        let index = PairIndex::from_candidate_masks(&masks, HOLES);
        for sample in 0..128 {
            let mut required = HoleMask::default();
            for point in 0..HOLES {
                if (sample * 19 + point * 7 + sample * point) % 29 < 13 {
                    required.set(point);
                }
            }
            for limit in 0..=3 {
                let direct = index
                    .entries
                    .iter()
                    .any(|entry| required.missing_from(entry.mask, 2) <= limit);
                let mut stats = QueryStats::default();
                let indexed = index
                    .find_with_missing_at_most(required, limit, &mut stats)
                    .is_some();
                assert_eq!(indexed, direct, "sample={sample} limit={limit}");
            }
        }
    }

    #[test]
    fn full_pair_reduction_matches_direct_four_center_controls() {
        let mut positive = 0usize;
        let mut negative = 0usize;
        for seed in 0..6_480 {
            let instance = synthetic_instance(seed);
            let index =
                PairIndex::from_candidate_masks(&instance.candidate_masks, instance.holes.len());
            let accounting = build_first_pair_queries(&instance);
            let indexed = search_queries(&index, &accounting.queries, &instance, 3)
                .best_completion
                .is_some();
            let direct = direct_four_center_decision(&instance);
            assert_eq!(indexed, direct, "seed={seed}");
            if direct {
                positive += 1;
            } else {
                negative += 1;
            }
        }
        assert!(positive > 0);
        assert!(negative > 0);
    }

    #[test]
    fn averaging_thresholds_match_the_four_instances() {
        let thresholds = EXPECTED_REPRESENTATIVES
            .map(|expected| first_pair_threshold(expected.hole_count, RESIDUAL_EXCLUSION_LIMIT));
        assert_eq!(thresholds, [183, 177, 196, 257]);
        assert_eq!(choose_two(EXPECTED_CANDIDATE_COUNT), EXPECTED_PAIR_COUNT);
    }

    #[test]
    fn worker_count_parsing_enforces_safe_bounds() {
        assert_eq!(parse_worker_count("4").unwrap(), 4);
        assert_eq!(parse_worker_count("64").unwrap(), MAX_WORKERS);
        assert!(parse_worker_count("0").is_err());
        assert!(parse_worker_count("65").is_err());
        assert!(parse_worker_count("-1").is_err());
        assert!(parse_worker_count(&usize::MAX.to_string()).is_err());
        assert!(parse_worker_count("not-a-number").is_err());
    }
}
