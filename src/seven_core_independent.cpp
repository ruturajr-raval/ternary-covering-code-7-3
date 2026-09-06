#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t q = 3;
constexpr std::size_t length = 7;
constexpr std::size_t radius = 3;
constexpr std::size_t word_count = 2187;
constexpr std::size_t ball_size = 379;
constexpr std::size_t core_size = 8;
constexpr std::size_t fixed_core_size = 7;
constexpr std::size_t added_center_count = 4;
constexpr std::size_t exclusion_limit = 5;
constexpr std::size_t expected_minimum = 6;
constexpr std::size_t expected_orbit_count = 4;
constexpr std::size_t maximum_holes = 518;
constexpr std::size_t mask_blocks = (maximum_holes + 63) / 64;
constexpr std::size_t maximum_workers = 64;
constexpr std::uint64_t fnv_offset = 1469598103934665603ULL;
constexpr std::uint64_t fnv_prime = 1099511628211ULL;
constexpr std::uint32_t no_child = std::numeric_limits<std::uint32_t>::max();

using Word = std::array<std::uint8_t, length>;

constexpr std::array<Word, core_size> core = {{
    {{0, 0, 0, 0, 0, 1, 1}},
    {{0, 0, 0, 0, 1, 0, 2}},
    {{0, 0, 0, 0, 2, 2, 0}},
    {{0, 0, 0, 2, 1, 2, 1}},
    {{1, 1, 1, 1, 0, 2, 2}},
    {{1, 1, 1, 1, 1, 1, 0}},
    {{1, 1, 1, 1, 2, 0, 1}},
    {{2, 2, 2, 2, 0, 0, 0}},
}};

constexpr std::array<Word, 3> common_witness_tail = {{
    {{1, 1, 1, 2, 2, 1, 2}},
    {{2, 2, 2, 0, 1, 2, 1}},
    {{2, 2, 2, 1, 2, 1, 2}},
}};

struct Timer {
    using Clock = std::chrono::steady_clock;
    Clock::time_point start = Clock::now();

    [[nodiscard]] double seconds() const {
        return std::chrono::duration<double>(Clock::now() - start).count();
    }
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        fail(message);
    }
}

[[nodiscard]] std::size_t parse_positive(const std::string& text) {
    require(!text.empty(), "worker count must not be empty");
    require(
        std::all_of(text.begin(), text.end(), [](char character) {
            return character >= '0' && character <= '9';
        }),
        "worker count must contain only decimal digits"
    );
    std::size_t consumed = 0;
    const unsigned long long value = std::stoull(text, &consumed);
    require(consumed == text.size(), "worker count contains trailing text");
    require(value > 0, "worker count must be positive");
    require(
        value <= maximum_workers,
        "worker count exceeds the supported maximum of 64"
    );
    return static_cast<std::size_t>(value);
}

[[nodiscard]] Word decode(std::size_t value) {
    Word result{};
    for (std::size_t position = length; position-- > 0;) {
        result[position] = static_cast<std::uint8_t>(value % q);
        value /= q;
    }
    return result;
}

[[nodiscard]] std::size_t encode(const Word& word) {
    std::size_t value = 0;
    for (const std::uint8_t symbol : word) {
        value = value * q + static_cast<std::size_t>(symbol);
    }
    return value;
}

[[nodiscard]] std::size_t hamming_distance(const Word& left, const Word& right) {
    std::size_t result = 0;
    for (std::size_t coordinate = 0; coordinate < length; ++coordinate) {
        result += left[coordinate] != right[coordinate] ? 1U : 0U;
    }
    return result;
}

[[nodiscard]] std::string format_word(const Word& word) {
    std::string result;
    result.reserve(length);
    for (const std::uint8_t symbol : word) {
        result.push_back(static_cast<char>('0' + symbol));
    }
    return result;
}

template <typename Container>
[[nodiscard]] std::string join_words(const Container& words) {
    std::ostringstream output;
    bool first = true;
    for (const Word& word : words) {
        if (!first) {
            output << ',';
        }
        first = false;
        output << format_word(word);
    }
    return output.str();
}

[[nodiscard]] std::uint64_t choose_two(std::size_t count) {
    return static_cast<std::uint64_t>(count) *
           static_cast<std::uint64_t>(count - 1) / 2;
}

[[nodiscard]] std::uint64_t choose_four(std::size_t count) {
    const auto n = static_cast<std::uint64_t>(count);
    return n * (n - 1) * (n - 2) * (n - 3) / 24;
}

struct Mask {
    std::array<std::uint64_t, mask_blocks> blocks{};

    void set(std::size_t bit) {
        blocks[bit / 64] |= std::uint64_t{1} << (bit % 64);
    }

    [[nodiscard]] bool test(std::size_t bit) const {
        return (blocks[bit / 64] & (std::uint64_t{1} << (bit % 64))) != 0;
    }

    [[nodiscard]] std::size_t count(std::size_t block_count) const {
        std::size_t result = 0;
        for (std::size_t block = 0; block < block_count; ++block) {
            result += static_cast<std::size_t>(std::popcount(blocks[block]));
        }
        return result;
    }

    [[nodiscard]] std::size_t missing_from(
        const Mask& available,
        std::size_t block_count
    ) const {
        std::size_t result = 0;
        for (std::size_t block = 0; block < block_count; ++block) {
            result += static_cast<std::size_t>(
                std::popcount(blocks[block] & ~available.blocks[block])
            );
        }
        return result;
    }

    [[nodiscard]] Mask united(const Mask& other, std::size_t block_count) const {
        Mask result;
        for (std::size_t block = 0; block < block_count; ++block) {
            result.blocks[block] = blocks[block] | other.blocks[block];
        }
        return result;
    }

    void include(const Mask& other, std::size_t block_count) {
        for (std::size_t block = 0; block < block_count; ++block) {
            blocks[block] |= other.blocks[block];
        }
    }

    void intersect(const Mask& other, std::size_t block_count) {
        for (std::size_t block = 0; block < block_count; ++block) {
            blocks[block] &= other.blocks[block];
        }
    }

    [[nodiscard]] Mask difference(
        const Mask& covered,
        std::size_t block_count
    ) const {
        Mask result;
        for (std::size_t block = 0; block < block_count; ++block) {
            result.blocks[block] = blocks[block] & ~covered.blocks[block];
        }
        return result;
    }

    [[nodiscard]] static Mask full(std::size_t bit_count) {
        Mask result;
        const std::size_t full_blocks = bit_count / 64;
        for (std::size_t block = 0; block < full_blocks; ++block) {
            result.blocks[block] = std::numeric_limits<std::uint64_t>::max();
        }
        if (bit_count % 64 != 0) {
            result.blocks[full_blocks] =
                (std::uint64_t{1} << (bit_count % 64)) - 1;
        }
        return result;
    }
};

struct Transform {
    std::array<std::uint8_t, length> input_for_output{};
    std::array<std::array<std::uint8_t, q>, length> symbol_map{};
    std::array<std::uint8_t, core_size> point_action{};

    [[nodiscard]] Word apply(const Word& input) const {
        Word output{};
        for (std::size_t coordinate = 0; coordinate < length; ++coordinate) {
            output[coordinate] =
                symbol_map[coordinate][input[input_for_output[coordinate]]];
        }
        return output;
    }
};

struct CoordinateMatch {
    bool valid = false;
    std::array<std::uint8_t, q> symbol_map{};
};

[[nodiscard]] std::string transform_key(const Transform& transform) {
    std::string result;
    result.reserve(length * (q + 1));
    for (std::size_t coordinate = 0; coordinate < length; ++coordinate) {
        result.push_back(
            static_cast<char>('0' + transform.input_for_output[coordinate])
        );
        for (std::size_t symbol = 0; symbol < q; ++symbol) {
            result.push_back(
                static_cast<char>('0' + transform.symbol_map[coordinate][symbol])
            );
        }
    }
    return result;
}

[[nodiscard]] std::string action_key(
    const std::array<std::uint8_t, core_size>& action
) {
    std::string result;
    result.reserve(core_size);
    for (const std::uint8_t image : action) {
        result.push_back(static_cast<char>('0' + image));
    }
    return result;
}

void enumerate_coordinate_matchings(
    std::size_t output_coordinate,
    const std::array<std::array<CoordinateMatch, length>, length>& matches,
    std::array<bool, length>& used_input,
    Transform& current,
    const std::array<std::uint8_t, core_size>& point_action,
    std::set<std::string>& seen,
    std::vector<Transform>& transforms
) {
    if (output_coordinate == length) {
        current.point_action = point_action;
        for (std::size_t point = 0; point < core_size; ++point) {
            require(
                current.apply(core[point]) == core[point_action[point]],
                "constructed stabilizer map does not realize its point action"
            );
        }
        const std::string key = transform_key(current);
        if (seen.insert(key).second) {
            transforms.push_back(current);
        }
        return;
    }

    for (std::size_t input_coordinate = 0;
         input_coordinate < length;
         ++input_coordinate) {
        if (used_input[input_coordinate] ||
            !matches[input_coordinate][output_coordinate].valid) {
            continue;
        }
        used_input[input_coordinate] = true;
        current.input_for_output[output_coordinate] =
            static_cast<std::uint8_t>(input_coordinate);
        current.symbol_map[output_coordinate] =
            matches[input_coordinate][output_coordinate].symbol_map;
        enumerate_coordinate_matchings(
            output_coordinate + 1,
            matches,
            used_input,
            current,
            point_action,
            seen,
            transforms
        );
        used_input[input_coordinate] = false;
    }
}

[[nodiscard]] std::vector<Transform> enumerate_core_stabilizer() {
    for (std::size_t coordinate = 0; coordinate < length; ++coordinate) {
        std::array<bool, q> symbols{};
        for (const Word& word : core) {
            symbols[word[coordinate]] = true;
        }
        require(
            std::all_of(symbols.begin(), symbols.end(), [](bool value) {
                return value;
            }),
            "a core coordinate does not contain all three symbols"
        );
    }

    std::array<std::uint8_t, core_size> permutation{};
    std::iota(permutation.begin(), permutation.end(), std::uint8_t{0});
    std::set<std::string> seen;
    std::vector<Transform> transforms;

    do {
        std::array<std::array<CoordinateMatch, length>, length> matches{};
        for (std::size_t input_coordinate = 0;
             input_coordinate < length;
             ++input_coordinate) {
            for (std::size_t output_coordinate = 0;
                 output_coordinate < length;
                 ++output_coordinate) {
                std::array<int, q> mapping{{-1, -1, -1}};
                std::array<bool, q> used_images{};
                bool valid = true;
                for (std::size_t point = 0; point < core_size; ++point) {
                    const std::size_t source =
                        core[point][input_coordinate];
                    const std::size_t target =
                        core[permutation[point]][output_coordinate];
                    if (mapping[source] == -1) {
                        if (used_images[target]) {
                            valid = false;
                            break;
                        }
                        mapping[source] = static_cast<int>(target);
                        used_images[target] = true;
                    } else if (
                        mapping[source] != static_cast<int>(target)
                    ) {
                        valid = false;
                        break;
                    }
                }
                if (!valid ||
                    std::any_of(mapping.begin(), mapping.end(), [](int value) {
                        return value < 0;
                    })) {
                    continue;
                }
                matches[input_coordinate][output_coordinate].valid = true;
                for (std::size_t symbol = 0; symbol < q; ++symbol) {
                    matches[input_coordinate][output_coordinate]
                        .symbol_map[symbol] =
                        static_cast<std::uint8_t>(mapping[symbol]);
                }
            }
        }

        std::array<bool, length> used_input{};
        Transform current;
        enumerate_coordinate_matchings(
            0,
            matches,
            used_input,
            current,
            permutation,
            seen,
            transforms
        );
    } while (std::next_permutation(permutation.begin(), permutation.end()));

    require(!transforms.empty(), "no core stabilizer maps were reconstructed");
    require(
        transforms.size() == seen.size(),
        "duplicate core stabilizer maps survived deduplication"
    );

    std::set<std::string> actions;
    for (const Transform& transform : transforms) {
        std::array<bool, core_size> images{};
        for (const std::uint8_t image : transform.point_action) {
            require(image < core_size, "invalid point action");
            require(!images[image], "point action is not a permutation");
            images[image] = true;
        }
        actions.insert(action_key(transform.point_action));
    }
    for (const Transform& left : transforms) {
        for (const Transform& right : transforms) {
            std::array<std::uint8_t, core_size> composition{};
            for (std::size_t point = 0; point < core_size; ++point) {
                composition[point] =
                    right.point_action[left.point_action[point]];
            }
            require(
                actions.contains(action_key(composition)),
                "reconstructed point actions are not closed under composition"
            );
        }
    }
    return transforms;
}

[[nodiscard]] std::size_t unique_action_count(
    const std::vector<Transform>& transforms
) {
    std::set<std::string> actions;
    for (const Transform& transform : transforms) {
        actions.insert(action_key(transform.point_action));
    }
    return actions.size();
}

struct DeletionOrbit {
    std::size_t representative_index = 0;
    std::vector<std::size_t> members;
};

[[nodiscard]] std::vector<DeletionOrbit> deletion_orbits(
    const std::vector<Transform>& stabilizer
) {
    std::array<bool, core_size> assigned{};
    std::vector<DeletionOrbit> result;
    for (std::size_t point = 0; point < core_size; ++point) {
        if (assigned[point]) {
            continue;
        }
        std::set<std::size_t> orbit_set;
        for (const Transform& transform : stabilizer) {
            orbit_set.insert(transform.point_action[point]);
        }
        require(orbit_set.contains(point), "deletion orbit misses its seed");
        DeletionOrbit orbit;
        orbit.representative_index = *orbit_set.begin();
        orbit.members.assign(orbit_set.begin(), orbit_set.end());
        for (const std::size_t member : orbit.members) {
            require(!assigned[member], "deletion orbits overlap");
            assigned[member] = true;
        }
        result.push_back(std::move(orbit));
    }

    std::sort(
        result.begin(),
        result.end(),
        [](const DeletionOrbit& left, const DeletionOrbit& right) {
            return core[left.representative_index] <
                   core[right.representative_index];
        }
    );
    require(
        std::all_of(assigned.begin(), assigned.end(), [](bool value) {
            return value;
        }),
        "deletion orbits do not cover all eight core words"
    );
    return result;
}

struct HammingSpace {
    std::vector<Word> words;

    HammingSpace() {
        words.reserve(word_count);
        for (std::size_t id = 0; id < word_count; ++id) {
            words.push_back(decode(id));
            require(encode(words.back()) == id, "ternary encoding round trip failed");
        }
    }

    void verify_geometry() const {
        require(words.size() == word_count, "wrong ambient word count");
        for (const Word& center : words) {
            std::size_t points = 0;
            for (const Word& target : words) {
                points += hamming_distance(center, target) <= radius ? 1U : 0U;
            }
            require(points == ball_size, "a radius-three ball has the wrong size");
        }
    }
};

struct SevenCoreInstance {
    Word deleted{};
    std::vector<std::size_t> fixed_ids;
    std::vector<std::size_t> holes;
    std::vector<std::size_t> candidate_ids;
    std::vector<Mask> candidate_masks;
    std::size_t block_count = 0;
    Mask full_holes;
};

[[nodiscard]] SevenCoreInstance build_instance(
    const HammingSpace& space,
    std::size_t deleted_index
) {
    require(deleted_index < core_size, "invalid deletion index");
    SevenCoreInstance instance;
    instance.deleted = core[deleted_index];

    std::array<bool, word_count> fixed{};
    for (std::size_t index = 0; index < core_size; ++index) {
        if (index == deleted_index) {
            continue;
        }
        const std::size_t id = encode(core[index]);
        fixed[id] = true;
        instance.fixed_ids.push_back(id);
    }
    require(
        instance.fixed_ids.size() == fixed_core_size,
        "seven-word fixed core has the wrong size"
    );

    for (std::size_t point_id = 0; point_id < word_count; ++point_id) {
        bool covered = false;
        for (const std::size_t center_id : instance.fixed_ids) {
            if (hamming_distance(
                    space.words[point_id],
                    space.words[center_id]
                ) <= radius) {
                covered = true;
                break;
            }
        }
        if (!covered) {
            instance.holes.push_back(point_id);
        }
    }
    require(
        instance.holes.size() <= maximum_holes,
        "seven-word core exceeds the mask capacity"
    );
    instance.block_count = (instance.holes.size() + 63) / 64;
    instance.full_holes = Mask::full(instance.holes.size());

    instance.candidate_ids.reserve(word_count - fixed_core_size);
    instance.candidate_masks.reserve(word_count - fixed_core_size);
    for (std::size_t center_id = 0; center_id < word_count; ++center_id) {
        if (fixed[center_id]) {
            continue;
        }
        Mask coverage;
        for (std::size_t local_point = 0;
             local_point < instance.holes.size();
             ++local_point) {
            if (hamming_distance(
                    space.words[center_id],
                    space.words[instance.holes[local_point]]
                ) <= radius) {
                coverage.set(local_point);
            }
        }
        instance.candidate_ids.push_back(center_id);
        instance.candidate_masks.push_back(coverage);
    }
    require(
        instance.candidate_ids.size() == word_count - fixed_core_size,
        "wrong number of allowed added centers"
    );
    return instance;
}

struct PairEntry {
    Mask coverage;
    std::uint16_t first = 0;
    std::uint16_t second = 0;
};

struct TreeNode {
    Mask possible;
    std::uint32_t begin = 0;
    std::uint32_t end = 0;
    std::uint32_t zero_child = no_child;
    std::uint32_t one_child = no_child;
    std::uint16_t split_bit = 0;
    bool leaf = true;
};

struct QueryStats {
    std::uint64_t first_pairs = 0;
    std::uint64_t tree_nodes = 0;
    std::uint64_t pruned_nodes = 0;
    std::uint64_t leaf_pair_masks = 0;
    std::uint64_t overlap_rejections = 0;

    QueryStats& operator+=(const QueryStats& other) {
        first_pairs += other.first_pairs;
        tree_nodes += other.tree_nodes;
        pruned_nodes += other.pruned_nodes;
        leaf_pair_masks += other.leaf_pair_masks;
        overlap_rejections += other.overlap_rejections;
        return *this;
    }
};

struct PairIndex {
    std::vector<PairEntry> entries;
    std::vector<TreeNode> nodes;
    std::size_t hole_count = 0;
    std::size_t block_count = 0;
    std::size_t leaf_size = 64;
    std::uint32_t root = no_child;

    PairIndex(
        const std::vector<Mask>& center_masks,
        std::size_t holes,
        std::size_t requested_leaf_size = 64
    )
        : hole_count(holes),
          block_count((holes + 63) / 64),
          leaf_size(std::max<std::size_t>(requested_leaf_size, 2)) {
        require(
            center_masks.size() <=
                static_cast<std::size_t>(
                    std::numeric_limits<std::uint16_t>::max()
                ),
            "too many centers for compact pair identifiers"
        );
        entries.reserve(
            static_cast<std::size_t>(choose_two(center_masks.size()))
        );
        for (std::size_t first = 0; first + 1 < center_masks.size(); ++first) {
            for (std::size_t second = first + 1;
                 second < center_masks.size();
                 ++second) {
                entries.push_back(PairEntry{
                    center_masks[first].united(
                        center_masks[second],
                        block_count
                    ),
                    static_cast<std::uint16_t>(first),
                    static_cast<std::uint16_t>(second),
                });
            }
        }
        require(
            entries.size() == choose_two(center_masks.size()),
            "pair index did not construct every unordered pair"
        );
        nodes.reserve(entries.size() / leaf_size * 3 + 1);
        root = build_node(0, entries.size(), 0);
    }

    [[nodiscard]] std::uint32_t build_node(
        std::size_t begin,
        std::size_t end,
        std::size_t depth
    ) {
        require(begin < end, "cannot build an empty pair-index node");
        Mask possible;
        Mask common = Mask::full(hole_count);
        for (std::size_t index = begin; index < end; ++index) {
            possible.include(entries[index].coverage, block_count);
            common.intersect(entries[index].coverage, block_count);
        }

        const auto node_id = static_cast<std::uint32_t>(nodes.size());
        nodes.push_back(TreeNode{
            possible,
            static_cast<std::uint32_t>(begin),
            static_cast<std::uint32_t>(end),
            no_child,
            no_child,
            0,
            true,
        });
        if (end - begin <= leaf_size) {
            return node_id;
        }

        std::array<std::size_t, 12> candidates{};
        std::size_t candidate_count = 0;
        const std::size_t start =
            (depth * 97 + begin * 13 + end * 7) % hole_count;
        for (std::size_t offset = 0;
             offset < hole_count && candidate_count < candidates.size();
             ++offset) {
            const std::size_t bit = (start + offset) % hole_count;
            if (possible.test(bit) != common.test(bit)) {
                candidates[candidate_count++] = bit;
            }
        }
        if (candidate_count == 0) {
            return node_id;
        }

        std::size_t best_bit = candidates[0];
        std::size_t best_imbalance = end - begin;
        for (std::size_t candidate = 0;
             candidate < candidate_count;
             ++candidate) {
            std::size_t ones = 0;
            const std::size_t bit = candidates[candidate];
            for (std::size_t index = begin; index < end; ++index) {
                ones += entries[index].coverage.test(bit) ? 1U : 0U;
            }
            const std::size_t zeros = end - begin - ones;
            const std::size_t imbalance =
                ones > zeros ? ones - zeros : zeros - ones;
            if (imbalance < best_imbalance) {
                best_imbalance = imbalance;
                best_bit = bit;
            }
        }

        const auto middle_iterator = std::partition(
            entries.begin() + static_cast<std::ptrdiff_t>(begin),
            entries.begin() + static_cast<std::ptrdiff_t>(end),
            [best_bit](const PairEntry& entry) {
                return !entry.coverage.test(best_bit);
            }
        );
        const std::size_t middle =
            static_cast<std::size_t>(middle_iterator - entries.begin());
        if (middle == begin || middle == end) {
            return node_id;
        }

        const std::uint32_t zero = build_node(begin, middle, depth + 1);
        const std::uint32_t one = build_node(middle, end, depth + 1);
        nodes[node_id].zero_child = zero;
        nodes[node_id].one_child = one;
        nodes[node_id].split_bit = static_cast<std::uint16_t>(best_bit);
        nodes[node_id].leaf = false;
        return node_id;
    }

    [[nodiscard]] bool find_disjoint_cover(
        const Mask& required,
        std::uint16_t forbidden_first,
        std::uint16_t forbidden_second,
        std::size_t missing_limit,
        QueryStats& stats,
        PairEntry* witness = nullptr
    ) const {
        return query_node(
            root,
            required,
            forbidden_first,
            forbidden_second,
            missing_limit,
            stats,
            witness
        );
    }

    [[nodiscard]] bool query_node(
        std::uint32_t node_id,
        const Mask& required,
        std::uint16_t forbidden_first,
        std::uint16_t forbidden_second,
        std::size_t missing_limit,
        QueryStats& stats,
        PairEntry* witness
    ) const {
        ++stats.tree_nodes;
        const TreeNode& node = nodes[node_id];
        if (required.missing_from(node.possible, block_count) > missing_limit) {
            ++stats.pruned_nodes;
            return false;
        }
        if (node.leaf) {
            for (std::size_t index = node.begin; index < node.end; ++index) {
                ++stats.leaf_pair_masks;
                const PairEntry& entry = entries[index];
                if (entry.first == forbidden_first ||
                    entry.first == forbidden_second ||
                    entry.second == forbidden_first ||
                    entry.second == forbidden_second) {
                    ++stats.overlap_rejections;
                    continue;
                }
                if (required.missing_from(entry.coverage, block_count) <=
                    missing_limit) {
                    if (witness != nullptr) {
                        *witness = entry;
                    }
                    return true;
                }
            }
            return false;
        }

        const TreeNode& zero = nodes[node.zero_child];
        const TreeNode& one = nodes[node.one_child];
        const std::size_t zero_bound =
            required.missing_from(zero.possible, block_count);
        const std::size_t one_bound =
            required.missing_from(one.possible, block_count);
        const std::uint32_t first =
            zero_bound <= one_bound ? node.zero_child : node.one_child;
        const std::uint32_t second =
            zero_bound <= one_bound ? node.one_child : node.zero_child;
        return query_node(
                   first,
                   required,
                   forbidden_first,
                   forbidden_second,
                   missing_limit,
                   stats,
                   witness
               ) ||
               query_node(
                   second,
                   required,
                   forbidden_first,
                   forbidden_second,
                   missing_limit,
                   stats,
                   witness
               );
    }
};

struct FirstPair {
    std::uint16_t first = 0;
    std::uint16_t second = 0;
};

struct FirstPairReport {
    std::size_t threshold = 0;
    std::uint64_t all_pairs = 0;
    std::uint64_t checksum = fnv_offset;
    std::vector<FirstPair> eligible;
};

void hash_value(std::uint64_t& state, std::uint64_t value) {
    state ^= value;
    state *= fnv_prime;
}

[[nodiscard]] std::size_t averaging_threshold(
    std::size_t holes,
    std::size_t residual_limit
) {
    if (residual_limit >= holes) {
        return 0;
    }
    return (holes - residual_limit + 1) / 2;
}

[[nodiscard]] FirstPairReport collect_first_pairs(
    const SevenCoreInstance& instance
) {
    FirstPairReport report;
    report.threshold = averaging_threshold(
        instance.holes.size(),
        exclusion_limit
    );
    report.all_pairs = choose_two(instance.candidate_masks.size());
    for (std::size_t first = 0;
         first + 1 < instance.candidate_masks.size();
         ++first) {
        for (std::size_t second = first + 1;
             second < instance.candidate_masks.size();
             ++second) {
            const Mask coverage =
                instance.candidate_masks[first].united(
                    instance.candidate_masks[second],
                    instance.block_count
                );
            if (coverage.count(instance.block_count) < report.threshold) {
                continue;
            }
            report.eligible.push_back(FirstPair{
                static_cast<std::uint16_t>(first),
                static_cast<std::uint16_t>(second),
            });
            hash_value(report.checksum, first);
            hash_value(report.checksum, second);
            for (std::size_t block = 0;
                 block < instance.block_count;
                 ++block) {
                hash_value(report.checksum, coverage.blocks[block]);
            }
        }
    }
    return report;
}

struct FourCenterWitness {
    std::array<std::uint16_t, added_center_count> local_centers{};
};

struct WorkerOutcome {
    QueryStats stats;
    std::optional<FourCenterWitness> forbidden_completion;
    std::optional<std::string> error;
};

[[nodiscard]] std::size_t residual_for_local_centers(
    const SevenCoreInstance& instance,
    const std::array<std::uint16_t, added_center_count>& centers
) {
    Mask covered;
    for (const std::uint16_t center : centers) {
        covered.include(
            instance.candidate_masks[center],
            instance.block_count
        );
    }
    return instance.full_holes.missing_from(
        covered,
        instance.block_count
    );
}

[[nodiscard]] WorkerOutcome search_worker(
    std::size_t worker,
    std::size_t worker_count,
    const SevenCoreInstance& instance,
    const PairIndex& pair_index,
    const std::vector<FirstPair>& first_pairs
) {
    WorkerOutcome outcome;
    for (std::size_t query = worker;
         query < first_pairs.size();
         query += worker_count) {
        if (outcome.forbidden_completion.has_value()) {
            break;
        }
        ++outcome.stats.first_pairs;
        const FirstPair first = first_pairs[query];
        const Mask pair_coverage =
            instance.candidate_masks[first.first].united(
                instance.candidate_masks[first.second],
                instance.block_count
            );
        const Mask required = instance.full_holes.difference(
            pair_coverage,
            instance.block_count
        );
        PairEntry second;
        if (!pair_index.find_disjoint_cover(
                required,
                first.first,
                first.second,
                exclusion_limit,
                outcome.stats,
                &second
            )) {
            continue;
        }
        FourCenterWitness witness{{
            first.first,
            first.second,
            second.first,
            second.second,
        }};
        std::sort(
            witness.local_centers.begin(),
            witness.local_centers.end()
        );
        if (std::adjacent_find(
                witness.local_centers.begin(),
                witness.local_centers.end()
            ) != witness.local_centers.end()) {
            outcome.error =
                "pair search returned fewer than four distinct centers";
            return outcome;
        }
        if (residual_for_local_centers(
                instance,
                witness.local_centers
            ) > exclusion_limit) {
            outcome.error = "pair search returned an invalid completion";
            return outcome;
        }
        outcome.forbidden_completion = witness;
    }
    return outcome;
}

[[nodiscard]] WorkerOutcome search_all_first_pairs(
    const SevenCoreInstance& instance,
    const PairIndex& pair_index,
    const std::vector<FirstPair>& first_pairs,
    std::size_t requested_workers
) {
    const std::size_t worker_count = std::max<std::size_t>(
        1,
        std::min(
            std::min(requested_workers, maximum_workers),
            first_pairs.size()
        )
    );
    std::vector<WorkerOutcome> outcomes(worker_count);
    std::vector<std::jthread> threads;
    threads.reserve(worker_count);
    for (std::size_t worker = 0; worker < worker_count; ++worker) {
        threads.emplace_back([&, worker]() {
            try {
                outcomes[worker] = search_worker(
                    worker,
                    worker_count,
                    instance,
                    pair_index,
                    first_pairs
                );
            } catch (const std::exception& error) {
                outcomes[worker].error = error.what();
            } catch (...) {
                outcomes[worker].error =
                    "pair-search worker failed with an unknown exception";
            }
        });
    }
    for (std::jthread& thread : threads) {
        thread.join();
    }

    WorkerOutcome combined;
    for (const WorkerOutcome& outcome : outcomes) {
        combined.stats += outcome.stats;
        if (!combined.error.has_value() && outcome.error.has_value()) {
            combined.error = outcome.error;
        }
        if (!combined.forbidden_completion.has_value() &&
            outcome.forbidden_completion.has_value()) {
            combined.forbidden_completion =
                outcome.forbidden_completion;
        }
    }
    return combined;
}

[[nodiscard]] std::uint16_t local_center(
    const SevenCoreInstance& instance,
    std::size_t ambient_id
) {
    const auto iterator = std::lower_bound(
        instance.candidate_ids.begin(),
        instance.candidate_ids.end(),
        ambient_id
    );
    require(
        iterator != instance.candidate_ids.end() &&
            *iterator == ambient_id,
        "witness center is not an allowed added center"
    );
    const auto offset = iterator - instance.candidate_ids.begin();
    require(
        offset <= std::numeric_limits<std::uint16_t>::max(),
        "local center identifier does not fit in 16 bits"
    );
    return static_cast<std::uint16_t>(offset);
}

struct ExplicitWitness {
    std::array<Word, added_center_count> additions{};
    std::vector<Word> holes;
    std::size_t residual = 0;
};

[[nodiscard]] ExplicitWitness explicit_six_witness(
    const HammingSpace& space,
    const SevenCoreInstance& instance
) {
    ExplicitWitness witness;
    witness.additions[0] = instance.deleted;
    for (std::size_t index = 0; index < common_witness_tail.size(); ++index) {
        witness.additions[index + 1] = common_witness_tail[index];
    }

    std::array<std::uint16_t, added_center_count> local{};
    for (std::size_t index = 0; index < added_center_count; ++index) {
        local[index] = local_center(
            instance,
            encode(witness.additions[index])
        );
    }
    auto sorted = local;
    std::sort(sorted.begin(), sorted.end());
    require(
        std::adjacent_find(sorted.begin(), sorted.end()) == sorted.end(),
        "explicit witness does not contain four distinct centers"
    );
    witness.residual = residual_for_local_centers(instance, local);

    Mask covered;
    for (const std::uint16_t center : local) {
        covered.include(
            instance.candidate_masks[center],
            instance.block_count
        );
    }
    for (std::size_t local_point = 0;
         local_point < instance.holes.size();
         ++local_point) {
        if (!covered.test(local_point)) {
            witness.holes.push_back(
                space.words[instance.holes[local_point]]
            );
        }
    }
    require(
        witness.holes.size() == witness.residual,
        "explicit witness residual accounting disagrees"
    );
    return witness;
}

[[nodiscard]] bool pairs_are_disjoint(
    std::size_t first_a,
    std::size_t first_b,
    std::size_t second_a,
    std::size_t second_b
) {
    return first_a != second_a &&
           first_a != second_b &&
           first_b != second_a &&
           first_b != second_b;
}

[[nodiscard]] bool brute_pair_query(
    const std::vector<Mask>& masks,
    std::size_t holes,
    const Mask& required,
    std::size_t forbidden_first,
    std::size_t forbidden_second,
    std::size_t limit
) {
    const std::size_t blocks = (holes + 63) / 64;
    for (std::size_t first = 0; first + 1 < masks.size(); ++first) {
        for (std::size_t second = first + 1; second < masks.size(); ++second) {
            if (!pairs_are_disjoint(
                    forbidden_first,
                    forbidden_second,
                    first,
                    second
                )) {
                continue;
            }
            if (required.missing_from(
                    masks[first].united(masks[second], blocks),
                    blocks
                ) <= limit) {
                return true;
            }
        }
    }
    return false;
}

[[nodiscard]] std::size_t brute_four_minimum(
    const std::vector<Mask>& masks,
    std::size_t holes
) {
    const std::size_t blocks = (holes + 63) / 64;
    const Mask full = Mask::full(holes);
    std::size_t best = holes + 1;
    for (std::size_t a = 0; a + 3 < masks.size(); ++a) {
        for (std::size_t b = a + 1; b + 2 < masks.size(); ++b) {
            for (std::size_t c = b + 1; c + 1 < masks.size(); ++c) {
                for (std::size_t d = c + 1; d < masks.size(); ++d) {
                    Mask covered = masks[a].united(masks[b], blocks);
                    covered.include(masks[c], blocks);
                    covered.include(masks[d], blocks);
                    best = std::min(best, full.missing_from(covered, blocks));
                }
            }
        }
    }
    return best;
}

[[nodiscard]] bool indexed_four_decision(
    const std::vector<Mask>& masks,
    std::size_t holes,
    std::size_t limit
) {
    const std::size_t blocks = (holes + 63) / 64;
    const Mask full = Mask::full(holes);
    const std::size_t threshold = averaging_threshold(holes, limit);
    PairIndex index(masks, holes, 4);
    for (std::size_t first = 0; first + 1 < masks.size(); ++first) {
        for (std::size_t second = first + 1; second < masks.size(); ++second) {
            const Mask coverage = masks[first].united(masks[second], blocks);
            if (coverage.count(blocks) < threshold) {
                continue;
            }
            QueryStats stats;
            if (index.find_disjoint_cover(
                    full.difference(coverage, blocks),
                    static_cast<std::uint16_t>(first),
                    static_cast<std::uint16_t>(second),
                    limit,
                    stats
                )) {
                return true;
            }
        }
    }
    return false;
}

struct SelfTestReport {
    std::uint64_t index_queries = 0;
    std::uint64_t four_sets = 0;
    std::size_t synthetic_minimum = 0;
};

[[nodiscard]] SelfTestReport run_self_tests() {
    require(parse_positive("1") == 1, "self-test: worker parser rejected one");
    require(
        parse_positive("64") == maximum_workers,
        "self-test: worker parser rejected its maximum"
    );
    for (const std::string invalid : {"", "0", "-1", "65", "4x"}) {
        bool rejected = false;
        try {
            static_cast<void>(parse_positive(invalid));
        } catch (const std::exception&) {
            rejected = true;
        }
        require(rejected, "self-test: unsafe worker count was accepted");
    }

    for (std::size_t id = 0; id < word_count; ++id) {
        require(encode(decode(id)) == id, "self-test: encode/decode mismatch");
    }

    std::vector<Word> small_space;
    for (std::size_t id = 0; id < 27; ++id) {
        Word word{};
        std::size_t value = id;
        for (std::size_t position = 3; position-- > 0;) {
            word[position] = static_cast<std::uint8_t>(value % q);
            value /= q;
        }
        small_space.push_back(word);
    }
    for (const Word& center : small_space) {
        std::size_t count = 0;
        for (const Word& point : small_space) {
            std::size_t distance = 0;
            for (std::size_t coordinate = 0; coordinate < 3; ++coordinate) {
                distance += center[coordinate] != point[coordinate] ? 1U : 0U;
            }
            count += distance <= 1 ? 1U : 0U;
        }
        require(count == 7, "self-test: H(3,3) radius-one ball is not seven");
    }

    constexpr std::size_t synthetic_holes = 8;
    constexpr std::size_t synthetic_centers = 8;
    std::vector<Mask> masks(synthetic_centers);
    for (std::size_t center = 0; center < synthetic_centers; ++center) {
        for (std::size_t point = 0; point < synthetic_holes; ++point) {
            const std::size_t value =
                (center * 11 + point * 7 + center * point * 3 + point * point) %
                17;
            if (value < 9) {
                masks[center].set(point);
            }
        }
    }

    PairIndex index(masks, synthetic_holes, 4);
    SelfTestReport report;
    for (std::uint64_t required_bits = 0;
         required_bits < (std::uint64_t{1} << synthetic_holes);
         ++required_bits) {
        Mask required;
        required.blocks[0] = required_bits;
        for (std::size_t first = 0; first + 1 < synthetic_centers; ++first) {
            for (std::size_t second = first + 1;
                 second < synthetic_centers;
                 ++second) {
                for (std::size_t limit = 0; limit <= 2; ++limit) {
                    const bool direct = brute_pair_query(
                        masks,
                        synthetic_holes,
                        required,
                        first,
                        second,
                        limit
                    );
                    QueryStats stats;
                    const bool indexed = index.find_disjoint_cover(
                        required,
                        static_cast<std::uint16_t>(first),
                        static_cast<std::uint16_t>(second),
                        limit,
                        stats
                    );
                    require(
                        direct == indexed,
                        "self-test: pair index disagrees with brute force"
                    );
                    ++report.index_queries;
                }
            }
        }
    }

    report.four_sets = choose_four(synthetic_centers);
    report.synthetic_minimum = brute_four_minimum(masks, synthetic_holes);
    for (std::size_t limit = 0; limit <= synthetic_holes; ++limit) {
        const bool direct = report.synthetic_minimum <= limit;
        const bool indexed =
            indexed_four_decision(masks, synthetic_holes, limit);
        require(
            direct == indexed,
            "self-test: averaging reduction disagrees with four-set enumeration"
        );
    }

    for (const std::size_t boundary_holes :
         {63U, 64U, 65U, 127U, 128U, 129U, 517U, 518U}) {
        const Mask full = Mask::full(boundary_holes);
        const std::size_t blocks = (boundary_holes + 63) / 64;
        require(
            full.count(blocks) == boundary_holes,
            "self-test: full mask has the wrong boundary population"
        );
        for (std::size_t bit = 0; bit < boundary_holes; ++bit) {
            require(full.test(bit), "self-test: full mask misses a boundary bit");
        }
        if (boundary_holes < maximum_holes) {
            require(
                !full.test(boundary_holes),
                "self-test: full mask leaks past its boundary"
            );
        }
    }

    for (const std::size_t boundary_holes : {63U, 64U, 65U}) {
        constexpr std::size_t boundary_centers = 10;
        std::vector<Mask> boundary_masks(boundary_centers);
        for (std::size_t center = 0; center < boundary_centers; ++center) {
            for (std::size_t point = 0; point < boundary_holes; ++point) {
                if ((center * 13 + point * 17 + center * point) % 23 < 11) {
                    boundary_masks[center].set(point);
                }
            }
        }
        PairIndex boundary_index(boundary_masks, boundary_holes, 4);
        for (std::size_t sample = 0; sample < 16; ++sample) {
            Mask required;
            for (std::size_t point = 0; point < boundary_holes; ++point) {
                if ((sample * 19 + point * 7 + sample * point) % 29 < 13) {
                    required.set(point);
                }
            }
            for (std::size_t first = 0;
                 first + 1 < boundary_centers;
                 ++first) {
                for (std::size_t second = first + 1;
                     second < boundary_centers;
                     ++second) {
                    for (std::size_t limit = 0; limit <= 2; ++limit) {
                        const bool direct = brute_pair_query(
                            boundary_masks,
                            boundary_holes,
                            required,
                            first,
                            second,
                            limit
                        );
                        QueryStats stats;
                        const bool indexed = boundary_index.find_disjoint_cover(
                            required,
                            static_cast<std::uint16_t>(first),
                            static_cast<std::uint16_t>(second),
                            limit,
                            stats
                        );
                        require(
                            direct == indexed,
                            "self-test: boundary pair query mismatch"
                        );
                        ++report.index_queries;
                    }
                }
            }
        }
    }

    constexpr std::size_t boundary_four_holes = 65;
    constexpr std::size_t boundary_four_centers = 8;
    std::vector<Mask> boundary_four_masks(boundary_four_centers);
    for (std::size_t center = 0; center < boundary_four_centers; ++center) {
        for (std::size_t point = 0; point < boundary_four_holes; ++point) {
            if ((center * 31 + point * 11 + center * point) % 37 < 18) {
                boundary_four_masks[center].set(point);
            }
        }
    }
    const std::size_t boundary_minimum =
        brute_four_minimum(boundary_four_masks, boundary_four_holes);
    for (std::size_t limit = 0; limit <= boundary_four_holes; ++limit) {
        require(
            indexed_four_decision(
                boundary_four_masks,
                boundary_four_holes,
                limit
            ) == (boundary_minimum <= limit),
            "self-test: boundary four-center decision mismatch"
        );
    }
    report.four_sets += choose_four(boundary_four_centers);
    return report;
}

struct RepresentativeReport {
    Word representative{};
    std::vector<Word> orbit_members;
    std::size_t seven_core_holes = 0;
    std::size_t candidate_centers = 0;
    std::uint64_t unordered_pairs = 0;
    std::size_t first_pair_threshold = 0;
    std::size_t eligible_first_pairs = 0;
    std::uint64_t first_pair_checksum = 0;
    std::size_t pair_tree_nodes = 0;
    std::size_t pair_tree_leaves = 0;
    QueryStats query_stats;
    ExplicitWitness witness;
    double instance_seconds = 0.0;
    double index_seconds = 0.0;
    double query_seconds = 0.0;
    double total_seconds = 0.0;
};

[[nodiscard]] RepresentativeReport verify_representative(
    const HammingSpace& space,
    const DeletionOrbit& orbit,
    std::size_t workers
) {
    Timer total_timer;
    Timer instance_timer;
    SevenCoreInstance instance = build_instance(
        space,
        orbit.representative_index
    );
    const double instance_seconds = instance_timer.seconds();
    const ExplicitWitness witness = explicit_six_witness(space, instance);
    require(
        witness.residual == expected_minimum,
        "explicit four-center witness does not leave exactly six holes"
    );

    Timer index_timer;
    PairIndex pair_index(instance.candidate_masks, instance.holes.size());
    const FirstPairReport first_pairs = collect_first_pairs(instance);
    const double index_seconds = index_timer.seconds();
    require(
        pair_index.entries.size() == first_pairs.all_pairs,
        "pair index and first-pair scan have different accounting"
    );

    Timer query_timer;
    const WorkerOutcome outcome = search_all_first_pairs(
        instance,
        pair_index,
        first_pairs.eligible,
        workers
    );
    const double query_seconds = query_timer.seconds();
    require(
        !outcome.error.has_value(),
        outcome.error.has_value()
            ? "pair-search worker failed: " + *outcome.error
            : "pair-search worker failed"
    );
    require(
        !outcome.forbidden_completion.has_value(),
        "found four distinct added centers leaving at most five holes"
    );
    require(
        outcome.stats.first_pairs == first_pairs.eligible.size(),
        "not every eligible first pair was queried"
    );

    RepresentativeReport report;
    report.representative = core[orbit.representative_index];
    for (const std::size_t member : orbit.members) {
        report.orbit_members.push_back(core[member]);
    }
    report.seven_core_holes = instance.holes.size();
    report.candidate_centers = instance.candidate_ids.size();
    report.unordered_pairs = first_pairs.all_pairs;
    report.first_pair_threshold = first_pairs.threshold;
    report.eligible_first_pairs = first_pairs.eligible.size();
    report.first_pair_checksum = first_pairs.checksum;
    report.pair_tree_nodes = pair_index.nodes.size();
    report.pair_tree_leaves = static_cast<std::size_t>(
        std::count_if(
            pair_index.nodes.begin(),
            pair_index.nodes.end(),
            [](const TreeNode& node) {
                return node.leaf;
            }
        )
    );
    report.query_stats = outcome.stats;
    report.witness = witness;
    report.instance_seconds = instance_seconds;
    report.index_seconds = index_seconds;
    report.query_seconds = query_seconds;
    report.total_seconds = total_timer.seconds();
    return report;
}

struct Config {
    std::size_t workers = 1;
    bool self_test_only = false;
};

[[nodiscard]] Config parse_config(int argc, char** argv) {
    Config config;
    config.workers = std::max<std::size_t>(
        1,
        std::min<std::size_t>(
            std::thread::hardware_concurrency() == 0
                ? 1
                : std::thread::hardware_concurrency(),
            8
        )
    );
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--self-test-only") {
            config.self_test_only = true;
        } else if (argument == "--workers") {
            require(index + 1 < argc, "--workers requires a value");
            config.workers = parse_positive(argv[++index]);
        } else if (argument.rfind("--workers=", 0) == 0) {
            config.workers = parse_positive(argument.substr(10));
        } else if (argument == "--help" || argument == "-h") {
            std::cout
                << "usage: seven_core_independent [--workers N], "
                   "1 <= N <= 64 "
                   "[--self-test-only]\n";
            std::exit(0);
        } else {
            fail("unknown argument: " + argument);
        }
    }
    return config;
}

void print_representative(const RepresentativeReport& report) {
    std::cout << '\n';
    std::cout << "representative=" << format_word(report.representative) << '\n';
    std::cout << "orbit_size=" << report.orbit_members.size() << '\n';
    std::cout << "orbit_members=" << join_words(report.orbit_members) << '\n';
    std::cout << "seven_core_holes=" << report.seven_core_holes << '\n';
    std::cout << "candidate_centers=" << report.candidate_centers << '\n';
    std::cout << "unordered_candidate_pairs=" << report.unordered_pairs << '\n';
    std::cout << "excluded_residual_range=0..5\n";
    std::cout << "first_pair_averaging_threshold="
              << report.first_pair_threshold << '\n';
    std::cout << "eligible_first_pairs="
              << report.eligible_first_pairs << '\n';
    std::cout << "eligible_first_pair_checksum=0x"
              << std::hex << std::setw(16) << std::setfill('0')
              << report.first_pair_checksum << std::dec
              << std::setfill(' ') << '\n';
    std::cout << "pair_tree_nodes=" << report.pair_tree_nodes << '\n';
    std::cout << "pair_tree_leaves=" << report.pair_tree_leaves << '\n';
    std::cout << "queried_first_pairs="
              << report.query_stats.first_pairs << '\n';
    std::cout << "tree_nodes_visited="
              << report.query_stats.tree_nodes << '\n';
    std::cout << "tree_nodes_pruned="
              << report.query_stats.pruned_nodes << '\n';
    std::cout << "leaf_pair_masks_checked="
              << report.query_stats.leaf_pair_masks << '\n';
    std::cout << "overlap_rejections="
              << report.query_stats.overlap_rejections << '\n';
    std::cout << "completion_with_residual_at_most_5=none\n";
    std::cout << "minimum_residual=" << expected_minimum << '\n';
    std::cout << "witness_additions="
              << join_words(report.witness.additions) << '\n';
    std::cout << "witness_holes="
              << join_words(report.witness.holes) << '\n';
    std::cout << "instance_seconds=" << std::fixed << std::setprecision(3)
              << report.instance_seconds << '\n';
    std::cout << "index_seconds=" << report.index_seconds << '\n';
    std::cout << "query_seconds=" << report.query_seconds << '\n';
    std::cout << "representative_seconds=" << report.total_seconds << '\n';
}

int run(const Config& config) {
    Timer total_timer;
    const SelfTestReport self_tests = run_self_tests();
    std::cout << "INDEPENDENT C++20 SEVEN-CORE VERIFIER\n";
    std::cout << "self_tests=passed\n";
    std::cout << "self_test_pair_queries=" << self_tests.index_queries << '\n';
    std::cout << "self_test_four_sets=" << self_tests.four_sets << '\n';
    std::cout << "self_test_four_center_minimum="
              << self_tests.synthetic_minimum << '\n';
    if (config.self_test_only) {
        std::cout << "total_seconds=" << std::fixed << std::setprecision(3)
                  << total_timer.seconds() << '\n';
        return 0;
    }

    HammingSpace space;
    space.verify_geometry();
    const std::vector<Transform> stabilizer = enumerate_core_stabilizer();
    const std::vector<DeletionOrbit> orbits = deletion_orbits(stabilizer);
    require(
        orbits.size() == expected_orbit_count,
        "the core deletions do not form exactly four stabilizer orbits"
    );
    const std::size_t orbit_coverage = std::accumulate(
        orbits.begin(),
        orbits.end(),
        std::size_t{0},
        [](std::size_t total, const DeletionOrbit& orbit) {
            return total + orbit.members.size();
        }
    );
    require(
        orbit_coverage == core_size,
        "the four deletion orbits do not cover all eight deletions"
    );

    std::cout << "space=H(7,3)\n";
    std::cout << "ambient_words=" << space.words.size() << '\n';
    std::cout << "radius=" << radius << '\n';
    std::cout << "ball_size=" << ball_size << '\n';
    std::cout << "core=" << join_words(core) << '\n';
    std::cout << "core_stabilizer_maps=" << stabilizer.size() << '\n';
    std::cout << "core_action_group_size="
              << unique_action_count(stabilizer) << '\n';
    std::cout << "deletion_orbit_count=" << orbits.size() << '\n';
    std::cout << "deletion_orbit_coverage=" << orbit_coverage << '\n';
    std::cout << "workers=" << config.workers << '\n';
    std::cout << "search_method=disjoint_pair_meet_in_the_middle\n";
    std::cout
        << "safe_pruning=pair_tree_subtree_union_upper_bounds\n";
    std::cout
        << "averaging_rule=one_of_six_pairs_covers_at_least_half_of_all_covered_holes\n";
#if defined(__clang__)
    std::cout << "compiler=" << __clang_version__ << '\n';
#elif defined(__GNUC__)
    std::cout << "compiler=" << __VERSION__ << '\n';
#else
    std::cout << "compiler=unknown\n";
#endif
    std::cout
        << "recommended_flags=-std=c++20 -O3 -DNDEBUG -pthread "
           "-Wall -Wextra -Wpedantic -Wconversion -Wshadow -march=native\n";

    std::vector<RepresentativeReport> reports;
    reports.reserve(orbits.size());
    for (const DeletionOrbit& orbit : orbits) {
        reports.push_back(
            verify_representative(space, orbit, config.workers)
        );
    }
    for (const RepresentativeReport& report : reports) {
        require(
            report.witness.residual == expected_minimum,
            "a representative does not have minimum residual six"
        );
        print_representative(report);
    }

    const std::uint64_t total_pair_entries = std::accumulate(
        reports.begin(),
        reports.end(),
        std::uint64_t{0},
        [](std::uint64_t total, const RepresentativeReport& report) {
            return total + report.unordered_pairs;
        }
    );
    const std::uint64_t total_queries = std::accumulate(
        reports.begin(),
        reports.end(),
        std::uint64_t{0},
        [](std::uint64_t total, const RepresentativeReport& report) {
            return total + report.query_stats.first_pairs;
        }
    );
    std::cout << '\n';
    std::cout << "VERIFIED CONCLUSION\n";
    std::cout << "representatives_verified=" << reports.size() << '\n';
    std::cout << "deletions_covered_by_orbits=" << orbit_coverage << '\n';
    std::cout << "total_pair_entries_built=" << total_pair_entries << '\n';
    std::cout << "total_eligible_first_pairs_queried="
              << total_queries << '\n';
    std::cout
        << "all_four_representative_minima=6\n";
    std::cout
        << "scope=the_eight_seven_word_subcores_and_their_isometric_copies\n";
    std::cout << "total_seconds=" << std::fixed << std::setprecision(3)
              << total_timer.seconds() << '\n';
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        return run(parse_config(argc, argv));
    } catch (const std::exception& error) {
        std::cerr << "verification_error=" << error.what() << '\n';
        return 1;
    }
}
