/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Brie.h
 *
 * This header file contains the implementation for a generic, fixed
 * length integer trie.
 *
 * Tries trie is utilized to store n-ary tuples of integers. Each level
 * is implemented via a sparse array (also covered by this header file),
 * referencing the following nested level. The leaf level is realized
 * by a sparse bit-map to minimize the memory footprint.
 *
 * Multiple insert operations can be be conducted concurrently on trie
 * structures. So can read-only operations. However, inserts and read
 * operations may not be conducted at the same time.
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/utility/CacheUtil.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StreamUtil.h"
#include "souffle/utility/span.h"
#include <algorithm>
#include <atomic>
#include <bitset>
#include <cassert>
#include <climits>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <iterator>
#include <limits>
#include <type_traits>
#include <utility>
#include <vector>

// TODO: replace intrinsics w/ std lib functions?
#ifdef _WIN32
/**
 * When compiling for windows, redefine the gcc builtins which are used to
 * their equivalents on the windows platform.
 */
#define __sync_synchronize MemoryBarrier
#define __sync_bool_compare_and_swap(ptr, oldval, newval) \
    (InterlockedCompareExchangePointer((void* volatile*)ptr, (void*)newval, (void*)oldval) == (void*)oldval)
#endif  // _WIN32

namespace souffle {

template <unsigned Dim>
class Trie;

namespace detail::brie {

// FIXME: These data structs should be parameterised/made agnostic to `RamDomain` type.
using brie_element_type = RamDomain;

using tcb::make_span;

template <typename A>
struct forward_non_output_iterator_traits {
    using value_type = A;
    using difference_type = ptrdiff_t;
    using iterator_category = std::forward_iterator_tag;
    using pointer = const value_type*;
    using reference = const value_type&;
};

template <typename A, std::size_t arity>
auto copy(span<A, arity> s) {
    std::array<std::decay_t<A>, arity> cpy;
    std::copy_n(s.begin(), arity, cpy.begin());
    return cpy;
}

template <std::size_t offset, typename A, std::size_t arity>
auto drop(span<A, arity> s) -> std::enable_if_t<offset <= arity, span<A, arity - offset>> {
    return {s.begin() + offset, s.end()};
}

template <typename C>
auto tail(C& s) {
    return drop<1>(make_span(s));
}

/**
 * A templated functor to obtain default values for
 * unspecified elements of sparse array instances.
 */
template <typename T>
struct default_factory {
    T operator()() const {
        return T();  // just use the default constructor
    }
};

/**
 * A functor representing the identity function.
 */
template <typename T>
struct identity {
    T operator()(T v) const {
        return v;
    }
};

/**
 * A operation to be utilized by the sparse map when merging
 * elements associated to different values.
 */
template <typename T>
struct default_merge {
    /**
     * Merges two values a and b when merging spase maps.
     */
    T operator()(T a, T b) const {
        default_factory<T> def;
        // if a is the default => us b, else stick to a
        return (a != def()) ? a : b;
    }
};

/**
 * Iterator type for `souffle::SparseArray`.
 */
template <typename SparseArray>
struct SparseArrayIter {
    using Node = typename SparseArray::Node;
    using index_type = typename SparseArray::index_type;
    using array_value_type = typename SparseArray::value_type;

    using value_type = std::pair<index_type, array_value_type>;

    SparseArrayIter() = default;  // default constructor -- creating an end-iterator
    SparseArrayIter(const SparseArrayIter&) = default;
    SparseArrayIter& operator=(const SparseArrayIter&) = default;

    SparseArrayIter(const Node* node, value_type value) : node(node), value(std::move(value)) {}

    SparseArrayIter(const Node* first, index_type firstOffset) : node(first), value(firstOffset, 0) {
        // if the start is the end => we are done
        if (!first) return;

        // load the value
        if (first->cell[0].value == array_value_type()) {
            ++(*this);  // walk to first element
        } else {
            value.second = first->cell[0].value;
        }
    }

    // the equality operator as required by the iterator concept
    bool operator==(const SparseArrayIter& other) const {
        // only equivalent if pointing to the end
        return (node == nullptr && other.node == nullptr) ||
               (node == other.node && value.first == other.value.first);
    }

    // the not-equality operator as required by the iterator concept
    bool operator!=(const SparseArrayIter& other) const {
        return !(*this == other);
    }

    // the deref operator as required by the iterator concept
    const value_type& operator*() const {
        return value;
    }

    // support for the pointer operator
    const value_type* operator->() const {
        return &value;
    }

    // the increment operator as required by the iterator concept
    SparseArrayIter& operator++() {
        assert(!isEnd());
        // get current offset
        index_type x = value.first & SparseArray::INDEX_MASK;

        // go to next non-empty value in current node
        do {
            x++;
        } while (x < SparseArray::NUM_CELLS && node->cell[x].value == array_value_type());

        // check whether one has been found
        if (x < SparseArray::NUM_CELLS) {
            // update value and be done
            value.first = (value.first & ~SparseArray::INDEX_MASK) | x;
            value.second = node->cell[x].value;
            return *this;  // done
        }

        // go to parent
        node = node->parent;
        int level = 1;

        // get current index on this level
        x = SparseArray::getIndex(brie_element_type(value.first), level);
        x++;

        while (level > 0 && node) {
            // search for next child
            while (x < SparseArray::NUM_CELLS) {
                if (node->cell[x].ptr != nullptr) {
                    break;
                }
                x++;
            }

            // pick next step
            if (x < SparseArray::NUM_CELLS) {
                // going down
                node = node->cell[x].ptr;
                value.first &= SparseArray::getLevelMask(level + 1);
                value.first |= x << (SparseArray::BIT_PER_STEP * level);
                level--;
                x = 0;
            } else {
                // going up
                node = node->parent;
                level++;

                // get current index on this level
                x = SparseArray::getIndex(brie_element_type(value.first), level);
                x++;  // go one step further
            }
        }

        // check whether it is the end of range
        if (node == nullptr) {
            return *this;
        }

        // search the first value in this node
        x = 0;
        while (node->cell[x].value == array_value_type()) {
            x++;
        }

        // update value
        value.first |= x;
        value.second = node->cell[x].value;

        // done
        return *this;
    }

    SparseArrayIter operator++(int) {
        auto cpy = *this;
        ++(*this);
        return cpy;
    }

    // True if this iterator is passed the last element.
    bool isEnd() const {
        return node == nullptr;
    }

    // enables this iterator core to be printed (for debugging)
    void print(std::ostream& out) const {
        // `StreamUtil.h` defines an overload for `pair`, but we can't rely on it b/c
        // it's disabled if `__EMBEDDED__` is defined.
        out << "SparseArrayIter(" << node << " @ (" << value.first << ", " << value.second << "))";
    }

    friend std::ostream& operator<<(std::ostream& out, const SparseArrayIter& iter) {
        iter.print(out);
        return out;
    }

private:
    // a pointer to the leaf node currently processed or null (end)
    const Node* node{};

    // the value currently pointed to
    value_type value;
};

}  // namespace detail::brie

using namespace detail::brie;

/**
 * A sparse array simulates an array associating to every element
 * of uint32_t an element of a generic type T. Any non-defined element
 * will be default-initialized utilizing the detail::brie::default_factory
 * functor.
 *
 * Internally the array is organized as a balanced tree. The leaf
 * level of the tree corresponds to the elements of the represented
 * array. Inner nodes utilize individual bits of the indices to reference
 * sub-trees. For efficiency reasons, only the minimal sub-tree required
 * to cover all non-null / non-default values stored in the array is
 * maintained. Furthermore, several levels of nodes are aggreated in a
 * B-tree like fashion to inprove cache utilization and reduce the number
 * of steps required for lookup and insert operations.
 *
 * @tparam T the type of the stored elements
 * @tparam BITS the number of bits consumed per node-level
 *              e.g. if it is set to 3, the resulting tree will be of a degree of
 *              2^3=8, and thus 8 child-pointers will be stored in each inner node
 *              and as many values will be stored in each leaf node.
 * @tparam merge_op the functor to be utilized when merging the content of two
 *              instances of this type.
 * @tparam copy_op a functor to be applied to each stored value when copying an
 *              instance of this array. For instance, this is utilized by the
 *              trie implementation to create a clone of each sub-tree instead
 *              of preserving the original pointer.
 */
template <typename T, unsigned BITS = 6, typename merge_op = default_merge<T>, typename copy_op = identity<T>>
class SparseArray {
    template <typename A>
    friend struct detail::brie::SparseArrayIter;

    using this_t = SparseArray<T, BITS, merge_op, copy_op>;
    using key_type = uint64_t;

    // some internal constants
    static constexpr int BIT_PER_STEP = BITS;
    static constexpr int NUM_CELLS = 1 << BIT_PER_STEP;
    static constexpr key_type INDEX_MASK = NUM_CELLS - 1;

public:
    // the type utilized for indexing contained elements
    using index_type = key_type;

    // the type of value stored in this array
    using value_type = T;

    // the atomic view on stored values
    using atomic_value_type = std::atomic<value_type>;

private:
    struct Node;

    /**
     * The value stored in a single cell of a inner
     * or leaf node.
     */
    union Cell {
        // an atomic view on the pointer referencing a nested level
        std::atomic<Node*> aptr;

        // a pointer to the nested level (unsynchronized operations)
        Node* ptr{nullptr};

        // an atomic view on the value stored in this cell (leaf node)
        atomic_value_type avalue;

        // the value stored in this cell (unsynchronized access, leaf node)
        value_type value;
    };

    /**
     * The node type of the internally maintained tree.
     */
    struct Node {
        // a pointer to the parent node (for efficient iteration)
        const Node* parent;
        // the pointers to the child nodes (inner nodes) or the stored values (leaf nodes)
        Cell cell[NUM_CELLS];
    };

    /**
     * A struct describing all the information required by the container
     * class to manage the wrapped up tree.
     */
    struct RootInfo {
        // the root node of the tree
        Node* root;
        // the number of levels of the tree
        uint32_t levels;
        // the absolute offset of the theoretical first element in the tree
        index_type offset;

        // the first leaf node in the tree
        Node* first;
        // the absolute offset of the first element in the first leaf node
        index_type firstOffset;
    };

    union {
        RootInfo unsynced;         // for sequential operations
        volatile RootInfo synced;  // for synchronized operations
    };

public:
    /**
     * A default constructor creating an empty sparse array.
     */
    SparseArray() : unsynced(RootInfo{nullptr, 0, 0, nullptr, std::numeric_limits<index_type>::max()}) {}

    /**
     * A copy constructor for sparse arrays. It creates a deep
     * copy of the data structure maintained by the handed in
     * array instance.
     */
    SparseArray(const SparseArray& other)
            : unsynced(RootInfo{clone(other.unsynced.root, other.unsynced.levels), other.unsynced.levels,
                      other.unsynced.offset, nullptr, other.unsynced.firstOffset}) {
        if (unsynced.root) {
            unsynced.root->parent = nullptr;
            unsynced.first = findFirst(unsynced.root, unsynced.levels);
        }
    }

    /**
     * A r-value based copy constructor for sparse arrays. It
     * takes over ownership of the structure maintained by the
     * handed in array.
     */
    SparseArray(SparseArray&& other)
            : unsynced(RootInfo{other.unsynced.root, other.unsynced.levels, other.unsynced.offset,
                      other.unsynced.first, other.unsynced.firstOffset}) {
        other.unsynced.root = nullptr;
        other.unsynced.levels = 0;
        other.unsynced.first = nullptr;
    }

    /**
     * A destructor for sparse arrays clearing up the internally
     * maintained data structure.
     */
    ~SparseArray() {
        clean();
    }

    /**
     * An assignment creating a deep copy of the handed in
     * array structure (utilizing the copy functor provided
     * as a template parameter).
     */
    SparseArray& operator=(const SparseArray& other) {
        if (this == &other) return *this;

        // clean this one
        clean();

        // copy content
        unsynced.levels = other.unsynced.levels;
        unsynced.root = clone(other.unsynced.root, unsynced.levels);
        if (unsynced.root) {
            unsynced.root->parent = nullptr;
        }
        unsynced.offset = other.unsynced.offset;
        unsynced.first = (unsynced.root) ? findFirst(unsynced.root, unsynced.levels) : nullptr;
        unsynced.firstOffset = other.unsynced.firstOffset;

        // done
        return *this;
    }

    /**
     * An assignment operation taking over ownership
     * from a r-value reference to a sparse array.
     */
    SparseArray& operator=(SparseArray&& other) {
        // clean this one
        clean();

        // harvest content
        unsynced.root = other.unsynced.root;
        unsynced.levels = other.unsynced.levels;
        unsynced.offset = other.unsynced.offset;
        unsynced.first = other.unsynced.first;
        unsynced.firstOffset = other.unsynced.firstOffset;

        // reset other
        other.unsynced.root = nullptr;
        other.unsynced.levels = 0;
        other.unsynced.first = nullptr;

        // done
        return *this;
    }

    /**
     * Tests whether this sparse array is empty, thus it only
     * contains default-values, or not.
     */
    bool empty() const {
        return unsynced.root == nullptr;
    }

    /**
     * Computes the number of non-empty elements within this
     * sparse array.
     */
    std::size_t size() const {
        // quick one for the empty map
        if (empty()) return 0;

        // count elements -- since maintaining is making inserts more expensive
        std::size_t res = 0;
        for (auto it = begin(); it != end(); ++it) {
            ++res;
        }
        return res;
    }

private:
    /**
     * Computes the memory usage of the given sub-tree.
     */
    static std::size_t getMemoryUsage(const Node* node, int level) {
        // support null-nodes
        if (!node) return 0;

        // add size of current node
        std::size_t res = sizeof(Node);

        // sum up memory usage of child nodes
        if (level > 0) {
            for (int i = 0; i < NUM_CELLS; i++) {
                res += getMemoryUsage(node->cell[i].ptr, level - 1);
            }
        }

        // done
        return res;
    }

public:
    /**
     * Computes the total memory usage of this data structure.
     */
    std::size_t getMemoryUsage() const {
        // the memory of the wrapper class
        std::size_t res = sizeof(*this);

        // add nodes
        if (unsynced.root) {
            res += getMemoryUsage(unsynced.root, unsynced.levels);
        }

        // done
        return res;
    }

    /**
     * Resets the content of this array to default values for each contained
     * element.
     */
    void clear() {
        clean();
        unsynced.root = nullptr;
        unsynced.levels = 0;
        unsynced.first = nullptr;
        unsynced.firstOffset = std::numeric_limits<index_type>::max();
    }

    /**
     * A struct to be utilized as a local, temporal context by client code
     * to speed up the execution of various operations (optional parameter).
     */
    struct op_context {
        index_type lastIndex{0};
        Node* lastNode{nullptr};
        op_context() = default;
    };

private:
    // ---------------------------------------------------------------------
    //              Optimistic Locking of Root-Level Infos
    // ---------------------------------------------------------------------

    /**
     * A struct to cover a snapshot of the root node state.
     */
    struct RootInfoSnapshot {
        // the current pointer to a root node
        Node* root;
        // the current number of levels
        uint32_t levels;
        // the current offset of the first theoretical element
        index_type offset;
        // a version number for the optimistic locking
        uintptr_t version;
    };

    /**
     * Obtains the current version of the root.
     */
    uint64_t getRootVersion() const {
        // here it is assumed that the load of a 64-bit word is atomic
        return (uint64_t)synced.root;
    }

    /**
     * Obtains a snapshot of the current root information.
     */
    RootInfoSnapshot getRootInfo() const {
        RootInfoSnapshot res{};
        do {
            // first take the mod counter
            do {
                // if res.mod % 2 == 1 .. there is an update in progress
                res.version = getRootVersion();
            } while (res.version % 2);

            // then the rest
            res.root = synced.root;
            res.levels = synced.levels;
            res.offset = synced.offset;

            // check consistency of obtained data (optimistic locking)
        } while (res.version != getRootVersion());

        // got a consistent snapshot
        return res;
    }

    /**
     * Updates the current root information based on the handed in modified
     * snapshot instance if the version number of the snapshot still corresponds
     * to the current version. Otherwise a concurrent update took place and the
     * operation is aborted.
     *
     * @param info the updated information to be assigned to the active root-info data
     * @return true if successfully updated, false if aborted
     */
    bool tryUpdateRootInfo(const RootInfoSnapshot& info) {
        // check mod counter
        uintptr_t version = info.version;

        // update root to invalid pointer (ending with 1)
        if (!__sync_bool_compare_and_swap(&synced.root, (Node*)version, (Node*)(version + 1))) {
            return false;
        }

        // conduct update
        synced.levels = info.levels;
        synced.offset = info.offset;

        // update root (and thus the version to enable future retrievals)
        __sync_synchronize();
        synced.root = info.root;

        // done
        return true;
    }

    /**
     * A struct summarizing the state of the first node reference.
     */
    struct FirstInfoSnapshot {
        // the pointer to the first node
        Node* node;
        // the offset of the first node
        index_type offset;
        // the version number of the first node (for the optimistic locking)
        uintptr_t version;
    };

    /**
     * Obtains the current version number of the first node information.
     */
    uint64_t getFirstVersion() const {
        // here it is assumed that the load of a 64-bit word is atomic
        return (uint64_t)synced.first;
    }

    /**
     * Obtains a snapshot of the current first-node information.
     */
    FirstInfoSnapshot getFirstInfo() const {
        FirstInfoSnapshot res{};
        do {
            // first take the version
            do {
                res.version = getFirstVersion();
            } while (res.version % 2);

            // collect the values
            res.node = synced.first;
            res.offset = synced.firstOffset;

        } while (res.version != getFirstVersion());

        // we got a consistent snapshot
        return res;
    }

    /**
     * Updates the information stored regarding the first node in a
     * concurrent setting utilizing a optimistic locking approach.
     * This is identical to the approach utilized for the root info.
     */
    bool tryUpdateFirstInfo(const FirstInfoSnapshot& info) {
        // check mod counter
        uintptr_t version = info.version;

        // temporary update first pointer to point to uneven value (lock-out)
        if (!__sync_bool_compare_and_swap(&synced.first, (Node*)version, (Node*)(version + 1))) {
            return false;
        }

        // conduct update
        synced.firstOffset = info.offset;

        // update node pointer (and thus the version number)
        __sync_synchronize();
        synced.first = info.node;  // must be last (and atomic)

        // done
        return true;
    }

public:
    /**
     * Obtains a mutable reference to the value addressed by the given index.
     *
     * @param i the index of the element to be addressed
     * @return a mutable reference to the corresponding element
     */
    value_type& get(index_type i) {
        op_context ctxt;
        return get(i, ctxt);
    }

    /**
     * Obtains a mutable reference to the value addressed by the given index.
     *
     * @param i the index of the element to be addressed
     * @param ctxt a operation context to exploit state-less temporal locality
     * @return a mutable reference to the corresponding element
     */
    value_type& get(index_type i, op_context& ctxt) {
        return getLeaf(i, ctxt).value;
    }

    /**
     * Obtains a mutable reference to the atomic value addressed by the given index.
     *
     * @param i the index of the element to be addressed
     * @return a mutable reference to the corresponding element
     */
    atomic_value_type& getAtomic(index_type i) {
        op_context ctxt;
        return getAtomic(i, ctxt);
    }

    /**
     * Obtains a mutable reference to the atomic value addressed by the given index.
     *
     * @param i the index of the element to be addressed
     * @param ctxt a operation context to exploit state-less temporal locality
     * @return a mutable reference to the corresponding element
     */
    atomic_value_type& getAtomic(index_type i, op_context& ctxt) {
        return getLeaf(i, ctxt).avalue;
    }

private:
    /**
     * An internal function capable of navigating to a given leaf node entry.
     * If the cell does not exist yet it will be created as a side-effect.
     *
     * @param i the index of the requested cell
     * @param ctxt a operation context to exploit state-less temporal locality
     * @return a reference to the requested cell
     */
    inline Cell& getLeaf(index_type i, op_context& ctxt) {
        // check context
        if (ctxt.lastNode && (ctxt.lastIndex == (i & ~INDEX_MASK))) {
            // return reference to referenced
            return ctxt.lastNode->cell[i & INDEX_MASK];
        }

        // get snapshot of root
        auto info = getRootInfo();

        // check for emptiness
        if (info.root == nullptr) {
            // build new root node
            info.root = newNode();

            // initialize the new node
            info.root->parent = nullptr;
            info.offset = i & ~(INDEX_MASK);

            // try updating root information atomically
            if (tryUpdateRootInfo(info)) {
                // success -- finish get call

                // update first
                auto firstInfo = getFirstInfo();
                while (info.offset < firstInfo.offset) {
                    firstInfo.node = info.root;
                    firstInfo.offset = info.offset;
                    if (!tryUpdateFirstInfo(firstInfo)) {
                        // there was some concurrent update => check again
                        firstInfo = getFirstInfo();
                    }
                }

                // return reference to proper cell
                return info.root->cell[i & INDEX_MASK];
            }

            // somebody else was faster => use standard insertion procedure
            delete info.root;

            // retrieve new root info
            info = getRootInfo();

            // make sure there is a root
            assert(info.root);
        }

        // for all other inserts
        //   - check boundary
        //   - navigate to node
        //   - insert value

        // check boundaries
        while (!inBoundaries(i, info.levels, info.offset)) {
            // boundaries need to be expanded by growing upwards
            raiseLevel(info);  // try raising level unless someone else did already
            // update root info
            info = getRootInfo();
        }

        // navigate to node
        Node* node = info.root;
        unsigned level = info.levels;
        while (level != 0) {
            // get X coordinate
            auto x = getIndex(brie_element_type(i), level);

            // decrease level counter
            --level;

            // check next node
            std::atomic<Node*>& aNext = node->cell[x].aptr;
            Node* next = aNext;
            if (!next) {
                // create new sub-tree
                Node* newNext = newNode();
                newNext->parent = node;

                // try to update next
                if (!aNext.compare_exchange_strong(next, newNext)) {
                    // some other thread was faster => use updated next
                    delete newNext;
                } else {
                    // the locally created next is the new next
                    next = newNext;

                    // update first
                    if (level == 0) {
                        // compute offset of this node
                        auto off = i & ~INDEX_MASK;

                        // fast over-approximation of whether a update is necessary
                        if (off < unsynced.firstOffset) {
                            // update first reference if this one is the smallest
                            auto first_info = getFirstInfo();
                            while (off < first_info.offset) {
                                first_info.node = next;
                                first_info.offset = off;
                                if (!tryUpdateFirstInfo(first_info)) {
                                    // there was some concurrent update => check again
                                    first_info = getFirstInfo();
                                }
                            }
                        }
                    }
                }

                // now next should be defined
                assert(next);
            }

            // continue one level below
            node = next;
        }

        // update context
        ctxt.lastIndex = (i & ~INDEX_MASK);
        ctxt.lastNode = node;

        // return reference to cell
        return node->cell[i & INDEX_MASK];
    }

public:
    /**
     * Updates the value stored in cell i by the given value.
     */
    void update(index_type i, const value_type& val) {
        op_context ctxt;
        update(i, val, ctxt);
    }

    /**
     * Updates the value stored in cell i by the given value. A operation
     * context can be provided for exploiting temporal locality.
     */
    void update(index_type i, const value_type& val, op_context& ctxt) {
        get(i, ctxt) = val;
    }

    /**
     * Obtains the value associated to index i -- which might be
     * the default value of the covered type if the value hasn't been
     * defined previously.
     */
    value_type operator[](index_type i) const {
        return lookup(i);
    }

    /**
     * Obtains the value associated to index i -- which might be
     * the default value of the covered type if the value hasn't been
     * defined previously.
     */
    value_type lookup(index_type i) const {
        op_context ctxt;
        return lookup(i, ctxt);
    }

    /**
     * Obtains the value associated to index i -- which might be
     * the default value of the covered type if the value hasn't been
     * defined previously. A operation context can be provided for
     * exploiting temporal locality.
     */
    value_type lookup(index_type i, op_context& ctxt) const {
        // check whether it is empty
        if (!unsynced.root) return default_factory<value_type>()();

        // check boundaries
        if (!inBoundaries(i)) return default_factory<value_type>()();

        // check context
        if (ctxt.lastNode && ctxt.lastIndex == (i & ~INDEX_MASK)) {
            return ctxt.lastNode->cell[i & INDEX_MASK].value;
        }

        // navigate to value
        Node* node = unsynced.root;
        unsigned level = unsynced.levels;
        while (level != 0) {
            // get X coordinate
            auto x = getIndex(brie_element_type(i), level);

            // decrease level counter
            --level;

            // check next node
            Node* next = node->cell[x].ptr;

            // check next step
            if (!next) return default_factory<value_type>()();

            // continue one level below
            node = next;
        }

        // remember context
        ctxt.lastIndex = (i & ~INDEX_MASK);
        ctxt.lastNode = node;

        // return reference to cell
        return node->cell[i & INDEX_MASK].value;
    }

private:
    /**
     * A static operation utilized internally for merging sub-trees recursively.
     *
     * @param parent the parent node of the current merge operation
     * @param trg a reference to the pointer the cloned node should be stored to
     * @param src the node to be cloned
     * @param levels the height of the cloned node
     */
    static void merge(const Node* parent, Node*& trg, const Node* src, int levels) {
        // if other side is null => done
        if (src == nullptr) {
            return;
        }

        // if the trg sub-tree is empty, clone the corresponding branch
        if (trg == nullptr) {
            trg = clone(src, levels);
            if (trg != nullptr) {
                trg->parent = parent;
            }
            return;  // done
        }

        // otherwise merge recursively

        // the leaf-node step
        if (levels == 0) {
            merge_op merg;
            for (int i = 0; i < NUM_CELLS; ++i) {
                trg->cell[i].value = merg(trg->cell[i].value, src->cell[i].value);
            }
            return;
        }

        // the recursive step
        for (int i = 0; i < NUM_CELLS; ++i) {
            merge(trg, trg->cell[i].ptr, src->cell[i].ptr, levels - 1);
        }
    }

public:
    /**
     * Adds all the values stored in the given array to this array.
     */
    void addAll(const SparseArray& other) {
        // skip if other is empty
        if (other.empty()) {
            return;
        }

        // special case: emptiness
        if (empty()) {
            // use assignment operator
            *this = other;
            return;
        }

        // adjust levels
        while (unsynced.levels < other.unsynced.levels || !inBoundaries(other.unsynced.offset)) {
            raiseLevel();
        }

        // navigate to root node equivalent of the other node in this tree
        auto level = unsynced.levels;
        Node** node = &unsynced.root;
        while (level > other.unsynced.levels) {
            // get X coordinate
            auto x = getIndex(brie_element_type(other.unsynced.offset), level);

            // decrease level counter
            --level;

            // check next node
            Node*& next = (*node)->cell[x].ptr;
            if (!next) {
                // create new sub-tree
                next = newNode();
                next->parent = *node;
            }

            // continue one level below
            node = &next;
        }

        // merge sub-branches from here
        merge((*node)->parent, *node, other.unsynced.root, level);

        // update first
        if (unsynced.firstOffset > other.unsynced.firstOffset) {
            unsynced.first = findFirst(*node, level);
            unsynced.firstOffset = other.unsynced.firstOffset;
        }
    }

    // ---------------------------------------------------------------------
    //                           Iterator
    // ---------------------------------------------------------------------

    using iterator = SparseArrayIter<this_t>;

    /**
     * Obtains an iterator referencing the first non-default element or end in
     * case there are no such elements.
     */
    iterator begin() const {
        return iterator(unsynced.first, unsynced.firstOffset);
    }

    /**
     * An iterator referencing the position after the last non-default element.
     */
    iterator end() const {
        return iterator();
    }

    /**
     * An operation to obtain an iterator referencing an element addressed by the
     * given index. If the corresponding element is a non-default value, a corresponding
     * iterator will be returned. Otherwise end() will be returned.
     */
    iterator find(index_type i) const {
        op_context ctxt;
        return find(i, ctxt);
    }

    /**
     * An operation to obtain an iterator referencing an element addressed by the
     * given index. If the corresponding element is a non-default value, a corresponding
     * iterator will be returned. Otherwise end() will be returned. A operation context
     * can be provided for exploiting temporal locality.
     */
    iterator find(index_type i, op_context& ctxt) const {
        // check whether it is empty
        if (!unsynced.root) return end();

        // check boundaries
        if (!inBoundaries(i)) return end();

        // check context
        if (ctxt.lastNode && ctxt.lastIndex == (i & ~INDEX_MASK)) {
            Node* node = ctxt.lastNode;

            // check whether there is a proper entry
            value_type value = node->cell[i & INDEX_MASK].value;
            if (value == value_type{}) {
                return end();
            }
            // return iterator pointing to value
            return iterator(node, std::make_pair(i, value));
        }

        // navigate to value
        Node* node = unsynced.root;
        unsigned level = unsynced.levels;
        while (level != 0) {
            // get X coordinate
            auto x = getIndex(i, level);

            // decrease level counter
            --level;

            // check next node
            Node* next = node->cell[x].ptr;

            // check next step
            if (!next) return end();

            // continue one level below
            node = next;
        }

        // register in context
        ctxt.lastNode = node;
        ctxt.lastIndex = (i & ~INDEX_MASK);

        // check whether there is a proper entry
        value_type value = node->cell[i & INDEX_MASK].value;
        if (value == value_type{}) {
            return end();
        }

        // return iterator pointing to cell
        return iterator(node, std::make_pair(i, value));
    }

    /**
     * An operation obtaining the smallest non-default element such that it's index is >=
     * the given index.
     */
    iterator lowerBound(index_type i) const {
        op_context ctxt;
        return lowerBound(i, ctxt);
    }

    /**
     * An operation obtaining the smallest non-default element such that it's index is >=
     * the given index. A operation context can be provided for exploiting temporal locality.
     */
    iterator lowerBound(index_type i, op_context&) const {
        // check whether it is empty
        if (!unsynced.root) return end();

        // check boundaries
        if (!inBoundaries(i)) {
            // if it is on the lower end, return minimum result
            if (i < unsynced.offset) {
                const auto& value = unsynced.first->cell[0].value;
                auto res = iterator(unsynced.first, std::make_pair(unsynced.offset, value));
                if (value == value_type()) {
                    ++res;
                }
                return res;
            }
            // otherwise it is on the high end, return end iterator
            return end();
        }

        // navigate to value
        Node* node = unsynced.root;
        unsigned level = unsynced.levels;
        while (true) {
            // get X coordinate
            auto x = getIndex(brie_element_type(i), level);

            // check next node
            Node* next = node->cell[x].ptr;

            // check next step
            if (!next) {
                if (x == NUM_CELLS - 1) {
                    ++level;
                    node = const_cast<Node*>(node->parent);
                    if (!node) return end();
                }

                // continue search
                i = i & getLevelMask(level);

                // find next higher value
                i += 1ull << (BITS * level);

            } else {
                if (level == 0) {
                    // found boundary
                    return iterator(node, std::make_pair(i, node->cell[x].value));
                }

                // decrease level counter
                --level;

                // continue one level below
                node = next;
            }
        }
    }

    /**
     * An operation obtaining the smallest non-default element such that it's index is greater
     * the given index.
     */
    iterator upperBound(index_type i) const {
        op_context ctxt;
        return upperBound(i, ctxt);
    }

    /**
     * An operation obtaining the smallest non-default element such that it's index is greater
     * the given index. A operation context can be provided for exploiting temporal locality.
     */
    iterator upperBound(index_type i, op_context& ctxt) const {
        if (i == std::numeric_limits<index_type>::max()) {
            return end();
        }
        return lowerBound(i + 1, ctxt);
    }

private:
    /**
     * An internal debug utility printing the internal structure of this sparse array to the given output
     * stream.
     */
    void dump(bool detailed, std::ostream& out, const Node& node, int level, index_type offset,
            int indent = 0) const {
        auto x = getIndex(offset, level + 1);
        out << times("\t", indent) << x << ": Node " << &node << " on level " << level
            << " parent: " << node.parent << " -- range: " << offset << " - "
            << (offset + ~getLevelMask(level + 1)) << "\n";

        if (level == 0) {
            for (int i = 0; i < NUM_CELLS; i++) {
                if (detailed || node.cell[i].value != value_type()) {
                    out << times("\t", indent + 1) << i << ": [" << (offset + i) << "] " << node.cell[i].value
                        << "\n";
                }
            }
        } else {
            for (int i = 0; i < NUM_CELLS; i++) {
                if (node.cell[i].ptr) {
                    dump(detailed, out, *node.cell[i].ptr, level - 1,
                            offset + (i * (index_type(1) << (level * BIT_PER_STEP))), indent + 1);
                } else if (detailed) {
                    auto low = offset + (i * (1 << (level * BIT_PER_STEP)));
                    auto hig = low + ~getLevelMask(level);
                    out << times("\t", indent + 1) << i << ": empty range " << low << " - " << hig << "\n";
                }
            }
        }
        out << "\n";
    }

public:
    /**
     * A debug utility printing the internal structure of this sparse array to the given output stream.
     */
    void dump(bool detail = false, std::ostream& out = std::cout) const {
        if (!unsynced.root) {
            out << " - empty - \n";
            return;
        }
        out << "root:  " << unsynced.root << "\n";
        out << "offset: " << unsynced.offset << "\n";
        out << "first: " << unsynced.first << "\n";
        out << "fist offset: " << unsynced.firstOffset << "\n";
        dump(detail, out, *unsynced.root, unsynced.levels, unsynced.offset);
    }

private:
    // --------------------------------------------------------------------------
    //                                 Utilities
    // --------------------------------------------------------------------------

    /**
     * Creates new nodes and initializes them with 0.
     */
    static Node* newNode() {
        return new Node();
    }

    /**
     * Destroys a node and all its sub-nodes recursively.
     */
    static void freeNodes(Node* node, int level) {
        if (!node) return;
        if (level != 0) {
            for (int i = 0; i < NUM_CELLS; i++) {
                freeNodes(node->cell[i].ptr, level - 1);
            }
        }
        delete node;
    }

    /**
     * Conducts a cleanup of the internal tree structure.
     */
    void clean() {
        freeNodes(unsynced.root, unsynced.levels);
        unsynced.root = nullptr;
        unsynced.levels = 0;
    }

    /**
     * Clones the given node and all its sub-nodes.
     */
    static Node* clone(const Node* node, int level) {
        // support null-pointers
        if (node == nullptr) {
            return nullptr;
        }

        // create a clone
        auto* res = new Node();

        // handle leaf level
        if (level == 0) {
            copy_op copy;
            for (int i = 0; i < NUM_CELLS; i++) {
                res->cell[i].value = copy(node->cell[i].value);
            }
            return res;
        }

        // for inner nodes clone each child
        for (int i = 0; i < NUM_CELLS; i++) {
            auto cur = clone(node->cell[i].ptr, level - 1);
            if (cur != nullptr) {
                cur->parent = res;
            }
            res->cell[i].ptr = cur;
        }

        // done
        return res;
    }

    /**
     * Obtains the left-most leaf-node of the tree rooted by the given node
     * with the given level.
     */
    static Node* findFirst(Node* node, int level) {
        while (level > 0) {
            [[maybe_unused]] bool found = false;
            for (int i = 0; i < NUM_CELLS; i++) {
                Node* cur = node->cell[i].ptr;
                if (cur) {
                    node = cur;
                    --level;
                    found = true;
                    break;
                }
            }
            assert(found && "No first node!");
        }

        return node;
    }

    /**
     * Raises the level of this tree by one level. It does so by introducing
     * a new root node and inserting the current root node as a child node.
     */
    void raiseLevel() {
        // something went wrong when we pass that line
        assert(unsynced.levels < (sizeof(index_type) * 8 / BITS) + 1);

        // create new root
        Node* node = newNode();
        node->parent = nullptr;

        // insert existing root as child
        auto x = getIndex(brie_element_type(unsynced.offset), unsynced.levels + 1);
        node->cell[x].ptr = unsynced.root;

        // swap the root
        unsynced.root->parent = node;

        // update root
        unsynced.root = node;
        ++unsynced.levels;

        // update offset be removing additional bits
        unsynced.offset &= getLevelMask(unsynced.levels + 1);
    }

    /**
     * Attempts to raise the height of this tree based on the given root node
     * information and updates the root-info snapshot correspondingly.
     */
    void raiseLevel(RootInfoSnapshot& info) {
        // something went wrong when we pass that line
        assert(info.levels < (sizeof(index_type) * 8 / BITS) + 1);

        // create new root
        Node* newRoot = newNode();
        newRoot->parent = nullptr;

        // insert existing root as child
        auto x = getIndex(brie_element_type(info.offset), info.levels + 1);
        newRoot->cell[x].ptr = info.root;

        // exchange the root in the info struct
        auto oldRoot = info.root;
        info.root = newRoot;

        // update level counter
        ++info.levels;

        // update offset
        info.offset &= getLevelMask(info.levels + 1);

        // try exchanging root info
        if (tryUpdateRootInfo(info)) {
            // success => final step, update parent of old root
            oldRoot->parent = info.root;
        } else {
            // throw away temporary new node
            delete newRoot;
        }
    }

    /**
     * Tests whether the given index is covered by the boundaries defined
     * by the hight and offset of the internally maintained tree.
     */
    bool inBoundaries(index_type a) const {
        return inBoundaries(a, unsynced.levels, unsynced.offset);
    }

    /**
     * Tests whether the given index is within the boundaries defined by the
     * given tree hight and offset.
     */
    static bool inBoundaries(index_type a, uint32_t levels, index_type offset) {
        auto mask = getLevelMask(levels + 1);
        return (a & mask) == offset;
    }

    /**
     * Obtains the index within the arrays of cells of a given index on a given
     * level of the internally maintained tree.
     */
    static index_type getIndex(brie_element_type a, unsigned level) {
        return (a & (INDEX_MASK << (level * BIT_PER_STEP))) >> (level * BIT_PER_STEP);
    }

    /**
     * Computes the bit-mask to be applicable to obtain the offset of a node on a
     * given tree level.
     */
    static index_type getLevelMask(unsigned level) {
        if (level > (sizeof(index_type) * 8 / BITS)) return 0;
        return (~(index_type(0)) << (level * BIT_PER_STEP));
    }
};

namespace detail::brie {

/**
 * Iterator type for `souffle::SparseArray`. It enumerates the indices set to 1.
 */
template <typename SparseBitMap>
class SparseBitMapIter {
    using value_t = typename SparseBitMap::value_t;
    using value_type = typename SparseBitMap::index_type;
    using data_store_t = typename SparseBitMap::data_store_t;
    using nested_iterator = typename data_store_t::iterator;

    // the iterator through the underlying sparse data structure
    nested_iterator iter;

    // the currently consumed mask
    uint64_t mask = 0;

    // the value currently pointed to
    value_type value{};

public:
    SparseBitMapIter() = default;  // default constructor -- creating an end-iterator
    SparseBitMapIter(const SparseBitMapIter&) = default;
    SparseBitMapIter& operator=(const SparseBitMapIter&) = default;

    SparseBitMapIter(const nested_iterator& iter)
            : iter(iter), mask(SparseBitMap::toMask(iter->second)),
              value(iter->first << SparseBitMap::LEAF_INDEX_WIDTH) {
        moveToNextInMask();
    }

    SparseBitMapIter(const nested_iterator& iter, uint64_t m, value_type value)
            : iter(iter), mask(m), value(value) {}

    // the equality operator as required by the iterator concept
    bool operator==(const SparseBitMapIter& other) const {
        // only equivalent if pointing to the end
        return iter == other.iter && mask == other.mask;
    }

    // the not-equality operator as required by the iterator concept
    bool operator!=(const SparseBitMapIter& other) const {
        return !(*this == other);
    }

    // the deref operator as required by the iterator concept
    const value_type& operator*() const {
        return value;
    }

    // support for the pointer operator
    const value_type* operator->() const {
        return &value;
    }

    // the increment operator as required by the iterator concept
    SparseBitMapIter& operator++() {
        // progress in current mask
        if (moveToNextInMask()) return *this;

        // go to next entry
        ++iter;

        // update value
        if (!iter.isEnd()) {
            value = iter->first << SparseBitMap::LEAF_INDEX_WIDTH;
            mask = SparseBitMap::toMask(iter->second);
            moveToNextInMask();
        }

        // done
        return *this;
    }

    SparseBitMapIter operator++(int) {
        auto cpy = *this;
        ++(*this);
        return cpy;
    }

    bool isEnd() const {
        return iter.isEnd();
    }

    void print(std::ostream& out) const {
        out << "SparseBitMapIter(" << iter << " -> " << std::bitset<64>(mask) << " @ " << value << ")";
    }

    // enables this iterator core to be printed (for debugging)
    friend std::ostream& operator<<(std::ostream& out, const SparseBitMapIter& iter) {
        iter.print(out);
        return out;
    }

private:
    bool moveToNextInMask() {
        // check if there is something left
        if (mask == 0) return false;

        // get position of leading 1
        auto pos = __builtin_ctzll(mask);

        // consume this bit
        mask &= ~(1llu << pos);

        // update value
        value &= ~SparseBitMap::LEAF_INDEX_MASK;
        value |= pos;

        // done
        return true;
    }
};

}  // namespace detail::brie

/**
 * A sparse bit-map is a bit map virtually assigning a bit value to every value if the
 * uint64_t domain. However, only 1-bits are stored utilizing a nested sparse array
 * structure.
 *
 * @tparam BITS similar to the BITS parameter of the sparse array type
 */
template <unsigned BITS = 4>
class SparseBitMap {
    template <typename A>
    friend class detail::brie::SparseBitMapIter;

    using this_t = SparseBitMap<BITS>;

    // the element type stored in the nested sparse array
    using value_t = uint64_t;

    // define the bit-level merge operation
    struct merge_op {
        value_t operator()(value_t a, value_t b) const {
            return a | b;  // merging bit masks => bitwise or operation
        }
    };

    // the type of the internal data store
    using data_store_t = SparseArray<value_t, BITS, merge_op>;
    using atomic_value_t = typename data_store_t::atomic_value_type;

    // some constants for manipulating stored values
    static constexpr std::size_t BITS_PER_ENTRY = sizeof(value_t) * CHAR_BIT;
    static constexpr std::size_t LEAF_INDEX_WIDTH = __builtin_ctz(static_cast<unsigned long>(BITS_PER_ENTRY));
    static constexpr uint64_t LEAF_INDEX_MASK = BITS_PER_ENTRY - 1;

    static uint64_t toMask(const value_t& value) {
        static_assert(sizeof(value_t) == sizeof(uint64_t), "Fixed for 64-bit compiler.");
        return reinterpret_cast<const uint64_t&>(value);
    }

public:
    // the type to address individual entries
    using index_type = typename data_store_t::index_type;

private:
    // it utilizes a sparse map to store its data
    data_store_t store;

public:
    // a simple default constructor
    SparseBitMap() = default;

    // a default copy constructor
    SparseBitMap(const SparseBitMap&) = default;

    // a default r-value copy constructor
    SparseBitMap(SparseBitMap&&) = default;

    // a default assignment operator
    SparseBitMap& operator=(const SparseBitMap&) = default;

    // a default r-value assignment operator
    SparseBitMap& operator=(SparseBitMap&&) = default;

    // checks whether this bit-map is empty -- thus it does not have any 1-entries
    bool empty() const {
        return store.empty();
    }

    // the type utilized for recording context information for exploiting temporal locality
    using op_context = typename data_store_t::op_context;

    /**
     * Sets the bit addressed by i to 1.
     */
    bool set(index_type i) {
        op_context ctxt;
        return set(i, ctxt);
    }

    /**
     * Sets the bit addressed by i to 1. A context for exploiting temporal locality
     * can be provided.
     */
    bool set(index_type i, op_context& ctxt) {
        atomic_value_t& val = store.getAtomic(i >> LEAF_INDEX_WIDTH, ctxt);
        value_t bit = (1ull << (i & LEAF_INDEX_MASK));

#ifdef __GNUC__
#if __GNUC__ >= 7
        // In GCC >= 7 the usage of fetch_or causes a bug that needs further investigation
        // For now, this two-instruction based implementation provides a fix that does
        // not sacrifice too much performance.

        while (true) {
            auto order = std::memory_order::memory_order_relaxed;

            // load current value
            value_t old = val.load(order);

            // if bit is already set => we are done
            if (old & bit) return false;

            // set the bit, if failed, repeat
            if (!val.compare_exchange_strong(old, old | bit, order, order)) continue;

            // it worked, new bit added
            return true;
        }

#endif
#endif

        value_t old = val.fetch_or(bit, std::memory_order::memory_order_relaxed);
        return (old & bit) == 0u;
    }

    /**
     * Determines the whether the bit addressed by i is set or not.
     */
    bool test(index_type i) const {
        op_context ctxt;
        return test(i, ctxt);
    }

    /**
     * Determines the whether the bit addressed by i is set or not. A context for
     * exploiting temporal locality can be provided.
     */
    bool test(index_type i, op_context& ctxt) const {
        value_t bit = (1ull << (i & LEAF_INDEX_MASK));
        return store.lookup(i >> LEAF_INDEX_WIDTH, ctxt) & bit;
    }

    /**
     * Determines the whether the bit addressed by i is set or not.
     */
    bool operator[](index_type i) const {
        return test(i);
    }

    /**
     * Resets all contained bits to 0.
     */
    void clear() {
        store.clear();
    }

    /**
     * Determines the number of bits set.
     */
    std::size_t size() const {
        // this is computed on demand to keep the set operation simple.
        std::size_t res = 0;
        for (const auto& cur : store) {
            res += __builtin_popcountll(cur.second);
        }
        return res;
    }

    /**
     * Computes the total memory usage of this data structure.
     */
    std::size_t getMemoryUsage() const {
        // compute the total memory usage
        return sizeof(*this) - sizeof(data_store_t) + store.getMemoryUsage();
    }

    /**
     * Sets all bits set in other to 1 within this bit map.
     */
    void addAll(const SparseBitMap& other) {
        // nothing to do if it is a self-assignment
        if (this == &other) return;

        // merge the sparse store
        store.addAll(other.store);
    }

    // ---------------------------------------------------------------------
    //                           Iterator
    // ---------------------------------------------------------------------

    using iterator = SparseBitMapIter<this_t>;

    /**
     * Obtains an iterator pointing to the first index set to 1. If there
     * is no such bit, end() will be returned.
     */
    iterator begin() const {
        auto it = store.begin();
        if (it.isEnd()) return end();
        return iterator(it);
    }

    /**
     * Returns an iterator referencing the position after the last set bit.
     */
    iterator end() const {
        return iterator();
    }

    /**
     * Obtains an iterator referencing the position i if the corresponding
     * bit is set, end() otherwise.
     */
    iterator find(index_type i) const {
        op_context ctxt;
        return find(i, ctxt);
    }

    /**
     * Obtains an iterator referencing the position i if the corresponding
     * bit is set, end() otherwise. An operation context can be provided
     * to exploit temporal locality.
     */
    iterator find(index_type i, op_context& ctxt) const {
        // check prefix part
        auto it = store.find(i >> LEAF_INDEX_WIDTH, ctxt);
        if (it.isEnd()) return end();

        // check bit-set part
        uint64_t mask = toMask(it->second);
        if (!(mask & (1llu << (i & LEAF_INDEX_MASK)))) return end();

        // OK, it is there => create iterator
        mask &= ((1ull << (i & LEAF_INDEX_MASK)) - 1);  // remove all bits before pos i
        return iterator(it, mask, i);
    }

    /**
     * Locates an iterator to the first element in this sparse bit map not less
     * than the given index.
     */
    iterator lower_bound(index_type i) const {
        auto it = store.lowerBound(i >> LEAF_INDEX_WIDTH);
        if (it.isEnd()) return end();

        // check bit-set part
        uint64_t mask = toMask(it->second);

        // if there is no bit remaining in this mask, check next mask.
        if (!(mask & ((~uint64_t(0)) << (i & LEAF_INDEX_MASK)))) {
            index_type next = ((i >> LEAF_INDEX_WIDTH) + 1) << LEAF_INDEX_WIDTH;
            if (next < i) return end();
            return lower_bound(next);
        }

        // there are bits left, use least significant bit of those
        if (it->first == i >> LEAF_INDEX_WIDTH) {
            mask &= ((~uint64_t(0)) << (i & LEAF_INDEX_MASK));  // remove all bits before pos i
        }

        // compute value represented by least significant bit
        index_type pos = __builtin_ctzll(mask);

        // remove this bit as well
        mask = mask & ~(1ull << pos);

        // construct value of this located bit
        index_type val = (it->first << LEAF_INDEX_WIDTH) | pos;
        return iterator(it, mask, val);
    }

    /**
     * Locates an iterator to the first element in this sparse bit map than is greater
     * than the given index.
     */
    iterator upper_bound(index_type i) const {
        if (i == std::numeric_limits<index_type>::max()) {
            return end();
        }
        return lower_bound(i + 1);
    }

    /**
     * A debugging utility printing the internal structure of this map to the
     * given output stream.
     */
    void dump(bool detail = false, std::ostream& out = std::cout) const {
        store.dump(detail, out);
    }

    /**
     * Provides write-protected access to the internal store for running
     * analysis on the data structure.
     */
    const data_store_t& getStore() const {
        return store;
    }
};

// ---------------------------------------------------------------------
//                              TRIE
// ---------------------------------------------------------------------

namespace detail::brie {

/**
 * An iterator over the stored entries.
 *
 * Iterators for tries consist of a top-level iterator maintaining the
 * master copy of a materialized tuple and a recursively nested iterator
 * core -- one for each nested trie level.
 */
template <typename Value, typename IterCore>
class TrieIterator {
    template <unsigned Len, unsigned Pos, unsigned Dimensions>
    friend struct fix_binding;

    template <unsigned Dimensions>
    friend struct fix_lower_bound;

    template <unsigned Dimensions>
    friend struct fix_upper_bound;

    template <unsigned Pos, unsigned Dimensions>
    friend struct fix_first;

    template <unsigned Dimensions>
    friend struct fix_first_nested;

    template <typename A, typename B>
    friend class TrieIterator;

    // remove ref-qual (if any); this can happen if we're a iterator-view
    using iter_core_arg_type = typename std::remove_reference_t<IterCore>::store_iter;

    Value value = {};         // the value currently pointed to
    IterCore iter_core = {};  // the wrapped iterator

    // return an ephemeral nested iterator-view (view -> mutating us mutates our parent)
    // NB: be careful that the lifetime of this iterator-view doesn't exceed that of its parent.
    auto getNestedView() {
        auto& nested_iter_ref = iter_core.getNested();  // by ref (this is critical, we're a view, not a copy)
        auto nested_val = tail(value);
        return TrieIterator<decltype(nested_val), decltype(nested_iter_ref)>(
                std::move(nested_val), nested_iter_ref);
    }

    // special constructor for iterator-views (see `getNestedView`)
    explicit TrieIterator(Value value, IterCore iter_core) : value(std::move(value)), iter_core(iter_core) {}

public:
    TrieIterator() = default;  // default constructor -- creating an end-iterator
    TrieIterator(const TrieIterator&) = default;
    TrieIterator(TrieIterator&&) = default;
    TrieIterator& operator=(const TrieIterator&) = default;
    TrieIterator& operator=(TrieIterator&&) = default;

    explicit TrieIterator(iter_core_arg_type param) : iter_core(std::move(param), value) {}

    // the equality operator as required by the iterator concept
    bool operator==(const TrieIterator& other) const {
        // equivalent if pointing to the same value
        return iter_core == other.iter_core;
    }

    // the not-equality operator as required by the iterator concept
    bool operator!=(const TrieIterator& other) const {
        return !(*this == other);
    }

    const Value& operator*() const {
        return value;
    }

    const Value* operator->() const {
        return &value;
    }

    TrieIterator& operator++() {
        iter_core.inc(value);
        return *this;
    }

    TrieIterator operator++(int) {
        auto cpy = *this;
        ++(*this);
        return cpy;
    }

    // enables this iterator to be printed (for debugging)
    void print(std::ostream& out) const {
        out << "iter(" << iter_core << " -> " << value << ")";
    }

    friend std::ostream& operator<<(std::ostream& out, const TrieIterator& iter) {
        iter.print(out);
        return out;
    }
};

template <unsigned Dim>
struct TrieTypes;

/**
 * A base class for the Trie implementation allowing various
 * specializations of the Trie template to inherit common functionality.
 *
 * @tparam Dim the number of dimensions / arity of the stored tuples
 * @tparam Derived the type derived from this base class
 */
template <unsigned Dim, typename Derived>
class TrieBase {
    Derived& impl() {
        return static_cast<Derived&>(*this);
    }

    const Derived& impl() const {
        return static_cast<const Derived&>(*this);
    }

protected:
    using types = TrieTypes<Dim>;
    using store_type = typename types::store_type;

    store_type store;

public:
    using const_entry_span_type = typename types::const_entry_span_type;
    using entry_span_type = typename types::entry_span_type;
    using entry_type = typename types::entry_type;
    using iterator = typename types::iterator;
    using iterator_core = typename types::iterator_core;
    using op_context = typename types::op_context;

    /**
     * Inserts all tuples stored within the given trie into this trie.
     * This operation is considerably more efficient than the consecutive
     * insertion of the elements in other into this trie.
     *
     * @param other the elements to be inserted into this trie
     */
    void insertAll(const TrieBase& other) {
        store.addAll(other.store);
    }

    /**
     * Provides protected access to the internally maintained store.
     */
    const store_type& getStore() const {
        return store;
    }

    /**
     * Determines whether this trie is empty or not.
     */
    bool empty() const {
        return store.empty();
    }

    /**
     * Obtains an iterator referencing the first element stored within this trie.
     */
    iterator begin() const {
        return empty() ? end() : iterator(store.begin());
    }

    /**
     * Obtains an iterator referencing the position after the last element stored
     * within this trie.
     */
    iterator end() const {
        return iterator();
    }

    iterator find(const_entry_span_type entry, op_context& ctxt) const {
        auto range = impl().template getBoundaries<Dim>(entry, ctxt);
        return range.empty() ? range.end() : range.begin();
    }

    // implemented by `Derived`:
    //      bool insert(const entry_type& tuple, op_context& ctxt);
    //      bool contains(const_entry_span_type tuple, op_context& ctxt) const;
    //      bool lower_bound(const_entry_span_type tuple, op_context& ctxt) const;
    //      bool upper_bound(const_entry_span_type tuple, op_context& ctxt) const;
    //      template <unsigned levels>
    //      range<iterator> getBoundaries(const_entry_span_type, op_context&) const;

    // -- operation wrappers --

    template <unsigned levels>
    range<iterator> getBoundaries(const_entry_span_type entry) const {
        op_context ctxt;
        return impl().template getBoundaries<levels>(entry, ctxt);
    }

    template <unsigned levels>
    range<iterator> getBoundaries(const entry_type& entry, op_context& ctxt) const {
        return impl().template getBoundaries<levels>(const_entry_span_type(entry), ctxt);
    }

    template <unsigned levels>
    range<iterator> getBoundaries(const entry_type& entry) const {
        return impl().template getBoundaries<levels>(const_entry_span_type(entry));
    }

    template <unsigned levels, typename... Values, typename = std::enable_if_t<(isRamType<Values> && ...)>>
    range<iterator> getBoundaries(Values... values) const {
        return impl().template getBoundaries<levels>(entry_type{ramBitCast(values)...});
    }

// declare a initialiser-list compatible overload for a given function
#define BRIE_OVERLOAD_INIT_LIST(fn, constness)                     \
    auto fn(const_entry_span_type entry) constness {               \
        op_context ctxt;                                           \
        return impl().fn(entry, ctxt);                             \
    }                                                              \
    auto fn(const entry_type& entry, op_context& ctxt) constness { \
        return impl().fn(const_entry_span_type(entry), ctxt);      \
    }                                                              \
    auto fn(const entry_type& entry) constness {                   \
        return impl().fn(const_entry_span_type(entry));            \
    }

    BRIE_OVERLOAD_INIT_LIST(insert, )
    BRIE_OVERLOAD_INIT_LIST(find, const)
    BRIE_OVERLOAD_INIT_LIST(contains, const)
    BRIE_OVERLOAD_INIT_LIST(lower_bound, const)
    BRIE_OVERLOAD_INIT_LIST(upper_bound, const)

#undef BRIE_OVERLOAD_INIT_LIST

    /* -------------- operator hint statistics ----------------- */

    // an aggregation of statistical values of the hint utilization
    struct hint_statistics {
        // the counter for insertion operations
        CacheAccessCounter inserts;

        // the counter for contains operations
        CacheAccessCounter contains;

        // the counter for get_boundaries operations
        CacheAccessCounter get_boundaries;
    };

protected:
    // the hint statistic of this b-tree instance
    mutable hint_statistics hint_stats;

public:
    void printStats(std::ostream& out) const {
        out << "---------------------------------\n";
        out << "  insert-hint (hits/misses/total): " << hint_stats.inserts.getHits() << "/"
            << hint_stats.inserts.getMisses() << "/" << hint_stats.inserts.getAccesses() << "\n";
        out << "  contains-hint (hits/misses/total):" << hint_stats.contains.getHits() << "/"
            << hint_stats.contains.getMisses() << "/" << hint_stats.contains.getAccesses() << "\n";
        out << "  get-boundaries-hint (hits/misses/total):" << hint_stats.get_boundaries.getHits() << "/"
            << hint_stats.get_boundaries.getMisses() << "/" << hint_stats.get_boundaries.getAccesses()
            << "\n";
        out << "---------------------------------\n";
    }
};

template <unsigned Dim>
struct TrieTypes;

// FIXME: THIS KILLS COMPILE PERF - O(n^2)
/**
 * A functor extracting a reference to a nested iterator core from an enclosing
 * iterator core.
 */
template <unsigned Level>
struct get_nested_iter_core {
    template <typename IterCore>
    auto operator()(IterCore& core) -> decltype(get_nested_iter_core<Level - 1>()(core.getNested())) {
        return get_nested_iter_core<Level - 1>()(core.getNested());
    }
};

template <>
struct get_nested_iter_core<0> {
    template <typename IterCore>
    IterCore& operator()(IterCore& core) {
        return core;
    }
};

// FIXME: THIS KILLS COMPILE PERF - O(n^2)
/**
 * A functor initializing an iterator upon creation to reference the first
 * element in the associated Trie.
 */
template <unsigned Pos, unsigned Dim>
struct fix_first {
    template <unsigned bits, typename iterator>
    void operator()(const SparseBitMap<bits>& store, iterator& iter) const {
        // set iterator to first in store
        auto first = store.begin();
        get_nested_iter_core<Pos>()(iter.iter_core).setIterator(first);
        iter.value[Pos] = *first;
    }

    template <typename Store, typename iterator>
    void operator()(const Store& store, iterator& iter) const {
        // set iterator to first in store
        auto first = store.begin();
        get_nested_iter_core<Pos>()(iter.iter_core).setIterator(first);
        iter.value[Pos] = first->first;
        // and continue recursively
        fix_first<Pos + 1, Dim>()(first->second->getStore(), iter);
    }
};

template <unsigned Dim>
struct fix_first<Dim, Dim> {
    template <typename Store, typename iterator>
    void operator()(const Store&, iterator&) const {
        // terminal case => nothing to do
    }
};

template <unsigned Dim>
struct fix_first_nested {
    template <unsigned bits, typename iterator>
    void operator()(const SparseBitMap<bits>& store, iterator&& iter) const {
        // set iterator to first in store
        auto first = store.begin();
        iter.value[0] = *first;
        iter.iter_core.setIterator(std::move(first));
    }

    template <typename Store, typename iterator>
    void operator()(const Store& store, iterator&& iter) const {
        // set iterator to first in store
        auto first = store.begin();
        iter.value[0] = first->first;
        iter.iter_core.setIterator(std::move(first));
        // and continue recursively
        fix_first_nested<Dim - 1>()(first->second->getStore(), iter.getNestedView());
    }
};

// TODO: rewrite to erase `Pos` and `Len` arguments. this can cause a template instance explosion
/**
 * A functor initializing an iterator upon creation to reference the first element
 * exhibiting a given prefix within a given Trie.
 */
template <unsigned Len, unsigned Pos, unsigned Dim>
struct fix_binding {
    template <unsigned bits, typename iterator, typename entry_type>
    bool operator()(
            const SparseBitMap<bits>& store, iterator& begin, iterator& end, const entry_type& entry) const {
        // search in current level
        auto cur = store.find(entry[Pos]);

        // if not present => fail
        if (cur == store.end()) return false;

        // take current value
        get_nested_iter_core<Pos>()(begin.iter_core).setIterator(cur);
        ++cur;
        get_nested_iter_core<Pos>()(end.iter_core).setIterator(cur);

        // update iterator value
        begin.value[Pos] = entry[Pos];

        // no more remaining levels to fix
        return true;
    }

    template <typename Store, typename iterator, typename entry_type>
    bool operator()(const Store& store, iterator& begin, iterator& end, const entry_type& entry) const {
        // search in current level
        auto cur = store.find(entry[Pos]);

        // if not present => fail
        if (cur == store.end()) return false;

        // take current value as start
        get_nested_iter_core<Pos>()(begin.iter_core).setIterator(cur);

        // update iterator value
        begin.value[Pos] = entry[Pos];

        // fix remaining nested iterators
        auto res = fix_binding<Len - 1, Pos + 1, Dim>()(cur->second->getStore(), begin, end, entry);

        // update end of iterator
        if (get_nested_iter_core<Pos + 1>()(end.iter_core).getIterator() == cur->second->getStore().end()) {
            ++cur;
            if (cur != store.end()) {
                fix_first<Pos + 1, Dim>()(cur->second->getStore(), end);
            }
        }
        get_nested_iter_core<Pos>()(end.iter_core).setIterator(cur);

        // done
        return res;
    }
};

template <unsigned Pos, unsigned Dim>
struct fix_binding<0, Pos, Dim> {
    template <unsigned bits, typename iterator, typename entry_type>
    bool operator()(const SparseBitMap<bits>& store, iterator& begin, iterator& /* end */,
            const entry_type& /* entry */) const {
        // move begin to begin of store
        auto a = store.begin();
        get_nested_iter_core<Pos>()(begin.iter_core).setIterator(a);
        begin.value[Pos] = *a;

        return true;
    }

    template <typename Store, typename iterator, typename entry_type>
    bool operator()(const Store& store, iterator& begin, iterator& end, const entry_type& entry) const {
        // move begin to begin of store
        auto a = store.begin();
        get_nested_iter_core<Pos>()(begin.iter_core).setIterator(a);
        begin.value[Pos] = a->first;

        // continue recursively
        fix_binding<0, Pos + 1, Dim>()(a->second->getStore(), begin, end, entry);
        return true;
    }
};

template <unsigned Dim>
struct fix_binding<0, Dim, Dim> {
    template <typename Store, typename iterator, typename entry_type>
    bool operator()(const Store& /* store */, iterator& /* begin */, iterator& /* end */,
            const entry_type& /* entry */) const {
        // nothing more to do
        return true;
    }
};

/**
 * A functor initializing an iterator upon creation to reference the first element
 * within a given Trie being not less than a given value .
 */
template <unsigned Dim>
struct fix_lower_bound {
    using types = TrieTypes<Dim>;
    using const_entry_span_type = typename types::const_entry_span_type;

    template <unsigned bits, typename iterator>
    bool operator()(const SparseBitMap<bits>& store, iterator&& iter, const_entry_span_type entry) const {
        auto cur = store.lower_bound(entry[0]);
        if (cur == store.end()) return false;
        assert(entry[0] <= brie_element_type(*cur));

        iter.iter_core.setIterator(cur);
        iter.value[0] = *cur;
        return true;
    }

    template <typename Store, typename iterator>
    bool operator()(const Store& store, iterator&& iter, const_entry_span_type entry) const {
        auto cur = store.lowerBound(entry[0]);  // search in current level
        if (cur == store.end()) return false;   // if no lower boundary is found, be done
        assert(brie_element_type(cur->first) >= entry[0]);

        // if the lower bound is higher than the requested value, go to first in subtree
        if (brie_element_type(cur->first) > entry[0]) {
            iter.iter_core.setIterator(cur);
            iter.value[0] = cur->first;
            fix_first_nested<Dim - 1>()(cur->second->getStore(), iter.getNestedView());
            return true;
        }

        // attempt to fix the rest
        if (!fix_lower_bound<Dim - 1>()(cur->second->getStore(), iter.getNestedView(), tail(entry))) {
            // if it does not work, since there are no matching elements in this branch, go to next
            auto sub = copy(entry);
            sub[0] += 1;
            for (std::size_t i = 1; i < Dim; ++i)
                sub[i] = 0;

            return (*this)(store, iter, sub);
        }

        iter.iter_core.setIterator(cur);  // remember result
        iter.value[0] = cur->first;       // update iterator value
        return true;
    }
};

/**
 * A functor initializing an iterator upon creation to reference the first element
 * within a given Trie being greater than a given value .
 */
template <unsigned Dim>
struct fix_upper_bound {
    using types = TrieTypes<Dim>;
    using const_entry_span_type = typename types::const_entry_span_type;

    template <unsigned bits, typename iterator>
    bool operator()(const SparseBitMap<bits>& store, iterator&& iter, const_entry_span_type entry) const {
        auto cur = store.upper_bound(entry[0]);
        if (cur == store.end()) return false;
        assert(entry[0] <= brie_element_type(*cur));

        iter.iter_core.setIterator(cur);
        iter.value[0] = *cur;
        return true;  // no more remaining levels to fix
    }

    template <typename Store, typename iterator>
    bool operator()(const Store& store, iterator&& iter, const_entry_span_type entry) const {
        auto cur = store.lowerBound(entry[0]);  // search in current level
        if (cur == store.end()) return false;   // if no upper boundary is found, be done
        assert(brie_element_type(cur->first) >= entry[0]);

        // if the lower bound is higher than the requested value, go to first in subtree
        if (brie_element_type(cur->first) > entry[0]) {
            iter.iter_core.setIterator(cur);
            iter.value[0] = cur->first;
            fix_first_nested<Dim - 1>()(cur->second->getStore(), iter.getNestedView());
            return true;
        }

        // attempt to fix the rest
        if (!fix_upper_bound<Dim - 1>()(cur->second->getStore(), iter.getNestedView(), tail(entry))) {
            // if it does not work, since there are no matching elements in this branch, go to next
            auto sub = copy(entry);
            sub[0] += 1;
            for (std::size_t i = 1; i < Dim; ++i)
                sub[i] = 0;

            return (*this)(store, iter, sub);
        }

        iter.iter_core.setIterator(cur);  // remember result
        iter.value[0] = cur->first;       // update iterator value
        return true;
    }
};

template <unsigned Dim>
struct TrieTypes {
    using entry_type = std::array<brie_element_type, Dim>;
    using entry_span_type = span<brie_element_type, Dim>;
    using const_entry_span_type = span<const brie_element_type, Dim>;

    // the type of the nested tries (1 dimension less)
    using nested_trie_type = Trie<Dim - 1>;

    // the merge operation capable of merging two nested tries
    struct nested_trie_merger {
        nested_trie_type* operator()(nested_trie_type* a, const nested_trie_type* b) const {
            if (!b) return a;
            if (!a) return new nested_trie_type(*b);
            a->insertAll(*b);
            return a;
        }
    };

    // the operation capable of cloning a nested trie
    struct nested_trie_cloner {
        nested_trie_type* operator()(nested_trie_type* a) const {
            if (!a) return a;
            return new nested_trie_type(*a);
        }
    };

    // the data structure utilized for indexing nested tries
    using store_type = SparseArray<nested_trie_type*,
            6,  // = 2^6 entries per block
            nested_trie_merger, nested_trie_cloner>;

    // The iterator core for trie iterators involving this level.
    struct iterator_core {
        using store_iter = typename store_type::iterator;  // the iterator for the current level
        using nested_core_iter = typename nested_trie_type::iterator_core;  // the type of the nested iterator

    private:
        store_iter iter;
        nested_core_iter nested;

    public:
        iterator_core() = default;  // default -> end iterator

        iterator_core(store_iter store_iter, entry_span_type entry) : iter(std::move(store_iter)) {
            entry[0] = iter->first;
            nested = {iter->second->getStore().begin(), tail(entry)};
        }

        void setIterator(store_iter store_iter) {
            iter = std::move(store_iter);
        }

        store_iter& getIterator() {
            return iter;
        }

        nested_core_iter& getNested() {
            return nested;
        }

        bool inc(entry_span_type entry) {
            // increment nested iterator
            auto nested_entry = tail(entry);
            if (nested.inc(nested_entry)) return true;

            // increment the iterator on this level
            ++iter;

            // check whether the end has been reached
            if (iter.isEnd()) return false;

            // otherwise update entry value
            entry[0] = iter->first;

            // and restart nested
            nested = {iter->second->getStore().begin(), nested_entry};
            return true;
        }

        bool operator==(const iterator_core& other) const {
            return nested == other.nested && iter == other.iter;
        }

        bool operator!=(const iterator_core& other) const {
            return !(*this == other);
        }

        // enables this iterator core to be printed (for debugging)
        void print(std::ostream& out) const {
            out << iter << " | " << nested;
        }

        friend std::ostream& operator<<(std::ostream& out, const iterator_core& iter) {
            iter.print(out);
            return out;
        }
    };

    using iterator = TrieIterator<entry_type, iterator_core>;

    // the operation context aggregating all operation contexts of nested structures
    struct op_context {
        using local_ctxt = typename store_type::op_context;
        using nested_ctxt = typename nested_trie_type::op_context;

        // for insert and contain
        local_ctxt local{};
        brie_element_type lastQuery{};
        nested_trie_type* lastNested{nullptr};
        nested_ctxt nestedCtxt{};

        // for boundaries
        unsigned lastBoundaryLevels{Dim + 1};
        entry_type lastBoundaryRequest{};
        range<iterator> lastBoundaries{iterator(), iterator()};
    };
};

template <>
struct TrieTypes<1u> {
    using entry_type = std::array<brie_element_type, 1>;
    using entry_span_type = span<brie_element_type, 1>;
    using const_entry_span_type = span<const brie_element_type, 1>;

    // the map type utilized internally
    using store_type = SparseBitMap<>;
    using op_context = store_type::op_context;

    /**
     * The iterator core of this level contributing to the construction of
     * a composed trie iterator.
     */
    struct iterator_core {
        using store_iter = typename store_type::iterator;

    private:
        store_iter iter;

    public:
        iterator_core() = default;  // default end-iterator constructor

        iterator_core(store_iter store_iter, entry_span_type entry)
                : iter(std::move(store_iter))  // NOLINT : mistaken warning -`store_iter` is not const-qual
        {
            entry[0] = brie_element_type(*iter);
        }

        void setIterator(store_iter store_iter) {
            iter = std::move(store_iter);  // NOLINT : mistaken warning - `store_iter` is not const-qual
        }

        store_iter& getIterator() {
            return iter;
        }

        bool inc(entry_span_type entry) {
            // increment the iterator on this level
            ++iter;

            // check whether the end has been reached
            if (iter.isEnd()) return false;

            // otherwise update entry value
            entry[0] = brie_element_type(*iter);
            return true;
        }

        bool operator==(const iterator_core& other) const {
            return iter == other.iter;
        }

        bool operator!=(const iterator_core& other) const {
            return !(*this == other);
        }

        // enables this iterator core to be printed (for debugging)
        void print(std::ostream& out) const {
            out << iter;
        }

        friend std::ostream& operator<<(std::ostream& out, const iterator_core& iter) {
            iter.print(out);
            return out;
        }
    };

    using iterator = TrieIterator<entry_type, iterator_core>;
};

}  // namespace detail::brie

// use an inner class so `TrieN` is fully defined before the recursion, allowing us to use
// `op_context` in `TrieBase`
template <unsigned Dim>
class Trie : public TrieBase<Dim, Trie<Dim>> {
    template <unsigned N>
    friend class Trie;

    // a shortcut for the common base class type
    using base = TrieBase<Dim, Trie<Dim>>;
    using types = TrieTypes<Dim>;
    using nested_trie_type = typename types::nested_trie_type;
    using store_type = typename types::store_type;

    using base::store;

public:
    using const_entry_span_type = typename types::const_entry_span_type;
    using entry_span_type = typename types::entry_span_type;
    using entry_type = typename types::entry_type;
    using iterator = typename types::iterator;
    using iterator_core = typename types::iterator_core;
    using op_context = typename types::op_context;
    // type aliases for compatibility with `BTree` and others
    using operation_hints = op_context;
    using element_type = entry_type;

    using base::begin;
    using base::contains;
    using base::empty;
    using base::end;
    using base::find;
    using base::getBoundaries;
    using base::insert;
    using base::lower_bound;
    using base::upper_bound;

    ~Trie() {
        clear();
    }

    /**
     * Determines the number of entries in this trie.
     */
    std::size_t size() const {
        // the number of elements is lazy-evaluated
        std::size_t res = 0;
        for (auto&& [_, v] : store)
            res += v->size();

        return res;
    }

    /**
     * Computes the total memory usage of this data structure.
     */
    std::size_t getMemoryUsage() const {
        // compute the total memory usage of this level
        auto res = sizeof(*this) - sizeof(store) + store.getMemoryUsage();
        for (auto&& [_, v] : store)
            res += v->getMemoryUsage();  // add the memory usage of sub-levels

        return res;
    }

    /**
     * Removes all entries within this trie.
     */
    void clear() {
        // delete lower levels manually
        // (can't use `Own` b/c we need `atomic` instances and those require trivial assignment)
        for (auto& cur : store)
            delete cur.second;

        // clear store
        store.clear();
    }

    /**
     * Inserts a new entry. A operation context may be provided to exploit temporal
     * locality.
     *
     * @param tuple the entry to be added
     * @param ctxt the operation context to be utilized
     * @return true if the same tuple hasn't been present before, false otherwise
     */
    bool insert(const_entry_span_type tuple, op_context& ctxt) {
        using value_t = typename store_type::value_type;
        using atomic_value_t = typename store_type::atomic_value_type;

        // check context
        if (ctxt.lastNested && ctxt.lastQuery == tuple[0]) {
            base::hint_stats.inserts.addHit();
            return ctxt.lastNested->insert(tail(tuple), ctxt.nestedCtxt);
        }

        base::hint_stats.inserts.addMiss();

        // lookup nested
        atomic_value_t& next = store.getAtomic(tuple[0], ctxt.local);

        // get pure pointer to next level
        value_t nextPtr = next;

        // conduct a lock-free lazy-creation of nested trees
        if (!nextPtr) {
            // create a sub-tree && register it atomically
            auto newNested = mk<nested_trie_type>();
            if (next.compare_exchange_weak(nextPtr, newNested.get())) {
                nextPtr = newNested.release();  // worked, ownership is acquired by `store`
            }
            // otherwise some other thread was faster => use its version
        }

        // make sure a next has been established
        assert(nextPtr);

        // clear context if necessary
        if (nextPtr != ctxt.lastNested) {
            ctxt.lastQuery = tuple[0];
            ctxt.lastNested = nextPtr;
            ctxt.nestedCtxt = {};
        }

        // conduct recursive step
        return nextPtr->insert(tail(tuple), ctxt.nestedCtxt);
    }

    bool contains(const_entry_span_type tuple, op_context& ctxt) const {
        // check context
        if (ctxt.lastNested && ctxt.lastQuery == tuple[0]) {
            base::hint_stats.contains.addHit();
            return ctxt.lastNested->contains(tail(tuple), ctxt.nestedCtxt);
        }

        base::hint_stats.contains.addMiss();

        // lookup next step
        auto next = store.lookup(tuple[0], ctxt.local);

        // clear context if necessary
        if (next != ctxt.lastNested) {
            ctxt.lastQuery = tuple[0];
            ctxt.lastNested = next;
            ctxt.nestedCtxt = {};
        }

        // conduct recursive step
        return next && next->contains(tail(tuple), ctxt.nestedCtxt);
    }

    /**
     * Obtains a range of elements matching the prefix of the given entry up to
     * levels elements. A operation context may be provided to exploit temporal
     * locality.
     *
     * @tparam levels the length of the requested matching prefix
     * @param entry the entry to be looking for
     * @param ctxt the operation context to be utilized
     * @return the corresponding range of matching elements
     */
    template <unsigned levels>
    range<iterator> getBoundaries(const_entry_span_type entry, op_context& ctxt) const {
        // if nothing is bound => just use begin and end
        if constexpr (levels == 0) {
            return make_range(begin(), end());
        } else {  // HACK: explicit `else` branch b/c OSX compiler doesn't do DCE before `0 < limit` warning
            // check context
            if (ctxt.lastBoundaryLevels == levels) {
                bool fit = true;
                for (unsigned i = 0; i < levels; ++i) {
                    fit = fit && (entry[i] == ctxt.lastBoundaryRequest[i]);
                }

                // if it fits => take it
                if (fit) {
                    base::hint_stats.get_boundaries.addHit();
                    return ctxt.lastBoundaries;
                }
            }

            // the hint has not been a hit
            base::hint_stats.get_boundaries.addMiss();

            // start with two end iterators
            iterator begin{};
            iterator end{};

            // adapt them level by level
            auto found = fix_binding<levels, 0, Dim>()(store, begin, end, entry);
            if (!found) return make_range(iterator(), iterator());

            // update context
            static_assert(std::tuple_size_v<decltype(ctxt.lastBoundaryRequest)> == Dim);
            static_assert(std::tuple_size_v<decltype(entry)> == Dim);
            ctxt.lastBoundaryLevels = levels;
            std::copy_n(entry.begin(), Dim, ctxt.lastBoundaryRequest.begin());
            ctxt.lastBoundaries = make_range(begin, end);

            // use the result
            return ctxt.lastBoundaries;
        }
    }

    /**
     * Obtains an iterator to the first element not less than the given entry value.
     *
     * @param entry the lower bound for this search
     * @param ctxt the operation context to be utilized
     * @return an iterator addressing the first element in this structure not less than the given value
     */
    iterator lower_bound(const_entry_span_type entry, op_context& /* ctxt */) const {
        // start with a default-initialized iterator
        iterator res;

        // adapt it level by level
        bool found = fix_lower_bound<Dim>()(store, res, entry);

        // use the result
        return found ? res : end();
    }

    /**
     * Obtains an iterator to the first element greater than the given entry value, or end if there is no
     * such element.
     *
     * @param entry the upper bound for this search
     * @param ctxt the operation context to be utilized
     * @return an iterator addressing the first element in this structure greater than the given value
     */
    iterator upper_bound(const_entry_span_type entry, op_context& /* ctxt */) const {
        // start with a default-initialized iterator
        iterator res;

        // adapt it level by level
        bool found = fix_upper_bound<Dim>()(store, res, entry);

        // use the result
        return found ? res : end();
    }

    /**
     * Computes a partition of an approximate number of chunks of the content
     * of this trie. Thus, the union of the resulting set of disjoint ranges is
     * equivalent to the content of this trie.
     *
     * @param chunks the number of chunks requested
     * @return a list of sub-ranges forming a partition of the content of this trie
     */
    std::vector<range<iterator>> partition(unsigned chunks = 500) const {
        std::vector<range<iterator>> res;

        // shortcut for empty trie
        if (this->empty()) return res;

        // use top-level elements for partitioning
        size_t step = std::max(store.size() / chunks, std::size_t(1));

        size_t c = 1;
        auto priv = begin();
        for (auto it = store.begin(); it != store.end(); ++it, c++) {
            if (c % step != 0 || c == 1) {
                continue;
            }
            auto cur = iterator(it);
            res.push_back(make_range(priv, cur));
            priv = cur;
        }
        // add final chunk
        res.push_back(make_range(priv, end()));
        return res;
    }
};

/**
 * A template specialization for tries representing a set.
 * For improved memory efficiency, this level is the leaf-node level
 * of all tries exhibiting an arity >= 1. Internally, values are stored utilizing
 * sparse bit maps.
 */
template <>
class Trie<1u> : public TrieBase<1u, Trie<1u>> {
    using base = TrieBase<1u, Trie<1u>>;
    using types = TrieTypes<1u>;
    using store_type = typename types::store_type;

    using base::store;

public:
    using const_entry_span_type = typename types::const_entry_span_type;
    using entry_span_type = typename types::entry_span_type;
    using entry_type = typename types::entry_type;
    using iterator = typename types::iterator;
    using iterator_core = typename types::iterator_core;
    using op_context = typename types::op_context;
    // type aliases for compatibility with `BTree` and others
    using operation_hints = op_context;
    using element_type = entry_type;

    using base::begin;
    using base::contains;
    using base::empty;
    using base::end;
    using base::find;
    using base::getBoundaries;
    using base::insert;
    using base::lower_bound;
    using base::upper_bound;

    /**
     * Determines the number of entries in this trie.
     */
    std::size_t size() const {
        return store.size();
    }

    /**
     * Computes the total memory usage of this data structure.
     */
    std::size_t getMemoryUsage() const {
        // compute the total memory usage
        return sizeof(*this) - sizeof(store) + store.getMemoryUsage();
    }

    /**
     * Removes all elements form this trie.
     */
    void clear() {
        store.clear();
    }

    /**
     * Inserts the given tuple into this trie.
     * An operation context can be provided to exploit temporal locality.
     *
     * @param tuple the tuple to be inserted
     * @param ctxt an operation context for exploiting temporal locality
     * @return true if the tuple has not been present before, false otherwise
     */
    bool insert(const_entry_span_type tuple, op_context& ctxt) {
        return store.set(tuple[0], ctxt);
    }

    /**
     * Determines whether the given tuple is present in this trie or not.
     * An operation context can be provided to exploit temporal locality.
     *
     * @param tuple the tuple to be tested
     * @param ctxt an operation context for exploiting temporal locality
     * @return true if present, false otherwise
     */
    bool contains(const_entry_span_type tuple, op_context& ctxt) const {
        return store.test(tuple[0], ctxt);
    }

    // ---------------------------------------------------------------------
    //                           Iterator
    // ---------------------------------------------------------------------

    /**
     * Obtains a partition of this tire such that the resulting list of ranges
     * cover disjoint subsets of the elements stored in this trie. Their union
     * is equivalent to the content of this trie.
     */
    std::vector<range<iterator>> partition(unsigned chunks = 500) const {
        std::vector<range<iterator>> res;

        // shortcut for empty trie
        if (this->empty()) return res;

        // use top-level elements for partitioning
        int step = static_cast<int>(std::max(store.size() / chunks, std::size_t(1)));

        int c = 1;
        auto priv = begin();
        for (auto it = store.begin(); it != store.end(); ++it, c++) {
            if (c % step != 0 || c == 1) {
                continue;
            }
            auto cur = iterator(it);
            res.push_back(make_range(priv, cur));
            priv = cur;
        }
        // add final chunk
        res.push_back(make_range(priv, end()));
        return res;
    }

    /**
     * Obtains a range of elements matching the prefix of the given entry up to
     * levels elements. A operation context may be provided to exploit temporal
     * locality.
     *
     * @tparam levels the length of the requested matching prefix
     * @param entry the entry to be looking for
     * @param ctxt the operation context to be utilized
     * @return the corresponding range of matching elements
     */
    template <unsigned levels>
    range<iterator> getBoundaries(const_entry_span_type entry, op_context& ctxt) const {
        // for levels = 0
        if (levels == 0) return make_range(begin(), end());
        // for levels = 1
        auto pos = store.find(entry[0], ctxt);
        if (pos == store.end()) return make_range(end(), end());
        auto next = pos;
        ++next;
        return make_range(iterator(pos), iterator(next));
    }

    iterator lower_bound(const_entry_span_type entry, op_context&) const {
        return iterator(store.lower_bound(entry[0]));
    }

    iterator upper_bound(const_entry_span_type entry, op_context&) const {
        return iterator(store.upper_bound(entry[0]));
    }
};

}  // end namespace souffle

namespace std {

using namespace ::souffle::detail::brie;

template <typename A>
struct iterator_traits<SparseArrayIter<A>>
        : forward_non_output_iterator_traits<typename SparseArrayIter<A>::value_type> {};

template <typename A>
struct iterator_traits<SparseBitMapIter<A>>
        : forward_non_output_iterator_traits<typename SparseBitMapIter<A>::value_type> {};

template <typename A, typename IterCore>
struct iterator_traits<TrieIterator<A, IterCore>> : forward_non_output_iterator_traits<A> {};

}  // namespace std

#ifdef _WIN32
#undef __sync_synchronize
#undef __sync_bool_compare_and_swap
#endif
