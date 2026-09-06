use std::collections::HashSet;
use std::env;

const Q: usize = 3;
const N: usize = 7;
const RADIUS: usize = 3;
const CODE_SIZE: usize = 11;
const WORD_COUNT: usize = 2187;
const MASK_WORDS: usize = WORD_COUNT.div_ceil(64);

type Word = [u8; N];
type BallMask = [u64; MASK_WORDS];

const FRONTIER_CODES: [[&str; CODE_SIZE]; 4] = [
    [
        "0000000", "0121222", "0122121", "0211111", "1000102", "1002200", "1121021", "1210210",
        "2000201", "2121120", "2212012",
    ],
    [
        "0000000", "0121102", "0212002", "1000212", "1011210", "1102210", "1220210", "2022121",
        "2110121", "2121021", "2201121",
    ],
    [
        "0000000", "0201100", "0212000", "0220200", "1022121", "1111021", "1200221", "2011212",
        "2102212", "2110112", "2121012",
    ],
    [
        "0000000", "0000211", "0112221", "0221122", "1000101", "1112002", "1221012", "1221220",
        "2000202", "2112110", "2221021",
    ],
];

#[allow(dead_code)]
const BASELINE_CODE_12: [&str; 12] = [
    "0000000", "0001012", "0002021", "0022010", "0212211", "1102110", "1121101", "1210222",
    "2000011", "2120122", "2211220", "2212202",
];

#[derive(Clone, Copy)]
struct Candidate {
    center: usize,
    gain: usize,
    key: u64,
}

#[derive(Clone, Debug)]
struct Repair {
    centers: Vec<usize>,
    uncovered: usize,
}

#[derive(Clone, Debug)]
struct SearchMove {
    code: Vec<usize>,
    uncovered: usize,
    removed: Vec<usize>,
    added: Vec<usize>,
}

struct Config {
    seed: u64,
    restarts: usize,
    rounds: usize,
    pool_size: usize,
    pair_passes: usize,
    uphill: usize,
}

struct Rng {
    state: u64,
}

impl Rng {
    fn new(seed: u64) -> Self {
        Self {
            state: mix64(seed.max(1)),
        }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = mix64(self.state);
        self.state
    }

    fn range(&mut self, upper: usize) -> usize {
        assert!(upper > 0);
        (self.next_u64() as usize) % upper
    }

    fn chance(&mut self, numerator: usize, denominator: usize) -> bool {
        self.range(denominator) < numerator
    }

    fn shuffle<T>(&mut self, values: &mut [T]) {
        for index in (1..values.len()).rev() {
            values.swap(index, self.range(index + 1));
        }
    }
}

struct Space {
    balls: Vec<Vec<u16>>,
    #[allow(dead_code)]
    masks: Vec<BallMask>,
}

impl Space {
    fn new() -> Self {
        let words: Vec<Word> = (0..WORD_COUNT).map(decode).collect();
        let mut balls = Vec::with_capacity(WORD_COUNT);
        let mut masks = Vec::with_capacity(WORD_COUNT);

        for center in &words {
            let mut ball = Vec::with_capacity(379);
            let mut mask = [0u64; MASK_WORDS];
            for (point, word) in words.iter().enumerate() {
                if distance(center, word) <= RADIUS {
                    ball.push(point as u16);
                    mask[point / 64] |= 1u64 << (point % 64);
                }
            }
            assert_eq!(ball.len(), 379);
            balls.push(ball);
            masks.push(mask);
        }

        Self { balls, masks }
    }

    #[allow(dead_code)]
    fn covers(&self, center: usize, point: usize) -> bool {
        self.masks[center][point / 64] & (1u64 << (point % 64)) != 0
    }

    fn coverage_counts(&self, code: &[usize]) -> Vec<u8> {
        let mut counts = vec![0u8; WORD_COUNT];
        for &center in code {
            for &point in &self.balls[center] {
                counts[point as usize] += 1;
            }
        }
        counts
    }

    fn uncovered_count(&self, code: &[usize]) -> usize {
        self.coverage_counts(code)
            .into_iter()
            .filter(|&count| count == 0)
            .count()
    }

    fn uncovered_points(&self, code: &[usize]) -> Vec<usize> {
        self.coverage_counts(code)
            .into_iter()
            .enumerate()
            .filter_map(|(point, count)| (count == 0).then_some(point))
            .collect()
    }
}

struct Signatures {
    blocks: usize,
    bits: Vec<u64>,
    gains: Vec<usize>,
}

impl Signatures {
    fn build(space: &Space, need: &[usize]) -> Self {
        let blocks = need.len().div_ceil(64);
        let mut point_to_local = vec![usize::MAX; WORD_COUNT];
        for (local, &point) in need.iter().enumerate() {
            point_to_local[point] = local;
        }

        let mut bits = vec![0u64; WORD_COUNT * blocks];
        let mut gains = vec![0usize; WORD_COUNT];
        for (center, gain) in gains.iter_mut().enumerate() {
            let row = center * blocks;
            for &point in &space.balls[center] {
                let local = point_to_local[point as usize];
                if local != usize::MAX {
                    bits[row + local / 64] |= 1u64 << (local % 64);
                    *gain += 1;
                }
            }
        }

        Self {
            blocks,
            bits,
            gains,
        }
    }

    fn union_count2(&self, left: usize, right: usize) -> usize {
        let left_row = left * self.blocks;
        let right_row = right * self.blocks;
        let mut covered = 0usize;
        for block in 0..self.blocks {
            covered +=
                (self.bits[left_row + block] | self.bits[right_row + block]).count_ones() as usize;
        }
        covered
    }

    fn union_count3(&self, first: usize, second: usize, third: usize) -> usize {
        let first_row = first * self.blocks;
        let second_row = second * self.blocks;
        let third_row = third * self.blocks;
        let mut covered = 0usize;
        for block in 0..self.blocks {
            covered += (self.bits[first_row + block]
                | self.bits[second_row + block]
                | self.bits[third_row + block])
                .count_ones() as usize;
        }
        covered
    }
}

fn mix64(mut value: u64) -> u64 {
    value = value.wrapping_add(0x9e3779b97f4a7c15);
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
    value ^ (value >> 31)
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

fn parse_word(text: &str) -> Word {
    assert_eq!(text.len(), N);
    let mut word = [0u8; N];
    for (position, symbol) in text.bytes().enumerate() {
        assert!((b'0'..=b'2').contains(&symbol));
        word[position] = symbol - b'0';
    }
    word
}

fn format_word(center: usize) -> String {
    decode(center)
        .into_iter()
        .map(|symbol| char::from(b'0' + symbol))
        .collect()
}

fn distance(left: &Word, right: &Word) -> usize {
    left.iter()
        .zip(right.iter())
        .filter(|(a, b)| a != b)
        .count()
}

fn code_from_text<const SIZE: usize>(words: &[&str; SIZE]) -> Vec<usize> {
    let mut code: Vec<usize> = words.iter().map(|text| encode(&parse_word(text))).collect();
    code.sort_unstable();
    code
}

fn code_hash(code: &[usize]) -> u64 {
    code.iter().fold(0xcbf29ce484222325u64, |hash, center| {
        (hash ^ *center as u64).wrapping_mul(0x100000001b3)
    })
}

fn pair_key(seed: u64, left: usize, right: usize) -> u64 {
    let (first, second) = if left < right {
        (left, right)
    } else {
        (right, left)
    };
    mix64(seed ^ ((first as u64) << 32) ^ second as u64)
}

fn triple_key(seed: u64, first: usize, second: usize, third: usize) -> u64 {
    let mut centers = [first, second, third];
    centers.sort_unstable();
    mix64(
        seed ^ (centers[0] as u64).wrapping_mul(0x9e3779b185ebca87)
            ^ (centers[1] as u64).wrapping_mul(0xc2b2ae3d27d4eb4f)
            ^ (centers[2] as u64).wrapping_mul(0x165667b19e3779f9),
    )
}

fn sorted_candidates(signatures: &Signatures, forbidden: &[bool], seed: u64) -> Vec<Candidate> {
    let mut candidates: Vec<Candidate> = (0..WORD_COUNT)
        .filter(|&center| !forbidden[center])
        .map(|center| Candidate {
            center,
            gain: signatures.gains[center],
            key: mix64(seed ^ center as u64),
        })
        .collect();
    candidates.sort_unstable_by(|left, right| {
        right
            .gain
            .cmp(&left.gain)
            .then_with(|| left.key.cmp(&right.key))
            .then_with(|| left.center.cmp(&right.center))
    });
    candidates
}

fn same_pair(left: usize, right: usize, original: &[usize; 2]) -> bool {
    let mut pair = [left, right];
    pair.sort_unstable();
    pair == *original
}

fn same_triple(first: usize, second: usize, third: usize, original: &[usize; 3]) -> bool {
    let mut triple = [first, second, third];
    triple.sort_unstable();
    triple == *original
}

fn best_pair_repair(
    need_len: usize,
    signatures: &Signatures,
    candidates: &[Candidate],
    original: [usize; 2],
    seed: u64,
) -> (Repair, Option<Repair>) {
    assert!(candidates.len() >= 2);
    let mut original = original;
    original.sort_unstable();

    let mut best_all_covered = 0usize;
    let mut best_all_key = u64::MAX;
    let mut best_all = [candidates[0].center, candidates[1].center];
    let mut best_changed_covered = 0usize;
    let mut best_changed_key = u64::MAX;
    let mut best_changed = None;

    for first_index in 0..candidates.len() - 1 {
        let first = candidates[first_index];
        let changed_bound = best_changed.map_or(0, |_| best_changed_covered);
        if first.gain + candidates[0].gain < changed_bound {
            break;
        }

        for second in &candidates[first_index + 1..] {
            if first.gain + second.gain < changed_bound {
                break;
            }

            let covered = signatures.union_count2(first.center, second.center);
            let key = pair_key(seed, first.center, second.center);
            if covered > best_all_covered || (covered == best_all_covered && key < best_all_key) {
                best_all_covered = covered;
                best_all_key = key;
                best_all = [first.center, second.center];
            }

            if !same_pair(first.center, second.center, &original)
                && (best_changed.is_none()
                    || covered > best_changed_covered
                    || (covered == best_changed_covered && key < best_changed_key))
            {
                best_changed_covered = covered;
                best_changed_key = key;
                best_changed = Some([first.center, second.center]);
            }
        }
    }

    let best_all = Repair {
        centers: best_all.into_iter().collect(),
        uncovered: need_len - best_all_covered,
    };
    let best_changed = best_changed.map(|centers| Repair {
        centers: centers.into_iter().collect(),
        uncovered: need_len - best_changed_covered,
    });
    (best_all, best_changed)
}

fn exact_two_exchange(space: &Space, code: &[usize], seed: u64) -> SearchMove {
    assert_eq!(code.len(), CODE_SIZE);
    let mut best_move = None;
    let mut best_key = u64::MAX;

    for first_slot in 0..CODE_SIZE - 1 {
        for second_slot in first_slot + 1..CODE_SIZE {
            let mut removed = [code[first_slot], code[second_slot]];
            removed.sort_unstable();
            let remaining: Vec<usize> = code
                .iter()
                .enumerate()
                .filter_map(|(slot, &center)| {
                    (slot != first_slot && slot != second_slot).then_some(center)
                })
                .collect();
            let need = space.uncovered_points(&remaining);
            let signatures = Signatures::build(space, &need);
            let mut forbidden = vec![false; WORD_COUNT];
            for &center in &remaining {
                forbidden[center] = true;
            }
            let candidates = sorted_candidates(
                &signatures,
                &forbidden,
                seed ^ ((first_slot as u64) << 8) ^ second_slot as u64,
            );
            let (_, changed) = best_pair_repair(
                need.len(),
                &signatures,
                &candidates,
                removed,
                seed ^ pair_key(seed, removed[0], removed[1]),
            );
            let changed = changed.expect("a changed replacement pair must exist");

            let mut candidate_code = remaining;
            candidate_code.extend_from_slice(&changed.centers);
            candidate_code.sort_unstable();
            debug_assert_eq!(candidate_code.len(), CODE_SIZE);
            debug_assert!(candidate_code.windows(2).all(|pair| pair[0] != pair[1]));

            let key = mix64(
                seed ^ code_hash(&candidate_code)
                    ^ pair_key(seed, removed[0], removed[1]).rotate_left(17),
            );
            if best_move.as_ref().is_none_or(|best: &SearchMove| {
                changed.uncovered < best.uncovered
                    || (changed.uncovered == best.uncovered && key < best_key)
            }) {
                best_key = key;
                best_move = Some(SearchMove {
                    code: candidate_code,
                    uncovered: changed.uncovered,
                    removed: removed.into_iter().collect(),
                    added: changed.centers,
                });
            }
        }
    }

    best_move.expect("the two-exchange neighborhood is nonempty")
}

fn add_to_pool(
    center: usize,
    forbidden: &[bool],
    selected: &mut [bool],
    pool: &mut Vec<usize>,
    target: usize,
) {
    if pool.len() < target && !forbidden[center] && !selected[center] {
        selected[center] = true;
        pool.push(center);
    }
}

fn build_lns_pool(
    space: &Space,
    need: &[usize],
    signatures: &Signatures,
    forbidden: &[bool],
    removed: [usize; 3],
    target: usize,
    seed: u64,
) -> Vec<Candidate> {
    let available = forbidden.iter().filter(|&&value| !value).count();
    let target = target.clamp(6, available);
    let ranked = sorted_candidates(signatures, forbidden, seed);
    let mut selected = vec![false; WORD_COUNT];
    let mut pool = Vec::with_capacity(target);

    for center in removed {
        add_to_pool(center, forbidden, &mut selected, &mut pool, target);
    }

    let high_gain_target = (target * 2 / 3).max(pool.len());
    for candidate in &ranked {
        if pool.len() >= high_gain_target {
            break;
        }
        add_to_pool(
            candidate.center,
            forbidden,
            &mut selected,
            &mut pool,
            target,
        );
    }

    if !need.is_empty() {
        let offset = (mix64(seed) as usize) % need.len();
        for step in 0..need.len() {
            if pool.len() >= target * 5 / 6 {
                break;
            }
            let point = need[(offset + step) % need.len()];
            let mut coverers: Vec<usize> = space.balls[point]
                .iter()
                .map(|&center| center as usize)
                .filter(|&center| !forbidden[center] && !selected[center])
                .collect();
            coverers.sort_unstable_by_key(|&center| {
                (
                    mix64(seed ^ ((point as u64) << 32) ^ center as u64),
                    usize::MAX - signatures.gains[center],
                    center,
                )
            });
            for center in coverers.into_iter().take(2) {
                add_to_pool(center, forbidden, &mut selected, &mut pool, target);
            }
        }
    }

    let mut diverse = ranked.clone();
    diverse.sort_unstable_by_key(|candidate| (candidate.key, candidate.center));
    for candidate in diverse {
        if pool.len() >= target {
            break;
        }
        add_to_pool(
            candidate.center,
            forbidden,
            &mut selected,
            &mut pool,
            target,
        );
    }

    let mut result: Vec<Candidate> = pool
        .into_iter()
        .map(|center| Candidate {
            center,
            gain: signatures.gains[center],
            key: mix64(seed ^ center as u64),
        })
        .collect();
    result.sort_unstable_by(|left, right| {
        right
            .gain
            .cmp(&left.gain)
            .then_with(|| left.key.cmp(&right.key))
            .then_with(|| left.center.cmp(&right.center))
    });
    result
}

fn best_changed_triple(
    need_len: usize,
    signatures: &Signatures,
    candidates: &[Candidate],
    original: [usize; 3],
    seed: u64,
) -> Repair {
    assert!(candidates.len() >= 3);
    let mut original = original;
    original.sort_unstable();
    let mut best_covered = 0usize;
    let mut best_key = u64::MAX;
    let mut best = None;

    for first_index in 0..candidates.len() - 2 {
        let first = candidates[first_index];
        let bound = best.map_or(0, |_| best_covered);
        if first.gain + candidates[0].gain + candidates[1].gain < bound {
            break;
        }

        for second_index in first_index + 1..candidates.len() - 1 {
            let second = candidates[second_index];
            if first.gain + second.gain + candidates[0].gain < bound {
                break;
            }

            for third in &candidates[second_index + 1..] {
                if first.gain + second.gain + third.gain < bound {
                    break;
                }
                if same_triple(first.center, second.center, third.center, &original) {
                    continue;
                }

                let covered = signatures.union_count3(first.center, second.center, third.center);
                let key = triple_key(seed, first.center, second.center, third.center);
                if best.is_none()
                    || covered > best_covered
                    || (covered == best_covered && key < best_key)
                {
                    best_covered = covered;
                    best_key = key;
                    best = Some([first.center, second.center, third.center]);
                }
            }
        }
    }

    let centers = best.expect("a changed replacement triple must exist");
    Repair {
        centers: centers.into_iter().collect(),
        uncovered: need_len - best_covered,
    }
}

fn lns_three_exchange(
    space: &Space,
    code: &[usize],
    slots: [usize; 3],
    pool_size: usize,
    seed: u64,
) -> SearchMove {
    let mut removed = [code[slots[0]], code[slots[1]], code[slots[2]]];
    removed.sort_unstable();
    let remaining: Vec<usize> = code
        .iter()
        .enumerate()
        .filter_map(|(slot, &center)| (!slots.contains(&slot)).then_some(center))
        .collect();
    let need = space.uncovered_points(&remaining);
    let signatures = Signatures::build(space, &need);
    let mut forbidden = vec![false; WORD_COUNT];
    for &center in &remaining {
        forbidden[center] = true;
    }
    let pool = build_lns_pool(
        space,
        &need,
        &signatures,
        &forbidden,
        removed,
        pool_size,
        seed,
    );
    let repair = best_changed_triple(need.len(), &signatures, &pool, removed, seed);
    let mut candidate_code = remaining;
    candidate_code.extend_from_slice(&repair.centers);
    candidate_code.sort_unstable();
    debug_assert_eq!(candidate_code.len(), CODE_SIZE);
    debug_assert!(candidate_code.windows(2).all(|pair| pair[0] != pair[1]));

    SearchMove {
        code: candidate_code,
        uncovered: repair.uncovered,
        removed: removed.into_iter().collect(),
        added: repair.centers,
    }
}

fn slot_triples() -> Vec<[usize; 3]> {
    let mut triples = Vec::with_capacity(165);
    for first in 0..CODE_SIZE - 2 {
        for second in first + 1..CODE_SIZE - 1 {
            for third in second + 1..CODE_SIZE {
                triples.push([first, second, third]);
            }
        }
    }
    triples
}

fn transformed_frontier(restart: usize, seed: u64) -> Vec<usize> {
    let base = code_from_text(&FRONTIER_CODES[restart % FRONTIER_CODES.len()]);
    let mut rng = Rng::new(seed ^ (restart as u64).wrapping_mul(0x9e3779b97f4a7c15));
    let mut coordinates = [0usize, 1, 2, 3, 4, 5, 6];
    rng.shuffle(&mut coordinates);
    let mut symbols = [[0u8, 1, 2]; N];
    for permutation in &mut symbols {
        rng.shuffle(permutation);
    }

    let mut transformed = Vec::with_capacity(CODE_SIZE);
    for center in base {
        let word = decode(center);
        let mut image = [0u8; N];
        for position in 0..N {
            image[position] = symbols[position][word[coordinates[position]] as usize];
        }
        transformed.push(encode(&image));
    }
    transformed.sort_unstable();
    transformed
}

fn update_best(best_code: &mut Vec<usize>, best_uncovered: &mut usize, move_result: &SearchMove) {
    if move_result.uncovered < *best_uncovered
        || (move_result.uncovered == *best_uncovered
            && (best_code.is_empty() || move_result.code < *best_code))
    {
        *best_uncovered = move_result.uncovered;
        *best_code = move_result.code.clone();
    }
}

fn run_search(space: &Space, config: &Config) -> (Vec<usize>, usize) {
    let mut global_best = Vec::new();
    let mut global_uncovered = WORD_COUNT;

    for restart in 0..config.restarts {
        let restart_seed = mix64(config.seed ^ (restart as u64).wrapping_mul(0x9e3779b97f4a7c15));
        let mut rng = Rng::new(restart_seed);
        let mut current = transformed_frontier(restart, restart_seed);
        let mut current_uncovered = space.uncovered_count(&current);
        let initial = SearchMove {
            code: current.clone(),
            uncovered: current_uncovered,
            removed: Vec::new(),
            added: Vec::new(),
        };
        update_best(&mut global_best, &mut global_uncovered, &initial);
        println!(
            "restart={} start_uncovered={} global_best={}",
            restart, current_uncovered, global_uncovered
        );

        let mut seen = HashSet::new();
        seen.insert(code_hash(&current));
        let mut triples = slot_triples();
        rng.shuffle(&mut triples);
        let pair_interval = if config.pair_passes == 0 {
            usize::MAX
        } else {
            config.rounds.max(1).div_ceil(config.pair_passes)
        };
        let mut pair_scans = 0usize;

        for round in 0..config.rounds {
            if pair_scans < config.pair_passes && round % pair_interval == 0 {
                let exact_seed = mix64(restart_seed ^ (pair_scans as u64) ^ 0x2e2e2e2e);
                let exact_move = exact_two_exchange(space, &current, exact_seed);
                let neighborhood_min = current_uncovered.min(exact_move.uncovered);
                println!(
                    "restart={} exact_two_scan={} neighborhood_min={} best_changed={}",
                    restart,
                    pair_scans + 1,
                    neighborhood_min,
                    exact_move.uncovered
                );
                pair_scans += 1;

                let exact_hash = code_hash(&exact_move.code);
                if exact_move.uncovered <= current_uncovered && !seen.contains(&exact_hash) {
                    current = exact_move.code.clone();
                    current_uncovered = exact_move.uncovered;
                    seen.insert(exact_hash);
                    update_best(&mut global_best, &mut global_uncovered, &exact_move);
                }
            }

            if round > 0 && round % triples.len() == 0 {
                rng.shuffle(&mut triples);
            }
            let slots = triples[round % triples.len()];
            let move_seed = mix64(
                restart_seed
                    ^ (round as u64).wrapping_mul(0xc2b2ae3d27d4eb4f)
                    ^ code_hash(&current),
            );
            let candidate = lns_three_exchange(space, &current, slots, config.pool_size, move_seed);
            let candidate_hash = code_hash(&candidate.code);
            let unseen = !seen.contains(&candidate_hash);
            let delta = candidate.uncovered.saturating_sub(current_uncovered);
            let within_best_band = candidate.uncovered <= global_uncovered + config.uphill;
            let accept = candidate.uncovered < current_uncovered
                || (candidate.uncovered == current_uncovered && unseen)
                || (unseen
                    && within_best_band
                    && delta <= config.uphill
                    && rng.chance(1, 4 + 2 * delta));

            if accept {
                current = candidate.code.clone();
                current_uncovered = candidate.uncovered;
                seen.insert(candidate_hash);
            }
            let previous_global = global_uncovered;
            update_best(&mut global_best, &mut global_uncovered, &candidate);
            if global_uncovered < previous_global {
                println!(
                    "restart={} round={} global_best={} removed={:?} added={:?}",
                    restart, round, global_uncovered, candidate.removed, candidate.added
                );
            }
            if global_uncovered == 0 {
                return (global_best, 0);
            }
        }
    }

    (global_best, global_uncovered)
}

fn parse_value<T: std::str::FromStr>(args: &[String], name: &str, default: T) -> T {
    args.windows(2)
        .find(|pair| pair[0] == name)
        .and_then(|pair| pair[1].parse().ok())
        .unwrap_or(default)
}

fn print_help() {
    println!(
        "Usage: exchange [--seed N] [--restarts N] [--rounds N] [--pool N] \
         [--pair-passes N] [--uphill N]"
    );
    println!("Exact two-center scans are interleaved with three-center large-neighborhood moves.");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print_help();
        return;
    }

    let config = Config {
        seed: parse_value(&args, "--seed", 1u64),
        restarts: parse_value(&args, "--restarts", 1usize).max(1),
        rounds: parse_value(&args, "--rounds", 48usize),
        pool_size: parse_value(&args, "--pool", 144usize).max(6),
        pair_passes: parse_value(&args, "--pair-passes", 1usize),
        uphill: parse_value(&args, "--uphill", 2usize),
    };
    println!(
        "config seed={} restarts={} rounds={} pool={} pair_passes={} uphill={}",
        config.seed,
        config.restarts,
        config.rounds,
        config.pool_size,
        config.pair_passes,
        config.uphill
    );

    let space = Space::new();
    let (mut code, uncovered) = run_search(&space, &config);
    code.sort_unstable();
    let verified = space.uncovered_count(&code);
    assert_eq!(uncovered, verified);
    println!(
        "result_seed={} result_size={} uncovered={}",
        config.seed,
        code.len(),
        verified
    );
    for center in code {
        println!("{}", format_word(center));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encoding_round_trip() {
        for center in 0..WORD_COUNT {
            assert_eq!(encode(&decode(center)), center);
        }
    }

    #[test]
    fn hamming_balls_have_expected_size() {
        let space = Space::new();
        assert!(space.balls.iter().all(|ball| ball.len() == 379));
    }

    #[test]
    fn retained_frontiers_each_leave_six_uncovered() {
        let space = Space::new();
        for code_words in FRONTIER_CODES {
            let code = code_from_text(&code_words);
            assert_eq!(space.uncovered_count(&code), 6);
        }
    }

    #[test]
    fn isometry_preserves_frontier_score() {
        let space = Space::new();
        for restart in 0..8 {
            let code = transformed_frontier(restart, 20260905);
            assert_eq!(space.uncovered_count(&code), 6);
        }
    }

    #[test]
    fn pair_repair_recovers_a_known_cover() {
        let space = Space::new();
        let code = code_from_text(&BASELINE_CODE_12);
        let removed = [code[3], code[9]];
        let remaining: Vec<usize> = code
            .iter()
            .copied()
            .filter(|center| !removed.contains(center))
            .collect();
        let need = space.uncovered_points(&remaining);
        let signatures = Signatures::build(&space, &need);
        let mut forbidden = vec![false; WORD_COUNT];
        for center in remaining {
            forbidden[center] = true;
        }
        let candidates = sorted_candidates(&signatures, &forbidden, 17);
        let (best, _) = best_pair_repair(need.len(), &signatures, &candidates, removed, 17);
        assert_eq!(best.uncovered, 0);
    }

    #[test]
    fn lns_move_has_distinct_centers_and_exact_score() {
        let space = Space::new();
        let code = code_from_text(&FRONTIER_CODES[0]);
        let result = lns_three_exchange(&space, &code, [0, 4, 8], 48, 23);
        assert_eq!(result.code.len(), CODE_SIZE);
        assert!(result.code.windows(2).all(|pair| pair[0] != pair[1]));
        assert_eq!(space.uncovered_count(&result.code), result.uncovered);
    }

    #[test]
    fn masks_agree_with_ball_lists() {
        let space = Space::new();
        for center in [0, 1, 127, 1093, 2186] {
            let listed: HashSet<usize> = space.balls[center]
                .iter()
                .map(|&point| point as usize)
                .collect();
            for point in 0..WORD_COUNT {
                assert_eq!(space.covers(center, point), listed.contains(&point));
            }
        }
    }
}
