/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */
#pragma once

#include "ConcurrentInsertOnlyHashMap.h"
#include "souffle/utility/ParallelUtil.h"

namespace souffle {
/**
 * A simple implementation of a cache that can be used during interation and compilation
 * to store frequently used values or values that are expensive to compute (e.g., regex).
 */
template <class Key, class Value, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
struct ConcurrentCache {
#ifdef _OPENMP
    using CacheImpl = ConcurrentInsertOnlyHashMap<ConcurrentLanes, Key, Value, Hash, KeyEqual, KeyFactory>;
#else
    using CacheImpl = ConcurrentInsertOnlyHashMap<SeqConcurrentLanes, Key, Value, Hash, KeyEqual, KeyFactory>;
#endif

    ConcurrentCache(const std::size_t LaneCount = 1) : lanes(LaneCount), cache(LaneCount, 8) {}
    ~ConcurrentCache() = default;

    void setNumLanes(const std::size_t NumLanes) {
        lanes.setNumLanes(NumLanes);
        cache.setNumLanes(NumLanes);
    }

    /**
     * @brief Lookup the specified key in the cache.
     *
     * If the key is in the cache, then the associated value is returned. Otherwise,
     * if the key, is not in the cache, the supplied function is invoked to construct
     * the value from the key.
     *
     * The cache is not modified if the constructor function throws an exception.
     * @param key the key for caching
     * @param constructor a functor that takes a key and produces a value
     * @return the cached value that is associated with the key
     */
    template <class CTOR>
    const Value& getOrCreate(const Key& key, const CTOR& constructor) {
        typename CacheImpl::lane_id lane = lanes.threadLane();
        auto entry = cache.weakFind(lane, key);
        if (entry == nullptr) {
            auto node = cache.node(constructor(key));
            auto result = cache.get(lane, node, key);
            if (!result.second) {
                // we need to delete the temporary node, since someone else
                // already created the same node concurrently
                delete node;
            }
            entry = result.first;
        }
        return entry->second;
    }

    /**
     * @brief Lookup the value associated with the specified key.
     *
     * If the key does not exist, constructs a value using
     * the key.
     *
     * This function forwards to getOrCreate
     * @param key the key to lookup
     * @return the cached value that is associated with the key
     */
    inline const Value& getOrCreate(const Key& key) {
        return getOrCreate(key, [](auto p) { return Value(p); });
    }

    ConcurrentLanes lanes;

    CacheImpl cache;
};

}  // namespace souffle
