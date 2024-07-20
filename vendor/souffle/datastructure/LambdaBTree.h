/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2018, Souffle Developers
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file LambdaBTree.h
 *
 * An implementation of a generic B-tree data structure including
 * interfaces for utilizing instances as set or multiset containers.
 * Allows the user to provide a function to execute on successful insert
 * Be careful using this, it currently expects a pair as the key.
 *
 ***********************************************************************/

#pragma once

#include "souffle/datastructure/BTree.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/ParallelUtil.h"
#include <atomic>
#include <cassert>
#include <typeinfo>
#include <vector>

namespace souffle {

namespace detail {
/**
 * The actual implementation of a b-tree data structure.
 *
 * @tparam Key             .. the element type to be stored in this tree
 * @tparam Comparator     .. a class defining an order on the stored elements
 * @tparam Allocator     .. utilized for allocating memory for required nodes
 * @tparam blockSize    .. determines the number of bytes/block utilized by leaf nodes
 * @tparam SearchStrategy .. enables switching between linear, binary or any other search strategy
 * @tparam isSet        .. true = set, false = multiset
 * @tparam Functor      .. a std::function that is called on successful (new) insert
 */
template <typename Key, typename Comparator,
        typename Allocator,  // is ignored so far - TODO: add support
        unsigned blockSize, typename SearchStrategy, bool isSet, typename Functor,
        typename WeakComparator = Comparator, typename Updater = detail::updater<Key>>
class LambdaBTree : public btree<Key, Comparator, Allocator, blockSize, SearchStrategy, isSet, WeakComparator,
                            Updater> {
public:
    using parenttype =
            btree<Key, Comparator, Allocator, blockSize, SearchStrategy, isSet, WeakComparator, Updater>;

    LambdaBTree(const Comparator& comp = Comparator(), const WeakComparator& weak_comp = WeakComparator())
            : parenttype(comp, weak_comp) {}

    /**
     * Inserts the given key into this tree.
     */
    typename Functor::result_type insert(Key& k, const Functor& f) {
        typename parenttype::operation_hints hints;
        return insert(k, hints, f);
    }

    // rewriting this because of david's changes
    typename Functor::result_type insert(
            Key& k, typename parenttype::operation_hints& hints, const Functor& f) {
#ifdef IS_PARALLEL

        // special handling for inserting first element
        while (this->root == nullptr) {
            // try obtaining root-lock
            if (!this->root_lock.try_start_write()) {
                // somebody else was faster => re-check
                continue;
            }

            // check loop condition again
            if (this->root != nullptr) {
                // somebody else was faster => normal insert
                this->root_lock.abort_write();
                break;
            }

            // create new node
            this->leftmost = new typename parenttype::leaf_node();
            this->leftmost->numElements = 1;
            // call the functor as we've successfully inserted
            typename Functor::result_type res = f(k);

            this->leftmost->keys[0] = k;
            this->root = this->leftmost;

            // operation complete => we can release the root lock
            this->root_lock.end_write();

            hints.last_insert.access(this->leftmost);

            return res;
        }

        // insert using iterative implementation

        typename parenttype::node* cur = nullptr;

        // test last insert hints
        typename parenttype::lock_type::Lease cur_lease;

        auto checkHint = [&](typename parenttype::node* last_insert) {
            // ignore null pointer
            if (!last_insert) return false;
            // get a read lease on indicated node
            auto hint_lease = last_insert->lock.start_read();
            // check whether it covers the key
            if (!this->weak_covers(last_insert, k)) return false;
            // and if there was no concurrent modification
            if (!last_insert->lock.validate(hint_lease)) return false;
            // use hinted location
            cur = last_insert;
            // and keep lease
            cur_lease = hint_lease;
            // we found a hit
            return true;
        };

        if (hints.last_insert.any(checkHint)) {
            // register this as a hit
            this->hint_stats.inserts.addHit();
        } else {
            // register this as a miss
            this->hint_stats.inserts.addMiss();
        }

        // if there is no valid hint ..
        if (!cur) {
            do {
                // get root - access lock
                auto root_lease = this->root_lock.start_read();

                // start with root
                cur = this->root;

                // get lease of the next node to be accessed
                cur_lease = cur->lock.start_read();

                // check validity of root pointer
                if (this->root_lock.end_read(root_lease)) {
                    break;
                }

            } while (true);
        }

        while (true) {
            // handle inner nodes
            if (cur->inner) {
                auto a = &(cur->keys[0]);
                auto b = &(cur->keys[cur->numElements]);

                auto pos = this->search.lower_bound(k, a, b, this->weak_comp);
                auto idx = pos - a;

                // early exit for sets
                if (isSet && pos != b && this->weak_equal(*pos, k)) {
                    // validate results
                    if (!cur->lock.validate(cur_lease)) {
                        // start over again
                        return insert(k, hints, f);
                    }

                    // update provenance information
                    if (typeid(Comparator) != typeid(WeakComparator) && this->less(k, *pos)) {
                        if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                            // start again
                            return insert(k, hints, f);
                        }
                        this->update(*pos, k);

                        // get result before releasing lock
                        auto res = (*pos).second;

                        cur->lock.end_write();
                        return res;
                    }

                    // get the result before releasing lock
                    auto res = (*pos).second;

                    // check validity
                    if (!cur->lock.validate(cur_lease)) {
                        // start over again
                        return insert(k, hints, f);
                    }

                    // we found the element => return the result
                    return res;
                }

                // get next pointer
                auto next = cur->getChild(idx);

                // get lease on next level
                auto next_lease = next->lock.start_read();

                // check whether there was a write
                if (!cur->lock.end_read(cur_lease)) {
                    // start over
                    return insert(k, hints, f);
                }

                // go to next
                cur = next;

                // move on lease
                cur_lease = next_lease;

                continue;
            }

            // the rest is for leaf nodes
            assert(!cur->inner);

            // -- insert node in leaf node --

            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = this->search.upper_bound(k, a, b, this->weak_comp);
            auto idx = pos - a;

            // early exit for sets
            if (isSet && pos != a && this->weak_equal(*(pos - 1), k)) {
                // validate result
                if (!cur->lock.validate(cur_lease)) {
                    // start over again
                    return insert(k, hints, f);
                }

                // TODO (pnappa): remove provenance from LambdaBTree - no use for it
                // update provenance information
                if (typeid(Comparator) != typeid(WeakComparator) && this->less(k, *(pos - 1))) {
                    if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                        // start again
                        return insert(k, hints, f);
                    }
                    this->update(*(pos - 1), k);

                    // retrieve result before releasing lock
                    auto res = (*(pos - 1)).second;

                    cur->lock.end_write();
                    return res;
                }

                // read result (atomic) -- just as a proof of concept, this is actually not valid!!
                std::atomic<typename Functor::result_type>& loc =
                        *reinterpret_cast<std::atomic<typename Functor::result_type>*>(&(*(pos - 1)).second);
                auto res = loc.load(std::memory_order_relaxed);

                // check validity
                if (!cur->lock.validate(cur_lease)) {
                    // start over again
                    return insert(k, hints, f);
                }

                // we found the element => done
                return res;
            }

            // upgrade to write-permission
            if (!cur->lock.try_upgrade_to_write(cur_lease)) {
                // something has changed => restart
                hints.last_insert.access(cur);
                return insert(k, hints, f);
            }

            if (cur->numElements >= parenttype::node::maxKeys) {
                // -- lock parents --
                auto priv = cur;
                auto parent = priv->parent;
                std::vector<typename parenttype::node*> parents;
                do {
                    if (parent) {
                        parent->lock.start_write();
                        while (true) {
                            // check whether parent is correct
                            if (parent == priv->parent) {
                                break;
                            }
                            // switch parent
                            parent->lock.abort_write();
                            parent = priv->parent;
                            parent->lock.start_write();
                        }
                    } else {
                        // lock root lock => since cur is root
                        this->root_lock.start_write();
                    }

                    // record locked node
                    parents.push_back(parent);

                    // stop at "sphere of influence"
                    if (!parent || !parent->isFull()) {
                        break;
                    }

                    // go one step higher
                    priv = parent;
                    parent = parent->parent;

                } while (true);

                // split this node
                auto old_root = this->root;
                idx -= cur->rebalance_or_split(const_cast<typename parenttype::node**>(&this->root),
                        this->root_lock, static_cast<int>(idx), parents);

                // release parent lock
                for (auto it = parents.rbegin(); it != parents.rend(); ++it) {
                    auto parent = *it;

                    // release this lock
                    if (parent) {
                        parent->lock.end_write();
                    } else {
                        if (old_root != this->root) {
                            this->root_lock.end_write();
                        } else {
                            this->root_lock.abort_write();
                        }
                    }
                }

                // insert element in right fragment
                if (((typename parenttype::size_type)idx) > cur->numElements) {
                    // release current lock
                    cur->lock.end_write();

                    // insert in sibling
                    return insert(k, hints, f);
                }
            }

            // ok - no split necessary
            assert(cur->numElements < parenttype::node::maxKeys && "Split required!");

            // move keys
            for (int j = static_cast<int>(cur->numElements); j > idx; --j) {
                cur->keys[j] = cur->keys[j - 1];
            }

            // insert new element
            typename Functor::result_type res = f(k);
            cur->keys[idx] = k;
            cur->numElements++;

            // release lock on current node
            cur->lock.end_write();

            // remember last insertion position
            hints.last_insert.access(cur);
            return res;
        }

#else
        // special handling for inserting first element
        if (this->empty()) {
            // create new node
            this->leftmost = new typename parenttype::leaf_node();
            this->leftmost->numElements = 1;
            // call the functor as we've successfully inserted
            typename Functor::result_type res = f(k);
            this->leftmost->keys[0] = k;
            this->root = this->leftmost;

            hints.last_insert.access(this->leftmost);

            return res;
        }

        // insert using iterative implementation
        typename parenttype::node* cur = this->root;

        auto checkHints = [&](typename parenttype::node* last_insert) {
            if (!last_insert) return false;
            if (!this->weak_covers(last_insert, k)) return false;
            cur = last_insert;
            return true;
        };

        // test last insert
        if (hints.last_insert.any(checkHints)) {
            this->hint_stats.inserts.addHit();
        } else {
            this->hint_stats.inserts.addMiss();
        }

        while (true) {
            // handle inner nodes
            if (cur->inner) {
                auto a = &(cur->keys[0]);
                auto b = &(cur->keys[cur->numElements]);

                auto pos = this->search.lower_bound(k, a, b, this->weak_comp);
                auto idx = pos - a;

                // early exit for sets
                if (isSet && pos != b && this->weak_equal(*pos, k)) {
                    // update provenance information
                    if (typeid(Comparator) != typeid(WeakComparator) && this->less(k, *pos)) {
                        this->update(*pos, k);
                        return (*pos).second;
                    }

                    return (*pos).second;
                }

                cur = cur->getChild(idx);
                continue;
            }

            // the rest is for leaf nodes
            assert(!cur->inner);

            // -- insert node in leaf node --

            auto a = &(cur->keys[0]);
            auto b = &(cur->keys[cur->numElements]);

            auto pos = this->search.upper_bound(k, a, b, this->weak_comp);
            auto idx = pos - a;

            // early exit for sets
            if (isSet && pos != a && this->weak_equal(*(pos - 1), k)) {
                // update provenance information
                if (typeid(Comparator) != typeid(WeakComparator) && this->less(k, *(pos - 1))) {
                    this->update(*(pos - 1), k);
                    return (*(pos - 1)).second;
                }

                return (*(pos - 1)).second;
            }

            if (cur->numElements >= parenttype::node::maxKeys) {
                // split this node
                idx -= cur->rebalance_or_split(const_cast<typename parenttype::node**>(&this->root),
                        this->root_lock, static_cast<int>(idx));

                // insert element in right fragment
                if (((typename parenttype::size_type)idx) > cur->numElements) {
                    idx -= cur->numElements + 1;
                    cur = cur->parent->getChild(cur->position + 1);
                }
            }

            // ok - no split necessary
            assert(cur->numElements < parenttype::node::maxKeys && "Split required!");

            // move keys
            for (int j = cur->numElements; j > idx; --j) {
                cur->keys[j] = cur->keys[j - 1];
            }

            // call the functor as we've successfully inserted
            typename Functor::result_type res = f(k);
            // insert new element
            cur->keys[idx] = k;
            cur->numElements++;

            // remember last insertion position
            hints.last_insert.access(cur);
            return res;
        }
#endif
    }

    /**
     * Inserts the given range of elements into this tree.
     */
    template <typename Iter>
    void insert(const Iter& a, const Iter& b) {
        // TODO: improve this beyond a naive insert
        typename parenttype::operation_hints hints;
        // a naive insert so far .. seems to work fine
        for (auto it = a; it != b; ++it) {
            // use insert with hint
            insert(*it, hints);
        }
    }

    /**
     * Swaps the content of this tree with the given tree. This
     * is a much more efficient operation than creating a copy and
     * realizing the swap utilizing assignment operations.
     */
    void swap(LambdaBTree& other) {
        // swap the content
        std::swap(this->root, other.root);
        std::swap(this->leftmost, other.leftmost);
    }

    // Implementation of the assignment operation for trees.
    LambdaBTree& operator=(const LambdaBTree& other) {
        // check identity
        if (this == &other) {
            return *this;
        }

        // create a deep-copy of the content of the other tree
        // shortcut for empty sets
        if (other.empty()) {
            return *this;
        }

        // clone content (deep copy)
        this->root = other.root->clone();

        // update leftmost reference
        auto tmp = this->root;
        while (!tmp->isLeaf()) {
            tmp = tmp->getChild(0);
        }
        this->leftmost = static_cast<typename parenttype::leaf_node*>(tmp);

        // done
        return *this;
    }

    // Implementation of an equality operation for trees.
    bool operator==(const LambdaBTree& other) const {
        // check identity
        if (this == &other) {
            return true;
        }

        // check size
        if (this->size() != other.size()) {
            return false;
        }
        if (this->size() < other.size()) {
            return other == *this;
        }

        // check content
        for (const auto& key : other) {
            if (!contains(key)) {
                return false;
            }
        }
        return true;
    }

    // Implementation of an inequality operation for trees.
    bool operator!=(const LambdaBTree& other) const {
        return !(*this == other);
    }
};

}  // end namespace detail

/**
 * A b-tree based set implementation.
 *
 * @tparam Key             .. the element type to be stored in this set
 * @tparam Functor         .. a std::function that is invoked on successful insert
 * @tparam Comparator     .. a class defining an order on the stored elements
 * @tparam Allocator     .. utilized for allocating memory for required nodes
 * @tparam blockSize    .. determines the number of bytes/block utilized by leaf nodes
 * @tparam SearchStrategy .. enables switching between linear, binary or any other search strategy
 */
template <typename Key, typename Functor, typename Comparator = detail::comparator<Key>,
        typename Allocator = std::allocator<Key>,  // is ignored so far
        unsigned blockSize = 256, typename SearchStrategy = typename detail::default_strategy<Key>::type>
class LambdaBTreeSet
        : public detail::LambdaBTree<Key, Comparator, Allocator, blockSize, SearchStrategy, true, Functor> {
    using super = detail::LambdaBTree<Key, Comparator, Allocator, blockSize, SearchStrategy, true, Functor>;

    friend class detail::LambdaBTree<Key, Comparator, Allocator, blockSize, SearchStrategy, true, Functor>;

public:
    /**
     * A default constructor creating an empty set.
     */
    LambdaBTreeSet(const Comparator& comp = Comparator()) : super(comp) {}

    /**
     * A constructor creating a set based on the given range.
     */
    template <typename Iter>
    LambdaBTreeSet(const Iter& a, const Iter& b) {
        this->insert(a, b);
    }

    // A copy constructor.
    LambdaBTreeSet(const LambdaBTreeSet& other) : super(other) {}

    // A move constructor.
    LambdaBTreeSet(LambdaBTreeSet&& other) : super(std::move(other)) {}

private:
    // A constructor required by the bulk-load facility.
    template <typename s, typename n, typename l>
    LambdaBTreeSet(s size, n* root, l* leftmost) : super::parenttype(size, root, leftmost) {}

public:
    // Support for the assignment operator.
    LambdaBTreeSet& operator=(const LambdaBTreeSet& other) {
        super::operator=(other);
        return *this;
    }

    // Support for the bulk-load operator.
    template <typename Iter>
    static LambdaBTreeSet load(const Iter& a, const Iter& b) {
        return super::template load<LambdaBTreeSet>(a, b);
    }
};

}  // end of namespace souffle
