use std::env;

const Q: usize = 3;
const N: usize = 7;
const RADIUS: usize = 3;
const WORD_COUNT: usize = 2187;

type Word = [u8; N];

struct Rng {
    state: u64,
}

impl Rng {
    fn new(seed: u64) -> Self {
        Self { state: seed.max(1) }
    }

    fn next_u64(&mut self) -> u64 {
        let mut value = self.state;
        value ^= value << 13;
        value ^= value >> 7;
        value ^= value << 17;
        self.state = value;
        value
    }

    fn range(&mut self, upper: usize) -> usize {
        (self.next_u64() as usize) % upper
    }

    fn chance(&mut self, numerator: usize, denominator: usize) -> bool {
        self.range(denominator) < numerator
    }
}

fn decode(mut value: usize) -> Word {
    let mut word = [0u8; N];
    for position in (0..N).rev() {
        word[position] = (value % Q) as u8;
        value /= Q;
    }
    word
}

#[cfg(test)]
fn encode(word: &Word) -> usize {
    word.iter()
        .fold(0usize, |value, symbol| value * Q + *symbol as usize)
}

fn distance(left: &Word, right: &Word) -> usize {
    left.iter()
        .zip(right.iter())
        .filter(|(a, b)| a != b)
        .count()
}

fn build_words() -> Vec<Word> {
    (0..WORD_COUNT).map(decode).collect()
}

fn build_balls(words: &[Word]) -> Vec<Vec<usize>> {
    words
        .iter()
        .map(|center| {
            words
                .iter()
                .enumerate()
                .filter_map(|(index, word)| (distance(center, word) <= RADIUS).then_some(index))
                .collect()
        })
        .collect()
}

fn add_center(counts: &mut [u8], ball: &[usize]) {
    for &point in ball {
        counts[point] += 1;
    }
}

fn remove_center(counts: &mut [u8], ball: &[usize]) {
    for &point in ball {
        counts[point] -= 1;
    }
}

fn uncovered_count(counts: &[u8]) -> usize {
    counts.iter().filter(|&&count| count == 0).count()
}

fn greedy_start(size: usize, balls: &[Vec<usize>], rng: &mut Rng) -> Vec<usize> {
    let mut code = vec![0usize];
    let mut counts = vec![0u8; WORD_COUNT];
    add_center(&mut counts, &balls[0]);

    while code.len() < size {
        let mut best_gain = 0usize;
        let mut candidates = Vec::new();
        for center in 1..WORD_COUNT {
            if code.contains(&center) {
                continue;
            }
            let gain = balls[center]
                .iter()
                .filter(|&&point| counts[point] == 0)
                .count();
            if gain > best_gain {
                best_gain = gain;
                candidates.clear();
                candidates.push(center);
            } else if gain == best_gain {
                candidates.push(center);
            }
        }
        let center = candidates[rng.range(candidates.len())];
        add_center(&mut counts, &balls[center]);
        code.push(center);
    }
    code
}

fn coverage_counts(code: &[usize], balls: &[Vec<usize>]) -> Vec<u8> {
    let mut counts = vec![0u8; WORD_COUNT];
    for &center in code {
        add_center(&mut counts, &balls[center]);
    }
    counts
}

fn unique_contribution(center: usize, counts: &[u8], balls: &[Vec<usize>]) -> usize {
    balls[center]
        .iter()
        .filter(|&&point| counts[point] == 1)
        .count()
}

fn random_unused(code: &[usize], rng: &mut Rng) -> usize {
    loop {
        let center = rng.range(WORD_COUNT);
        if !code.contains(&center) {
            return center;
        }
    }
}

fn perturb(code: &mut [usize], counts: &mut [u8], balls: &[Vec<usize>], rng: &mut Rng) {
    let moves = 2 + rng.range(3);
    for _ in 0..moves {
        let slot = 1 + rng.range(code.len() - 1);
        let replacement = random_unused(code, rng);
        remove_center(counts, &balls[code[slot]]);
        code[slot] = replacement;
        add_center(counts, &balls[replacement]);
    }
}

fn local_search(
    size: usize,
    restarts: usize,
    steps: usize,
    seed: u64,
    balls: &[Vec<usize>],
) -> (Vec<usize>, usize) {
    let mut rng = Rng::new(seed);
    let mut global_best = Vec::new();
    let mut global_uncovered = WORD_COUNT;

    for restart in 0..restarts {
        let mut code = greedy_start(size, balls, &mut rng);
        let mut counts = coverage_counts(&code, balls);
        let mut best_uncovered = uncovered_count(&counts);
        let mut stagnant = 0usize;

        if best_uncovered < global_uncovered {
            global_uncovered = best_uncovered;
            global_best = code.clone();
        }

        for _ in 0..steps {
            let current_uncovered = uncovered_count(&counts);
            if current_uncovered == 0 {
                return (code, 0);
            }

            if stagnant >= 300 {
                perturb(&mut code, &mut counts, balls, &mut rng);
                stagnant = 0;
                continue;
            }

            let slot = if rng.chance(1, 10) {
                1 + rng.range(size - 1)
            } else {
                let minimum = (1..size)
                    .map(|index| unique_contribution(code[index], &counts, balls))
                    .min()
                    .unwrap();
                let choices: Vec<usize> = (1..size)
                    .filter(|&index| unique_contribution(code[index], &counts, balls) == minimum)
                    .collect();
                choices[rng.range(choices.len())]
            };

            let removed = code[slot];
            remove_center(&mut counts, &balls[removed]);
            let uncovered: Vec<usize> = counts
                .iter()
                .enumerate()
                .filter_map(|(point, &count)| (count == 0).then_some(point))
                .collect();
            let focus = uncovered[rng.range(uncovered.len())];

            let replacement = if rng.chance(3, 100) {
                random_unused(&code, &mut rng)
            } else {
                let mut best_gain = 0usize;
                let mut candidates = Vec::new();
                for &center in &balls[focus] {
                    if code
                        .iter()
                        .enumerate()
                        .any(|(index, &used)| index != slot && used == center)
                    {
                        continue;
                    }
                    let gain = balls[center]
                        .iter()
                        .filter(|&&point| counts[point] == 0)
                        .count();
                    if gain > best_gain {
                        best_gain = gain;
                        candidates.clear();
                        candidates.push(center);
                    } else if gain == best_gain {
                        candidates.push(center);
                    }
                }
                candidates[rng.range(candidates.len())]
            };

            code[slot] = replacement;
            add_center(&mut counts, &balls[replacement]);

            let next_uncovered = uncovered_count(&counts);
            if next_uncovered < best_uncovered {
                best_uncovered = next_uncovered;
                stagnant = 0;
            } else {
                stagnant += 1;
            }
            if next_uncovered < global_uncovered {
                global_uncovered = next_uncovered;
                global_best = code.clone();
                println!("restart={} best_uncovered={}", restart, global_uncovered);
            }
        }
    }
    (global_best, global_uncovered)
}

fn parse_option(args: &[String], name: &str, default: usize) -> usize {
    args.windows(2)
        .find(|pair| pair[0] == name)
        .and_then(|pair| pair[1].parse().ok())
        .unwrap_or(default)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let size = parse_option(&args, "--size", 12);
    let restarts = parse_option(&args, "--restarts", 50);
    let steps = parse_option(&args, "--steps", 20_000);
    let seed = parse_option(&args, "--seed", 1) as u64;

    assert!(size >= 2);
    let words = build_words();
    let balls = build_balls(&words);
    assert!(balls.iter().all(|ball| ball.len() == 379));

    let (mut code, uncovered) = local_search(size, restarts, steps, seed, &balls);
    code.sort_unstable();
    println!("result_size={} uncovered={}", code.len(), uncovered);
    for center in code {
        println!(
            "{}",
            words[center]
                .iter()
                .map(|symbol| char::from(b'0' + *symbol))
                .collect::<String>()
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_encoding() {
        for value in 0..WORD_COUNT {
            assert_eq!(encode(&decode(value)), value);
        }
    }

    #[test]
    fn all_balls_have_expected_size() {
        let words = build_words();
        let balls = build_balls(&words);
        assert!(balls.iter().all(|ball| ball.len() == 379));
    }

    #[test]
    fn retained_baseline_covers() {
        let words = build_words();
        let balls = build_balls(&words);
        let code_words = [
            "0000000", "0001012", "0002021", "0022010", "0212211", "1102110", "1121101", "1210222",
            "2000011", "2120122", "2211220", "2212202",
        ];
        let code: Vec<usize> = code_words
            .iter()
            .map(|text| {
                let mut word = [0u8; N];
                for (index, symbol) in text.bytes().enumerate() {
                    word[index] = symbol - b'0';
                }
                encode(&word)
            })
            .collect();
        let counts = coverage_counts(&code, &balls);
        assert_eq!(uncovered_count(&counts), 0);
    }
}
