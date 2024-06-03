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
#include <cassert>
#include <cstring>

namespace souffle {

/**
 * A concurrent, almost lock-free associative datastructure that implements the
 * Flyweight pattern.  Assigns a unique index to each inserted key. Elements
 * cannot be removed, the datastructure can only grow.
 *
 * The datastructure enables a configurable number of concurrent access lanes.
 * Access to the datastructure is lock-free between different lanes.
 * Concurrent accesses through the same lane is sequential.
 *
 * Growing the datastructure requires to temporarily lock all lanes to let a
 * single lane perform the growing operation. The global lock is amortized
 * thanks to an exponential growth strategy.
 *
 */
template <class LanesPolicy, class Key, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
class ConcurrentFlyweight {
public:
    using lane_id = typename LanesPolicy::lane_id;
    using index_type = std::size_t;
    using key_type = Key;
    using value_type = std::pair<const Key, const index_type>;
    using pointer = const value_type*;
    using reference = const value_type&;

private:
    // Effectively:
    //  data slot_type = NONE | END | Idx index_type
    //  The last two values in the domain of `index_type` are used to represent cases `NONE` and `END`
    // TODO: strong type-def wrap this to prevent implicit conversions
    using slot_type = index_type;
    static constexpr slot_type NONE = std::numeric_limits<slot_type>::max();  // special case: `std::nullopt`
    static constexpr slot_type END = NONE - 1;                                // special case: end iterator
    static constexpr slot_type SLOT_MAX = END;  // +1 the largest non-special slot value

    static_assert(std::is_same_v<slot_type, index_type>,
            "conversion helpers assume they're the underlying type, "
            "with the last two values reserved for special cases");
    static_assert(std::is_unsigned_v<slot_type>);

    /// Converts from index to slot.
    static slot_type slot(const index_type I) {
        // not expected to happen. you'll run out of memory long before.
        assert(I < SLOT_MAX && "can't represent index in `slot_type` domain");
        return static_cast<slot_type>(I);
    }

    /// Converts from slot to index.
    static index_type index(const slot_type S) {
        assert(S < SLOT_MAX && "slot is sentinal value; can't convert to index !!");
        return static_cast<index_type>(S);
    }

public:
    /// Iterator with concurrent access to the datastructure.
    struct Iterator {
        using iterator_category = std::input_iterator_tag;
        using value_type = ConcurrentFlyweight::value_type;
        using pointer = ConcurrentFlyweight::pointer;
        using reference = ConcurrentFlyweight::reference;

    private:
        const ConcurrentFlyweight* This;

        /// Access lane to the datastructure.
        lane_id Lane;

        /// Current slot.
        slot_type Slot;

        /// Next slot that might be unassigned.
        slot_type NextMaybeUnassignedSlot;

        /// Handle that owns the next slot that might be unassigned.
        slot_type NextMaybeUnassignedHandle = NONE;

    public:
        // The 'begin' iterator
        Iterator(const ConcurrentFlyweight* This, const lane_id H)
                : This(This), Lane(H), Slot(NONE), NextMaybeUnassignedSlot(0) {
            FindNextMaybeUnassignedSlot();
            MoveToNextAssignedSlot();
        }

        // The 'end' iterator
        Iterator(const ConcurrentFlyweight* This)
                : This(This), Lane(0), Slot(END), NextMaybeUnassignedSlot(END) {}

        // The iterator starting at slot I, using access lane H.
        Iterator(const ConcurrentFlyweight* This, const lane_id H, const index_type I)
                : This(This), Lane(H), Slot(slot(I)), NextMaybeUnassignedSlot(slot(I)) {
            FindNextMaybeUnassignedSlot();
            MoveToNextAssignedSlot();
        }

        Iterator(const Iterator& That)
                : This(That.This), Lane(That.Lane), Slot(That.Slot),
                  NextMaybeUnassignedSlot(That.NextMaybeUnassignedSlot),
                  NextMaybeUnassignedHandle(That.NextMaybeUnassignedHandle) {}

        Iterator(Iterator&& That)
                : This(That.This), Lane(That.Lane), Slot(That.Slot),
                  NextMaybeUnassignedSlot(That.NextMaybeUnassignedSlot),
                  NextMaybeUnassignedHandle(That.NextMaybeUnassignedHandle) {}

        Iterator& operator=(const Iterator& That) {
            This = That.This;
            Lane = That.Lane;
            Slot = That.Slot;
            NextMaybeUnassignedSlot = That.NextMaybeUnassignedSlot;
            NextMaybeUnassignedHandle = That.NextMaybeUnassignedHandle;
        }

        Iterator& operator=(Iterator&& That) {
            This = That.This;
            Lane = That.Lane;
            Slot = That.Slot;
            NextMaybeUnassignedSlot = That.NextMaybeUnassignedSlot;
            NextMaybeUnassignedHandle = That.NextMaybeUnassignedHandle;
        }

        reference operator*() const {
            const auto Guard = This->Lanes.guard(Lane);
            return *This->Slots[index(Slot)];
        }

        pointer operator->() const {
            const auto Guard = This->Lanes.guard(Lane);
            return This->Slots[index(Slot)];
        }

        Iterator& operator++() {
            MoveToNextAssignedSlot();
            return *this;
        }

        Iterator operator++(int) {
            Iterator Tmp = *this;
            ++(*this);
            return Tmp;
        }

        bool operator==(const Iterator& That) const {
            return (This == That.This) && (Slot == That.Slot);
        }

        bool operator!=(const Iterator& That) const {
            return (This != That.This) || (Slot != That.Slot);
        }

    private:
        /** Find next slot after Slot that is maybe unassigned. */
        void FindNextMaybeUnassignedSlot() {
            NextMaybeUnassignedSlot = END;
            for (lane_id I = 0; I < This->Lanes.lanes(); ++I) {
                const auto Lane = This->Lanes.guard(I);
                if ((Slot == NONE || This->Handles[I].NextSlot > Slot) &&
                        This->Handles[I].NextSlot < NextMaybeUnassignedSlot) {
                    NextMaybeUnassignedSlot = This->Handles[I].NextSlot;
                    NextMaybeUnassignedHandle = I;
                }
            }
            if (NextMaybeUnassignedSlot == END) {
                NextMaybeUnassignedSlot = This->NextSlot.load(std::memory_order_acquire);
                NextMaybeUnassignedHandle = NONE;
            }
        }

        /**
         * Move Slot to next assigned slot and return true.
         * Otherwise the end is reached and Slot is assigned `END` and return false.
         */
        bool MoveToNextAssignedSlot() {
            static_assert(NONE == std::numeric_limits<slot_type>::max(),
                    "required for wrap around to 0 for begin-iterator-scan");
            static_assert(NONE + 1 == 0, "required for wrap around to 0 for begin-iterator-scan");
            while (Slot != END) {
                assert(Slot + 1 < SLOT_MAX);
                if (Slot + 1 < NextMaybeUnassignedSlot) {  // next unassigned slot not reached
                    Slot = Slot + 1;
                    return true;
                }

                if (NextMaybeUnassignedHandle == NONE) {  // reaching end
                    Slot = END;
                    NextMaybeUnassignedSlot = END;
                    NextMaybeUnassignedHandle = NONE;
                    return false;
                }

                if (NextMaybeUnassignedHandle != NONE) {  // maybe reaching the next unassigned slot
                    This->Lanes.lock(NextMaybeUnassignedHandle);
                    const bool IsAssigned = (Slot + 1 < This->Handles[NextMaybeUnassignedHandle].NextSlot);
                    This->Lanes.unlock(NextMaybeUnassignedHandle);
                    Slot = Slot + 1;
                    FindNextMaybeUnassignedSlot();
                    if (IsAssigned) {
                        return true;
                    }
                }
            }
            return false;
        }
    };

    using iterator = Iterator;

    /// Initialize the datastructure with the given capacity.
    ConcurrentFlyweight(const std::size_t LaneCount, const std::size_t InitialCapacity,
            const bool ReserveFirst, const Hash& hash = Hash(), const KeyEqual& key_equal = KeyEqual(),
            const KeyFactory& key_factory = KeyFactory())
            : Lanes(LaneCount), HandleCount(LaneCount),
              Mapping(LaneCount, InitialCapacity, hash, key_equal, key_factory) {
        Slots = std::make_unique<const value_type*[]>(InitialCapacity);
        Handles = std::make_unique<Handle[]>(HandleCount);
        NextSlot = (ReserveFirst ? 1 : 0);
        SlotCount = InitialCapacity;
    }

    /// Initialize the datastructure with a capacity of 8 elements.
    ConcurrentFlyweight(const std::size_t LaneCount, const bool ReserveFirst, const Hash& hash = Hash(),
            const KeyEqual& key_equal = KeyEqual(), const KeyFactory& key_factory = KeyFactory())

            : ConcurrentFlyweight(LaneCount, 8, ReserveFirst, hash, key_equal, key_factory) {}

    /// Initialize the datastructure with a capacity of 8 elements.
    ConcurrentFlyweight(const std::size_t LaneCount, const Hash& hash = Hash(),
            const KeyEqual& key_equal = KeyEqual(), const KeyFactory& key_factory = KeyFactory())
            : ConcurrentFlyweight(LaneCount, 8, false, hash, key_equal, key_factory) {}

    virtual ~ConcurrentFlyweight() {
        for (lane_id I = 0; I < HandleCount; ++I) {
            if (Handles[I].NextNode) {
                delete Handles[I].NextNode;
            }
        }
    }

    /**
     * Change the number of lanes and possibly grow the number of handles.
     * Do not use while threads are using this datastructure.
     */
    void setNumLanes(const std::size_t NumLanes) {
        if (NumLanes > HandleCount) {
            std::unique_ptr<Handle[]> NextHandles = std::make_unique<Handle[]>(NumLanes);
            std::copy(Handles.get(), Handles.get() + HandleCount, NextHandles.get());
            Handles.swap(NextHandles);
            HandleCount = NumLanes;
        }
        Mapping.setNumLanes(NumLanes);
        Lanes.setNumLanes(NumLanes);
    }

    /** Return a concurrent iterator on the first element. */
    Iterator begin(const lane_id H) const {
        return Iterator(this, H);
    }

    /** Return an iterator past the last element. */
    Iterator end() const {
        return Iterator(this);
    }

    /// Return true if the value is in the map.
    template <typename K>
    bool weakContains(const lane_id H, const K& X) const {
        return Mapping.weakContains(H, X);
    }

    /// Return the value associated with the given index.
    /// Assumption: the index is mapped in the datastructure.
    const Key& fetch(const lane_id H, const index_type Idx) const {
        const auto Lane = Lanes.guard(H);
        assert(Idx < SlotCount.load(std::memory_order_relaxed));
        return Slots[Idx]->first;
    }

    /// Return the pair of the index for the given value and a boolean
    /// indicating if the value was already present (false) or inserted by this handle (true).
    /// Insert the value and return a fresh index if the value is not
    /// yet indexed.
    template <class... Args>
    std::pair<index_type, bool> findOrInsert(const lane_id H, Args&&... Xs) {
        const auto Lane = Lanes.guard(H);
        node_type Node;

        slot_type Slot = Handles[H].NextSlot;

        // Getting the next insertion slot for the current lane may require
        // more than one attempts if the datastructure must grow and other
        // threads are waiting for the same lane @p H.
        while (true) {
            if (Slot == NONE) {
                // Reserve a slot for the lane, the datastructure might need to
                // grow before the slot memory location becomes available.
                Slot = NextSlot++;
                Handles[H].NextSlot = Slot;
                Handles[H].NextNode = Mapping.node(static_cast<index_type>(Slot));
            }

            if (Slot >= SlotCount.load(std::memory_order_relaxed)) {
                // The slot memory location is not yet available, try to
                // grow the datastructure. Other threads in other lanes might
                // be attempting to grow the datastructure concurrently.
                //
                // Anyway when this call returns the Slot memory location is
                // available.
                tryGrow(H);

                // Reload the Slot for the current lane since another thread
                // using the same lane may take-over the lane during tryGrow()
                // and consume the slot before the current thread is
                // rescheduled on the lane.
                Slot = Handles[H].NextSlot;
            } else {
                // From here the slot is known, allocated and available.
                break;
            }
        }

        Node = Handles[H].NextNode;

        // Insert key in the index in advance.
        Slots[Slot] = &Node->value();

        auto Res = Mapping.get(H, Node, std::forward<Args>(Xs)...);
        if (Res.second) {
            // Inserted by self, slot is consumed, clear the lane's state.
            Handles[H].clear();
            return std::make_pair(static_cast<index_type>(Slot), true);
        } else {
            // Inserted concurrently by another thread, clearing the slot is
            // not strictly needed but it avoids leaving a dangling pointer
            // there.
            //
            // The reserved slot and node remains in the lane state so that
            // they can be consumed by the next insertion operation on this
            // lane.
            Slots[Slot] = nullptr;
            return std::make_pair(Res.first->second, false);
        }
    }

private:
    using map_type = ConcurrentInsertOnlyHashMap<LanesPolicy, Key, index_type, Hash, KeyEqual, KeyFactory>;
    using node_type = typename map_type::node_type;

    struct Handle {
        void clear() {
            NextSlot = NONE;
            NextNode = nullptr;
        }

        slot_type NextSlot = NONE;
        node_type NextNode = nullptr;
    };

protected:
    // The concurrency manager.
    LanesPolicy Lanes;

private:
    // Number of handles
    std::size_t HandleCount;

    // Handle for each concurrent lane.
    std::unique_ptr<Handle[]> Handles;

    // Slots[I] points to the value associated with index I.
    std::unique_ptr<const value_type*[]> Slots;

    // The map from keys to index.
    map_type Mapping;

    // Next available slot.
    std::atomic<slot_type> NextSlot;

    // Number of slots.
    std::atomic<slot_type> SlotCount;

    /// Grow the datastructure if needed.
    bool tryGrow(const lane_id H) {
        // This call may release and re-acquire the lane to
        // allow progress of a concurrent growing operation.
        //
        // It is possible that another thread is waiting to
        // enter the same lane, and that other thread might
        // take and leave the lane before the current thread
        // re-acquires it.
        Lanes.beforeLockAllBut(H);

        if (NextSlot < SlotCount) {
            // Current size is fine
            Lanes.beforeUnlockAllBut(H);
            return false;
        }

        Lanes.lockAllBut(H);

        {  // safe section
            const std::size_t CurrentSize = SlotCount;
            std::size_t NewSize = (CurrentSize << 1);  // double size policy
            while (NewSize < NextSlot) {
                NewSize <<= 1;  // double size
            }
            std::unique_ptr<const value_type*[]> NewSlots = std::make_unique<const value_type*[]>(NewSize);
            std::memcpy(NewSlots.get(), Slots.get(), sizeof(const value_type*) * CurrentSize);
            Slots = std::move(NewSlots);
            SlotCount = NewSize;
        }

        Lanes.beforeUnlockAllBut(H);
        Lanes.unlockAllBut(H);

        return true;
    }
};

#ifdef _OPENMP
/** A Flyweight datastructure with concurrent access specialized for OpenMP. */
template <class Key, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
class OmpFlyweight : protected ConcurrentFlyweight<ConcurrentLanes, Key, Hash, KeyEqual, KeyFactory> {
public:
    using Base = ConcurrentFlyweight<ConcurrentLanes, Key, Hash, KeyEqual, KeyFactory>;
    using index_type = typename Base::index_type;
    using lane_id = typename Base::lane_id;
    using iterator = typename Base::iterator;

    explicit OmpFlyweight(const std::size_t LaneCount, const std::size_t InitialCapacity = 8,
            const bool ReserveFirst = false, const Hash& hash = Hash(),
            const KeyEqual& key_equal = KeyEqual(), const KeyFactory& key_factory = KeyFactory())
            : Base(LaneCount, InitialCapacity, ReserveFirst, hash, key_equal, key_factory) {}

    iterator begin() const {
        return Base::begin(Base::Lanes.threadLane());
    }

    iterator end() const {
        return Base::end();
    }

    template <typename K>
    bool weakContains(const K& X) const {
        return Base::weakContains(Base::Lanes.threadLane(), X);
    }

    const Key& fetch(const index_type Idx) const {
        return Base::fetch(Base::Lanes.threadLane(), Idx);
    }

    template <class... Args>
    std::pair<index_type, bool> findOrInsert(Args&&... Xs) {
        return Base::findOrInsert(Base::Lanes.threadLane(), std::forward<Args>(Xs)...);
    }
};
#endif

/**
 * A Flyweight datastructure with sequential access.
 *
 * Reuse the concurrent flyweight with a single access handle.
 */
template <class Key, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
class SeqFlyweight : protected ConcurrentFlyweight<SeqConcurrentLanes, Key, Hash, KeyEqual, KeyFactory> {
public:
    using Base = ConcurrentFlyweight<SeqConcurrentLanes, Key, Hash, KeyEqual, KeyFactory>;
    using index_type = typename Base::index_type;
    using lane_id = typename Base::lane_id;
    using iterator = typename Base::iterator;

    explicit SeqFlyweight(const std::size_t NumLanes, const std::size_t InitialCapacity = 8,
            const bool ReserveFirst = false, const Hash& hash = Hash(),
            const KeyEqual& key_equal = KeyEqual(), const KeyFactory& key_factory = KeyFactory())
            : Base(NumLanes, InitialCapacity, ReserveFirst, hash, key_equal, key_factory) {}

    iterator begin() const {
        return Base::begin(0);
    }

    iterator end() const {
        return Base::end();
    }

    template <typename K>
    bool weakContains(const K& X) const {
        return Base::weakContains(0, X);
    }

    const Key& fetch(const index_type Idx) const {
        return Base::fetch(0, Idx);
    }

    template <class... Args>
    std::pair<index_type, bool> findOrInsert(Args&&... Xs) {
        return Base::findOrInsert(0, std::forward<Args>(Xs)...);
    }
};

#ifdef _OPENMP
template <class Key, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
using FlyweightImpl = OmpFlyweight<Key, Hash, KeyEqual, KeyFactory>;
#else
template <class Key, class Hash = std::hash<Key>, class KeyEqual = std::equal_to<Key>,
        class KeyFactory = details::Factory<Key>>
using FlyweightImpl = SeqFlyweight<Key, Hash, KeyEqual, KeyFactory>;
#endif

}  // namespace souffle
