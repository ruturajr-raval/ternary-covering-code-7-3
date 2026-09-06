use std::env;
use std::process;
use std::thread;
use std::time::Instant;

const Q: usize = 3;
const N: usize = 7;
const RADIUS: usize = 3;
const WORD_COUNT: usize = 2_187;
const CORE_SIZE: usize = 8;
const HOLE_COUNT: usize = 253;
const MASK_WORDS: usize = HOLE_COUNT.div_ceil(64);
const ALLOWED_CENTER_COUNT: usize = WORD_COUNT - CORE_SIZE;
const EXPECTED_TRIPLES: u64 = 1_721_956_929;
const EXPECTED_MINIMUM: usize = 6;
const EXPECTED_MINIMIZER_COUNT: usize = 8;
const MAX_WORKERS: usize = 64;

type Word = [u8; N];
type HoleMask = [u64; MASK_WORDS];
type Triple = [usize; 3];

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

const KNOWN_RESIDUAL_SIX_WITNESS: [Word; 3] = [
    [1, 1, 1, 2, 2, 1, 2],
    [2, 2, 2, 0, 1, 1, 1],
    [2, 2, 2, 1, 2, 2, 2],
];

struct Space {
    words: Vec<Word>,
    core_ids: [usize; CORE_SIZE],
    holes: Vec<usize>,
    candidate_ids: Vec<usize>,
    candidate_masks: Vec<HoleMask>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SearchResult {
    triples: u64,
    minimum_residual: usize,
    minimizing_triple: Option<Triple>,
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

fn format_word(id: usize) -> String {
    decode(id)
        .into_iter()
        .map(|symbol| char::from(b'0' + symbol))
        .collect()
}

fn distance(left: &Word, right: &Word) -> usize {
    left.iter()
        .zip(right.iter())
        .filter(|(left_symbol, right_symbol)| left_symbol != right_symbol)
        .count()
}

fn build_words() -> Vec<Word> {
    (0..WORD_COUNT).map(decode).collect()
}

fn find_core_holes(words: &[Word], core_ids: &[usize; CORE_SIZE]) -> Vec<usize> {
    words
        .iter()
        .enumerate()
        .filter_map(|(point_id, point)| {
            core_ids
                .iter()
                .all(|&center_id| distance(&words[center_id], point) > RADIUS)
                .then_some(point_id)
        })
        .collect()
}

fn coverage_mask(center: &Word, words: &[Word], holes: &[usize]) -> HoleMask {
    let mut mask = [0u64; MASK_WORDS];
    for (local_id, &point_id) in holes.iter().enumerate() {
        if distance(center, &words[point_id]) <= RADIUS {
            mask[local_id / 64] |= 1u64 << (local_id % 64);
        }
    }
    mask
}

fn build_space() -> Space {
    let words = build_words();
    let core_ids = CORE.map(|word| encode(&word));
    let holes = find_core_holes(&words, &core_ids);

    let mut candidate_ids = Vec::with_capacity(ALLOWED_CENTER_COUNT);
    let mut candidate_masks = Vec::with_capacity(ALLOWED_CENTER_COUNT);
    for (center_id, center) in words.iter().enumerate() {
        if core_ids.contains(&center_id) {
            continue;
        }
        candidate_ids.push(center_id);
        candidate_masks.push(coverage_mask(center, &words, &holes));
    }

    Space {
        words,
        core_ids,
        holes,
        candidate_ids,
        candidate_masks,
    }
}

fn choose_three(count: usize) -> u64 {
    let count = count as u64;
    count * (count - 1) * (count - 2) / 6
}

fn residual(mask_a: &HoleMask, mask_b: &HoleMask, mask_c: &HoleMask) -> usize {
    let covered = (0..MASK_WORDS)
        .map(|block| (mask_a[block] | mask_b[block] | mask_c[block]).count_ones() as usize)
        .sum::<usize>();
    HOLE_COUNT - covered
}

fn update_minimum(result: &mut SearchResult, residual: usize, triple: Triple) {
    if residual < result.minimum_residual
        || (residual == result.minimum_residual
            && result
                .minimizing_triple
                .is_none_or(|current| triple < current))
    {
        result.minimum_residual = residual;
        result.minimizing_triple = Some(triple);
    }
}

fn search_worker(
    worker_id: usize,
    worker_count: usize,
    candidate_ids: &[usize],
    masks: &[HoleMask],
) -> SearchResult {
    let candidate_count = candidate_ids.len();
    let mut result = SearchResult {
        triples: 0,
        minimum_residual: HOLE_COUNT + 1,
        minimizing_triple: None,
    };

    for first in (worker_id..candidate_count - 2).step_by(worker_count) {
        let mask_a = masks[first];
        for second in first + 1..candidate_count - 1 {
            let mask_b = masks[second];
            let ab0 = mask_a[0] | mask_b[0];
            let ab1 = mask_a[1] | mask_b[1];
            let ab2 = mask_a[2] | mask_b[2];
            let ab3 = mask_a[3] | mask_b[3];

            for third in second + 1..candidate_count {
                let mask_c = &masks[third];
                let covered = (ab0 | mask_c[0]).count_ones()
                    + (ab1 | mask_c[1]).count_ones()
                    + (ab2 | mask_c[2]).count_ones()
                    + (ab3 | mask_c[3]).count_ones();
                let current_residual = HOLE_COUNT - covered as usize;
                result.triples += 1;

                if current_residual <= result.minimum_residual {
                    update_minimum(
                        &mut result,
                        current_residual,
                        [
                            candidate_ids[first],
                            candidate_ids[second],
                            candidate_ids[third],
                        ],
                    );
                }
            }
        }
    }

    result
}

fn combine_results(partials: Vec<SearchResult>) -> SearchResult {
    let mut combined = SearchResult {
        triples: 0,
        minimum_residual: HOLE_COUNT + 1,
        minimizing_triple: None,
    };

    for partial in partials {
        combined.triples += partial.triples;
        if let Some(triple) = partial.minimizing_triple {
            update_minimum(&mut combined, partial.minimum_residual, triple);
        }
    }
    combined
}

fn exhaustive_search(space: &Space, worker_count: usize) -> SearchResult {
    let workers = worker_count.max(1).min(space.candidate_ids.len() - 2);
    let partials = thread::scope(|scope| {
        let mut handles = Vec::with_capacity(workers);
        for worker_id in 0..workers {
            handles.push(scope.spawn(move || {
                search_worker(
                    worker_id,
                    workers,
                    &space.candidate_ids,
                    &space.candidate_masks,
                )
            }));
        }
        handles
            .into_iter()
            .map(|handle| handle.join().expect("core verifier worker panicked"))
            .collect()
    });
    combine_results(partials)
}

fn minimizer_worker(
    worker_id: usize,
    worker_count: usize,
    candidate_ids: &[usize],
    masks: &[HoleMask],
    target_residual: usize,
) -> Vec<Triple> {
    let candidate_count = candidate_ids.len();
    let mut minimizers = Vec::new();
    for first in (worker_id..candidate_count - 2).step_by(worker_count) {
        let mask_a = masks[first];
        for second in first + 1..candidate_count - 1 {
            let mask_b = masks[second];
            let ab0 = mask_a[0] | mask_b[0];
            let ab1 = mask_a[1] | mask_b[1];
            let ab2 = mask_a[2] | mask_b[2];
            let ab3 = mask_a[3] | mask_b[3];

            for third in second + 1..candidate_count {
                let mask_c = &masks[third];
                let covered = (ab0 | mask_c[0]).count_ones()
                    + (ab1 | mask_c[1]).count_ones()
                    + (ab2 | mask_c[2]).count_ones()
                    + (ab3 | mask_c[3]).count_ones();
                if HOLE_COUNT - covered as usize == target_residual {
                    minimizers.push([
                        candidate_ids[first],
                        candidate_ids[second],
                        candidate_ids[third],
                    ]);
                }
            }
        }
    }
    minimizers
}

fn enumerate_minimizers(space: &Space, worker_count: usize, target_residual: usize) -> Vec<Triple> {
    let partials = thread::scope(|scope| {
        let mut handles = Vec::with_capacity(worker_count);
        for worker_id in 0..worker_count {
            handles.push(scope.spawn(move || {
                minimizer_worker(
                    worker_id,
                    worker_count,
                    &space.candidate_ids,
                    &space.candidate_masks,
                    target_residual,
                )
            }));
        }
        handles
            .into_iter()
            .map(|handle| handle.join().expect("core verifier worker panicked"))
            .collect::<Vec<Vec<Triple>>>()
    });
    let mut minimizers: Vec<Triple> = partials.into_iter().flatten().collect();
    minimizers.sort_unstable();
    minimizers.dedup();
    minimizers
}

fn witness_residual(space: &Space) -> usize {
    let witness_ids = KNOWN_RESIDUAL_SIX_WITNESS.map(|word| encode(&word));
    let witness_masks = witness_ids.map(|center_id| {
        let candidate_index = space
            .candidate_ids
            .binary_search(&center_id)
            .expect("known witness center must be allowed");
        space.candidate_masks[candidate_index]
    });
    residual(&witness_masks[0], &witness_masks[1], &witness_masks[2])
}

fn validate_space(space: &Space) -> Result<(), String> {
    if space.words.len() != WORD_COUNT {
        return Err(format!(
            "constructed {} words, expected {WORD_COUNT}",
            space.words.len()
        ));
    }
    if space.holes.len() != HOLE_COUNT {
        return Err(format!(
            "constructed {} core holes, expected {HOLE_COUNT}",
            space.holes.len()
        ));
    }
    if space.candidate_ids.len() != ALLOWED_CENTER_COUNT {
        return Err(format!(
            "constructed {} allowed centers, expected {ALLOWED_CENTER_COUNT}",
            space.candidate_ids.len()
        ));
    }
    if space
        .core_ids
        .iter()
        .any(|center_id| space.candidate_ids.binary_search(center_id).is_ok())
    {
        return Err("a core center was retained as an allowed center".to_string());
    }
    let triples = choose_three(space.candidate_ids.len());
    if triples != EXPECTED_TRIPLES {
        return Err(format!(
            "computed {triples} candidate triples, expected {EXPECTED_TRIPLES}"
        ));
    }
    let known_residual = witness_residual(space);
    if known_residual != EXPECTED_MINIMUM {
        return Err(format!(
            "known witness leaves {known_residual} holes, expected {EXPECTED_MINIMUM}"
        ));
    }
    Ok(())
}

fn parse_worker_count(value: &str) -> Result<usize, String> {
    let requested = value
        .parse::<usize>()
        .map_err(|_| format!("CORE_DIRECT_WORKERS must be a positive integer, found {value:?}"))?;
    if requested == 0 {
        return Err("CORE_DIRECT_WORKERS must be a positive integer".to_string());
    }
    if requested > MAX_WORKERS {
        return Err(format!(
            "CORE_DIRECT_WORKERS exceeds the supported maximum of {MAX_WORKERS}"
        ));
    }
    Ok(requested)
}

fn worker_count() -> Result<usize, String> {
    let available = thread::available_parallelism()
        .map(|count| count.get())
        .unwrap_or(1);
    match env::var("CORE_DIRECT_WORKERS") {
        Ok(value) => parse_worker_count(&value),
        Err(env::VarError::NotPresent) => Ok(available.min(MAX_WORKERS)),
        Err(error) => Err(format!("could not read CORE_DIRECT_WORKERS: {error}")),
    }
}

fn run() -> Result<(), String> {
    let total_started = Instant::now();
    let space = build_space();
    validate_space(&space)?;

    let requested_workers = worker_count()?;
    let workers = requested_workers.max(1).min(space.candidate_ids.len() - 2);
    let search_started = Instant::now();
    let result = exhaustive_search(&space, workers);
    let minimizers = enumerate_minimizers(&space, workers, result.minimum_residual);
    let search_elapsed = search_started.elapsed();

    if result.triples != EXPECTED_TRIPLES {
        return Err(format!(
            "enumerated {} triples, expected {EXPECTED_TRIPLES}",
            result.triples
        ));
    }
    if result.minimum_residual != EXPECTED_MINIMUM {
        return Err(format!(
            "minimum residual was {}, expected {EXPECTED_MINIMUM}",
            result.minimum_residual
        ));
    }
    if minimizers.len() != EXPECTED_MINIMIZER_COUNT {
        return Err(format!(
            "found {} minimizing triples, expected {EXPECTED_MINIMIZER_COUNT}",
            minimizers.len()
        ));
    }
    let triple = result
        .minimizing_triple
        .ok_or_else(|| "the exhaustive search produced no minimizing triple".to_string())?;
    if minimizers.first() != Some(&triple) {
        return Err("the first-pass and second-pass minimizing triples differ".to_string());
    }

    println!("words={}", space.words.len());
    println!("core_centers={}", space.core_ids.len());
    println!("core_holes={}", space.holes.len());
    println!("allowed_centers={}", space.candidate_ids.len());
    println!("workers={workers}");
    println!("total_triples={}", result.triples);
    println!("minimum_residual={}", result.minimum_residual);
    println!(
        "lexicographically_smallest_minimizing_triple={},{},{}",
        format_word(triple[0]),
        format_word(triple[1]),
        format_word(triple[2])
    );
    println!("minimizing_triple_count={}", minimizers.len());
    for (index, minimizer) in minimizers.iter().enumerate() {
        println!(
            "minimizing_triple[{index}]={},{},{}",
            format_word(minimizer[0]),
            format_word(minimizer[1]),
            format_word(minimizer[2])
        );
    }
    println!("search_seconds={:.3}", search_elapsed.as_secs_f64());
    println!("total_seconds={:.3}", total_started.elapsed().as_secs_f64());
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("core_direct verification failed: {error}");
        process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_radius_three_ball_has_size_379() {
        let words = build_words();
        for center in &words {
            let ball_size = words
                .iter()
                .filter(|point| distance(center, point) <= RADIUS)
                .count();
            assert_eq!(ball_size, 379);
        }
    }

    #[test]
    fn fixed_core_leaves_253_holes() {
        let words = build_words();
        let core_ids = CORE.map(|word| encode(&word));
        let holes = find_core_holes(&words, &core_ids);
        assert_eq!(holes.len(), HOLE_COUNT);
    }

    #[test]
    fn allowed_center_and_triple_counts_are_exact() {
        let space = build_space();
        assert_eq!(space.candidate_ids.len(), ALLOWED_CENTER_COUNT);
        assert_eq!(choose_three(space.candidate_ids.len()), EXPECTED_TRIPLES);
        for core_id in space.core_ids {
            assert!(space.candidate_ids.binary_search(&core_id).is_err());
        }
    }

    #[test]
    fn known_witness_leaves_six_holes() {
        let space = build_space();
        assert_eq!(witness_residual(&space), EXPECTED_MINIMUM);
    }

    #[test]
    fn worker_count_parsing_enforces_safe_bounds() {
        assert_eq!(parse_worker_count("1"), Ok(1));
        assert_eq!(parse_worker_count("64"), Ok(64));
        assert!(parse_worker_count("0").is_err());
        assert!(parse_worker_count("65").is_err());
        assert!(parse_worker_count("-1").is_err());
        assert!(parse_worker_count("workers").is_err());
    }
}
