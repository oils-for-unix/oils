/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file CacheUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include <array>
#include <fstream>

// -------------------------------------------------------------------------------
//                              Hint / Cache
// -------------------------------------------------------------------------------

namespace souffle {

/**
 * An Least-Recently-Used cache for arbitrary element types. Elements can be signaled
 * to be accessed and iterated through in their LRU order.
 */
template <typename T, unsigned size = 1>
class LRUCache {
    // the list of pointers maintained
    std::array<T, size> entries;

    // pointer to predecessor / successor in the entries list
    std::array<std::size_t, size> priv;  // < predecessor of element i
    std::array<std::size_t, size> post;  // < successor of element i

    std::size_t first{0};        // < index of the first element
    std::size_t last{size - 1};  // < index of the last element

public:
    // creates a new, empty cache
    LRUCache(const T& val = T()) {
        for (unsigned i = 0; i < size; i++) {
            entries[i] = val;
            priv[i] = i - 1;
            post[i] = i + 1;
        }
        priv[first] = last;
        post[last] = first;
    }

    // clears the content of this cache
    void clear(const T& val = T()) {
        for (auto& cur : entries) {
            cur = val;
        }
    }

    // registers an access to the given element
    void access(const T& val) {
        // test whether it is contained
        for (std::size_t i = 0; i < size; i++) {
            if (entries[i] != val) {
                continue;
            }

            // -- move this one to the front --

            // if it is the first, nothing to handle
            if (i == first) {
                return;
            }

            // if this is the last, just first and last need to change
            if (i == last) {
                auto tmp = last;
                last = priv[last];
                first = tmp;
                return;
            }

            // otherwise we need to update the linked list

            // remove from current position
            post[priv[i]] = post[i];
            priv[post[i]] = priv[i];

            // insert in first position
            post[i] = first;
            priv[i] = last;
            priv[first] = i;
            post[last] = i;

            // update first pointer
            first = i;
            return;
        }
        // not present => drop last, make it first
        entries[last] = val;
        auto tmp = last;
        last = priv[last];
        first = tmp;
    }

    /**
     * Iterates over the elements within this cache in LRU order.
     * The operator is applied on each element. If the operation
     * returns false, iteration is continued. If the operator return
     * true, iteration is stopped -- similar to the any operator.
     *
     * @param op the operator to be applied on every element
     * @return true if op returned true for any entry, false otherwise
     */
    template <typename Op>
    bool forEachInOrder(const Op& op) const {
        std::size_t i = first;
        while (i != last) {
            if (op(entries[i])) return true;
            i = post[i];
        }
        return op(entries[i]);
    }

    // equivalent to forEachInOrder
    template <typename Op>
    bool any(const Op& op) const {
        return forEachInOrder(op);
    }
};

template <typename T, unsigned size>
std::ostream& operator<<(std::ostream& out, const LRUCache<T, size>& cache) {
    bool first = true;
    cache.forEachInOrder([&](const T& val) {
        if (!first) {
            out << ",";
        }
        first = false;
        out << val;
        return false;
    });
    return out;
}

// a specialization for a single-entry cache
template <typename T>
class LRUCache<T, 1> {
    // the single entry in this cache
    T entry;

public:
    // creates a new, empty cache
    LRUCache() : entry() {}

    // creates a new, empty cache storing the given value
    LRUCache(const T& val) : entry(val) {}

    // clears the content of this cache
    void clear(const T& val = T()) {
        entry = val;
    }

    // registers an access to the given element
    void access(const T& val) {
        entry = val;
    }

    /**
     * See description in most general case.
     */
    template <typename Op>
    bool forEachInOrder(const Op& op) const {
        return op(entry);
    }

    // equivalent to forEachInOrder
    template <typename Op>
    bool any(const Op& op) const {
        return forEachInOrder(op);
    }

    // --- print support ---

    friend std::ostream& operator<<(std::ostream& out, const LRUCache& cache) {
        return out << cache.entry;
    }
};

// a specialization for no-entry caches.
template <typename T>
class LRUCache<T, 0> {
public:
    // creates a new, empty cache
    LRUCache(const T& = T()) {}

    // clears the content of this cache
    void clear(const T& = T()) {
        // nothing to do
    }

    // registers an access to the given element
    void access(const T&) {
        // nothing to do
    }

    /**
     * Always returns false.
     */
    template <typename Op>
    bool forEachInOrder(const Op&) const {
        return false;
    }

    // equivalent to forEachInOrder
    template <typename Op>
    bool any(const Op& op) const {
        return forEachInOrder(op);
    }

    // --- print support ---

    friend std::ostream& operator<<(std::ostream& out, const LRUCache& /* cache */) {
        return out << "-empty-";
    }
};

// -------------------------------------------------------------------------------
//                           Hint / Cache Profiling
// -------------------------------------------------------------------------------

/**
 * cache hits/misses.
 */
#ifdef _SOUFFLE_STATS

#include <atomic>

class CacheAccessCounter {
    std::atomic<std::size_t> hits;
    std::atomic<std::size_t> misses;

public:
    CacheAccessCounter() : hits(0), misses(0) {}
    CacheAccessCounter(const CacheAccessCounter& other) : hits(other.getHits()), misses(other.getMisses()) {}
    void addHit() {
        hits.fetch_add(1, std::memory_order_relaxed);
    }
    void addMiss() {
        misses.fetch_add(1, std::memory_order_relaxed);
    }
    std::size_t getHits() const {
        return hits;
    }
    std::size_t getMisses() const {
        return misses;
    }
    std::size_t getAccesses() const {
        return getHits() + getMisses();
    }
    void reset() {
        hits = 0;
        misses = 0;
    }
};

#else

class CacheAccessCounter {
public:
    CacheAccessCounter() = default;
    CacheAccessCounter(const CacheAccessCounter& /* other */) = default;
    inline void addHit() {}
    inline void addMiss() {}
    inline std::size_t getHits() {
        return 0;
    }
    inline std::size_t getMisses() {
        return 0;
    }
    inline std::size_t getAccesses() {
        return 0;
    }
    inline void reset() {}
};

#endif
}  // end namespace souffle
