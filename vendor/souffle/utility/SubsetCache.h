/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SubsetCache.h
 *
 * Data structure for efficiently generating subsets without recomputation
 *
 ***********************************************************************/

#pragma once

namespace souffle {

class SubsetCache {
public:
    using PowerSet = std::set<std::vector<std::size_t>>;

    const PowerSet& getSubsets(std::size_t N, std::size_t K) const {
        if (cache.count({N, K})) {
            return cache.at({N, K});
        }

        PowerSet res;

        // generate the next permutation of the bitmask
        std::vector<std::size_t> cur;
        cur.reserve(K);

        // use bitmask for subset generation
        std::string bitmask(K, 1);  // K leading 1's
        bitmask.resize(N, 0);       // N-K trailing 0's

        // generate the combination while there are combinations to go
        do {
            cur.clear();

            // construct the subset using the set bits in the bitmask
            for (std::size_t i = 0; i < N; ++i)  // [0..N-1] integers
            {
                if (bitmask[i]) {
                    cur.push_back(i);
                }
            }
            res.insert(cur);
        } while (std::prev_permutation(bitmask.begin(), bitmask.end()));
        cache[std::make_pair(N, K)] = res;
        return cache.at({N, K});
    }

private:
    mutable std::map<std::pair<std::size_t, std::size_t>, PowerSet> cache;
};

}  // namespace souffle
