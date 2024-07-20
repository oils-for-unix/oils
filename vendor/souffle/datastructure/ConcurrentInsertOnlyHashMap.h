/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */
#pragma once

#include "souffle/utility/ParallelUtil.h"

#include <array>
#include <atomic>
#include <cassert>
#include <cmath>
#include <memory>
#include <mutex>
#include <vector>

namespace souffle {
namespace details {

static const std::vector<std::pair<unsigned, unsigned>> ToPrime = {
        // https://primes.utm.edu/lists/2small/0bit.html
        // ((2^n) - k) is prime
        // {n, k}
        {4, 3},  // 2^4 - 3 = 13
        {8, 5},  // 8^5 - 5 = 251
        {9, 3}, {10, 3}, {11, 9}, {12, 3}, {13, 1}, {14, 3}, {15, 19}, {16, 15}, {17, 1}, {18, 5}, {19, 1},
        {20, 3}, {21, 9}, {22, 3}, {23, 15}, {24, 3}, {25, 39}, {26, 5}, {27, 39}, {28, 57}, {29, 3},
        {30, 35}, {31, 1}, {32, 5}, {33, 9}, {34, 41}, {35, 31}, {36, 5}, {37, 25}, {38, 45}, {39, 7},
        {40, 87}, {41, 21}, {42, 11}, {43, 57}, {44, 17}, {45, 55}, {46, 21}, {47, 115}, {48, 59}, {49, 81},
        {50, 27}, {51, 129}, {52, 47}, {53, 111}, {54, 33}, {55, 55}, {56, 5}, {57, 13}, {58, 27}, {59, 55},
        {60, 93}, {61, 1}, {62, 57}, {63, 25}};

// (2^64)-59 is the largest prime that fits in uint64_t
static constexpr uint64_t LargestPrime64 = 18446744073709551557UL;

// Return a prime greater or equal to the lower bound.
// Return 0 if the next prime would not fit in 64 bits.
inline static uint64_t GreaterOrEqualPrime(const uint64_t LowerBound) {
    if (LowerBound > LargestPrime64) {
        return 0;
    }

    for (std::size_t I = 0; I < ToPrime.size(); ++I) {
        const uint64_t N = ToPrime[I].first;
        const uint64_t K = ToPrime[I].second;
        const uint64_t Prime = (1ULL << N) - K;
        if (Prime >= LowerBound) {
            return Prime;
        }
    }
    return LargestPrime64;
}

template <typename T>
struct Factory {
    template <class... Args>
    T& replace(T& Place, Args&&... Xs) {
        Place = T{std::forward<Args>(Xs)...};
        return Place;
    }
};

}  // namespace details

/**
 * A concurrent, almost lock-free associative hash-map that can only grow.
 * Elements cannot be removed, the hash-map can only grow.
 *
 * The datastructures enables a configurable number of concurrent access lanes.
 * Access to the datastructure is lock-free between different lanes.
 * Concurrent accesses through the same lane is sequential.
 *
 * Growing the datastructure requires to temporarily lock all lanes to let a
 * single lane perform the growing operation. The global lock is amortized
 * thanks to an exponential growth strategy.
 */
template <class LanesPolicy, class Key, class T, class Hash = std::hash<Key>,
        class KeyEqual = std::equal_to<Key>, class KeyFactory = details::Factory<Key>>
class ConcurrentInsertOnlyHashMap {
public:
    class Node;

    using key_type = Key;
    using mapped_type = T;
    using node_type = Node*;
    using value_type = std::pair<const Key, const T>;
    using size_type = std::size_t;
    using hasher = Hash;
    using key_equal = KeyEqual;
    using self_type = ConcurrentInsertOnlyHashMap<Key, T, Hash, KeyEqual, KeyFactory>;
    using lane_id = typename LanesPolicy::lane_id;

    class Node {
    public:
        virtual ~Node() {}
        virtual const value_type& value() const = 0;
        virtual const key_type& key() const = 0;
        virtual const mapped_type& mapped() const = 0;
    };

private:
    // Each bucket of the hash-map is a linked list.
    struct BucketList : Node {
        virtual ~BucketList() {}

        BucketList(const Key& K, const T& V, BucketList* N) : Value(K, V), Next(N) {}

        const value_type& value() const {
            return Value;
        }

        const key_type& key() const {
            return Value.first;
        }

        const mapped_type& mapped() const {
            return Value.second;
        }

        // Stores the couple of a key and its associated value.
        value_type Value;

        // Points to next element of the map that falls into the same bucket.
        BucketList* Next;
    };

public:
    /**
     * @brief Construct a hash-map with at least the given number of buckets.
     *
     * Load-factor is initialized to 1.0.
     */
    ConcurrentInsertOnlyHashMap(const std::size_t LaneCount, const std::size_t Bucket_Count,
            const Hash& hash = Hash(), const KeyEqual& key_equal = KeyEqual(),
            const KeyFactory& key_factory = KeyFactory())
            : Lanes(LaneCount), Hasher(hash), EqualTo(key_equal), Factory(key_factory) {
        Size = 0;
        BucketCount = details::GreaterOrEqualPrime(Bucket_Count);
        if (BucketCount == 0) {
            // Hopefuly this number of buckets is never reached.
            BucketCount = std::numeric_limits<std::size_t>::max();
        }
        LoadFactor = 1.0;
        Buckets = std::make_unique<std::atomic<BucketList*>[]>(BucketCount);
        MaxSizeBeforeGrow = static_cast<std::size_t>(std::ceil(LoadFactor * (double)BucketCount));
    }

    ConcurrentInsertOnlyHashMap(const Hash& hash = Hash(), const KeyEqual& key_equal = KeyEqual(),
            const KeyFactory& key_factory = KeyFactory())
            : ConcurrentInsertOnlyHashMap(8, hash, key_equal, key_factory) {}

    ~ConcurrentInsertOnlyHashMap() {
        for (std::size_t Bucket = 0; Bucket < BucketCount; ++Bucket) {
            BucketList* L = Buckets[Bucket].load(std::memory_order_relaxed);
            while (L != nullptr) {
                BucketList* BL = L;
                L = L->Next;
                delete (BL);
            }
        }
    }

    void setNumLanes(const std::size_t NumLanes) {
        Lanes.setNumLanes(NumLanes);
    }

    /** @brief Create a fresh node initialized with the given value and a
     * default-constructed key.
     *
     * The ownership of the returned node given to the caller.
     */
    node_type node(const T& V) {
        BucketList* BL = new BucketList(Key{}, V, nullptr);
        return static_cast<node_type>(BL);
    }

    /**
     * @brief Lookup a value associated with a key.
     *
     * The search is done concurrently with possible insertion of the
     * searched key. If the a nullpointer is returned, then the key
     * was not associated with a value when the search began.
     */
    template <class K>
    const value_type* weakFind(const lane_id H, const K& X) const {
        const size_t HashValue = Hasher(X);
        const auto Guard = Lanes.guard(H);
        const size_t Bucket = HashValue % BucketCount;

        BucketList* L = Buckets[Bucket].load(std::memory_order_acquire);
        while (L != nullptr) {
            if (EqualTo(L->Value.first, X)) {
                // found the key
                return &L->Value;
            }
            L = L->Next;
        }
        return nullptr;
    }

    /** @brief Checks if the map contains an element with the given key.
     *
     * The search is done concurrently with possible insertion of the
     * searched key. If return true, then there is definitely an element
     * with the specified key, if return false then there was no such
     * element when the search began.
     */
    template <class K>
    inline bool weakContains(const lane_id H, const K& X) const {
        return weakFind(H, X) != nullptr;
    }

    /**
     * @brief Inserts in-place if the key is not mapped, does nothing if the key already exists.
     *
     * @param H is the access lane.
     *
     * @param N is a node initialized with the mapped value to insert.
     *
     * @param Xs are arguments to forward to the hasher, the comparator and and
     * the constructor of the key.
     *
     *
     * Be Careful: the inserted node becomes available to concurrent lanes as
     * soon as it is inserted, thus concurrent lanes may access the inserted
     * value even before the inserting lane returns from this function.
     * This is the reason why the inserting lane must prepare the inserted
     * node's mapped value prior to calling this function.
     *
     * Be Careful: the given node remains the ownership of the caller unless
     * the returned couple second member is true.
     *
     * Be Careful: the given node may not be inserted if the key already
     * exists.  The caller is in charge of handling that case and either
     * dispose of the node or save it for the next insertion operation.
     *
     * Be Careful: Once the given node is actually inserted, its ownership is
     * transfered to the hash-map. However it remains valid.
     *
     * If the key that compares equal to arguments Xs exists, then nothing is
     * inserted. The returned value is the couple of the pointer to the
     * existing value and the false boolean value.
     *
     * If the key that compares equal to arguments Xs does not exist, then the
     * node N is updated with the key constructed from Xs, and inserted in the
     * hash-map. The returned value is the couple of the pointer to the
     * inserted value and the true boolean value.
     *
     */
    template <class... Args>
    std::pair<const value_type*, bool> get(const lane_id H, const node_type N, Args&&... Xs) {
        // At any time a concurrent lane may insert the key before this lane.
        //
        // The synchronisation point is the atomic compare-and-exchange of the
        // head of the bucket list that must contain the inserted node.
        //
        // The insertion algorithm is as follow:
        //
        // 1) Compute the key hash from Xs.
        //
        // 2) Lock the lane, that also prevent concurrent lanes from growing of
        // the datastructure.
        //
        // 3) Determine the bucket where the element must be inserted.
        //
        // 4) Read the "last known head" of the bucket list. Other lanes
        // inserting in the same bucket may update the bucket head
        // concurrently.
        //
        // 5) Search the bucket list for the key by comparing with Xs starting
        // from the last known head. If it is not the first round of search,
        // then stop searching where the previous round of search started.
        //
        // 6) If the key is found return the couple of the value pointer and
        // false (to indicate that this lane did not insert the node N).
        //
        // 7) It the key is not found prepare N for insertion by updating its
        // key with Xs and chaining the last known head.
        //
        // 8) Try to exchange to last known head with N at the bucket head. The
        // atomic compare and exchange operation guarantees that it only
        // succeed if not other node was inserted in the bucket since we
        // searched it, otherwise it fails when another lane has concurrently
        // inserted a node in the same bucket.
        //
        // 9) If the atomic compare and exchange succeeded, the node has just
        // been inserted by this lane. From now-on other lanes can also see
        // the node. Return the couple of a pointer to the inserted value and
        // the true boolean.
        //
        // 10) If the atomic compare and exchange failed, another node has been
        // inserted by a concurrent lane in the same bucket. A new round of
        // search is required -> restart from step 4.
        //
        //
        // The datastructure is optionaly grown after step 9) before returning.

        const value_type* Value = nullptr;
        bool Inserted = false;

        size_t NewSize;

        // 1)
        const size_t HashValue = Hasher(std::forward<Args>(Xs)...);

        // 2)
        Lanes.lock(H);  // prevent the datastructure from growing

        // 3)
        const size_t Bucket = HashValue % BucketCount;

        // 4)
        // the head of the bucket's list last time we checked
        BucketList* LastKnownHead = Buckets[Bucket].load(std::memory_order_acquire);
        // the head of the bucket's list we already searched from
        BucketList* SearchedFrom = nullptr;
        // the node we want to insert
        BucketList* const Node = static_cast<BucketList*>(N);

        // Loop until either the node is inserted or the key is found in the bucket.
        // Assuming bucket collisions are rare this loop is not executed more than once.
        while (true) {
            // 5)
            // search the key in the bucket, stop where we already search at a
            // previous iteration.
            BucketList* L = LastKnownHead;
            while (L != SearchedFrom) {
                if (EqualTo(L->Value.first, std::forward<Args>(Xs)...)) {
                    // 6)
                    // Found the key, no need to insert.
                    // Although it's not strictly necessary, clear the node
                    // chaining to avoid leaving a dangling pointer there.
                    Value = &(L->Value);
                    Node->Next = nullptr;
                    goto Done;
                }
                L = L->Next;
            }
            SearchedFrom = LastKnownHead;

            // 7)
            // Not found in bucket, prepare node chaining.
            Node->Next = LastKnownHead;
            // The factory step could be done only once, but assuming bucket collisions are
            // rare this whole loop is not executed more than once.
            Factory.replace(const_cast<key_type&>(Node->Value.first), std::forward<Args>(Xs)...);

            // 8)
            // Try to insert the key in front of the bucket's list.
            // This operation also performs step 4) because LastKnownHead is
            // updated in the process.
            if (Buckets[Bucket].compare_exchange_strong(
                        LastKnownHead, Node, std::memory_order_release, std::memory_order_relaxed)) {
                // 9)
                Inserted = true;
                NewSize = ++Size;
                Value = &(Node->Value);
                goto AfterInserted;
            }

            // 10) concurrent insertion detected in this bucket, new round required.
        }

    AfterInserted : {
        if (NewSize > MaxSizeBeforeGrow) {
            tryGrow(H);
        }
    }

    Done:

        Lanes.unlock(H);

        // 6,9)
        return std::make_pair(Value, Inserted);
    }

private:
    // The concurrent lanes manager.
    LanesPolicy Lanes;

    /// Hash function.
    Hash Hasher;

    /// Current number of buckets.
    std::size_t BucketCount;

    /// Atomic pointer to head bucket linked-list head.
    std::unique_ptr<std::atomic<BucketList*>[]> Buckets;

    /// The Equal-to function.
    KeyEqual EqualTo;

    KeyFactory Factory;

    /// Current number of elements stored in the map.
    std::atomic<std::size_t> Size;

    /// Maximum size before the map should grow.
    std::size_t MaxSizeBeforeGrow;

    /// The load-factor of the map.
    double LoadFactor;

    // Grow the datastructure.
    // Must be called while owning lane H.
    bool tryGrow(const lane_id H) {
        Lanes.beforeLockAllBut(H);

        if (Size <= MaxSizeBeforeGrow) {
            // Current size is fine
            Lanes.beforeUnlockAllBut(H);
            return false;
        }

        Lanes.lockAllBut(H);

        {  // safe section

            // Compute the new number of buckets:
            // Chose a prime number of buckets that ensures the desired load factor
            // given the current number of elements in the map.
            const std::size_t CurrentSize = Size;
            assert(LoadFactor > 0);
            const std::size_t NeededBucketCount =
                    static_cast<std::size_t>(std::ceil(static_cast<double>(CurrentSize) / LoadFactor));
            std::size_t NewBucketCount = NeededBucketCount;
            for (std::size_t I = 0; I < details::ToPrime.size(); ++I) {
                const uint64_t N = details::ToPrime[I].first;
                const uint64_t K = details::ToPrime[I].second;
                const uint64_t Prime = (1ULL << N) - K;
                if (Prime >= NeededBucketCount) {
                    NewBucketCount = Prime;
                    break;
                }
            }

            std::unique_ptr<std::atomic<BucketList*>[]> NewBuckets =
                    std::make_unique<std::atomic<BucketList*>[]>(NewBucketCount);

            // Rehash, this operation is costly because it requires to scan
            // the existing elements, compute its hash to find its new bucket
            // and insert in the new bucket.
            //
            // Maybe concurrent lanes could help using some job-stealing algorithm.
            //
            // Use relaxed memory ordering since the whole operation takes place
            // in a critical section.
            for (std::size_t B = 0; B < BucketCount; ++B) {
                BucketList* L = Buckets[B].load(std::memory_order_relaxed);
                while (L) {
                    BucketList* const Elem = L;
                    L = L->Next;

                    const auto& Value = Elem->Value;
                    std::size_t NewHash = Hasher(Value.first);
                    const std::size_t NewBucket = NewHash % NewBucketCount;
                    Elem->Next = NewBuckets[NewBucket].load(std::memory_order_relaxed);
                    NewBuckets[NewBucket].store(Elem, std::memory_order_relaxed);
                }
            }

            Buckets = std::move(NewBuckets);
            BucketCount = NewBucketCount;
            MaxSizeBeforeGrow =
                    static_cast<std::size_t>(std::ceil(static_cast<double>(NewBucketCount) * LoadFactor));
        }

        Lanes.beforeUnlockAllBut(H);
        Lanes.unlockAllBut(H);
        return true;
    }
};

}  // namespace souffle
