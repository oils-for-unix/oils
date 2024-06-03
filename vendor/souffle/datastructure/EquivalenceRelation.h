/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017 The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file EquivalenceRelation.h
 *
 * Defines a binary relation interface to be used with Souffle as a relational store.
 * Pairs inserted into this relation implicitly store a reflexive, symmetric, and transitive relation
 * with each other.
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/datastructure/LambdaBTree.h"
#include "souffle/datastructure/PiggyList.h"
#include "souffle/datastructure/UnionFind.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/ParallelUtil.h"
#include <atomic>
#include <cassert>
#include <cstddef>
#include <functional>
#include <iostream>
#include <iterator>
#include <set>
#include <shared_mutex>
#include <stdexcept>
#include <tuple>
#include <unordered_set>
#include <utility>
#include <vector>

namespace souffle {
template <typename TupleType>
class EquivalenceRelation {
    using value_type = typename TupleType::value_type;

    // mapping from representative to disjoint set
    // just a cache, essentially, used for iteration over
    using StatesList = souffle::PiggyList<value_type>;
    using StatesBucket = StatesList*;
    using StorePair = std::pair<value_type, StatesBucket>;
    using StatesMap = souffle::LambdaBTreeSet<StorePair, std::function<StatesBucket(StorePair&)>,
            souffle::EqrelMapComparator<StorePair>>;

public:
    using element_type = TupleType;

    EquivalenceRelation() : statesMapStale(false){};
    ~EquivalenceRelation() {
        emptyPartition();
    }

    /**
     * A collection of operation hints speeding up some of the involved operations
     * by exploiting temporal locality.
     * Unused in this class, as there is no speedup to be gained.
     * This is just defined as the class expects it.
     */
    struct operation_hints {
        // resets all hints (to be triggered e.g. when deleting nodes)
        void clear() {}
    };

    /**
     * Insert the two values symbolically as a binary relation
     * @param x node to be added/paired
     * @param y node to be added/paired
     * @return true if the pair is new to the data structure
     */
    bool insert(value_type x, value_type y) {
        operation_hints z;
        return insert(x, y, z);
    };

    /**
     * Insert the tuple symbolically.
     * @param tuple The tuple to be inserted
     * @return true if the tuple is new to the data structure
     */
    bool insert(const TupleType& tuple) {
        operation_hints hints;
        return insert(tuple[0], tuple[1], hints);
    };

    /**
     * Insert the two values symbolically as a binary relation
     * @param x node to be added/paired
     * @param y node to be added/paired
     * @param z the hints to where the pair should be inserted (not applicable atm)
     * @return true if the pair is new to the data structure
     */
    bool insert(value_type x, value_type y, operation_hints) {
        // indicate that iterators will have to generate on request
        this->statesMapStale.store(true, std::memory_order_relaxed);
        bool retval = !contains(x, y);
        sds.unionNodes(x, y);
        return retval;
    }

    /**
     * inserts all nodes from the other relation into this one
     * @param other the binary relation from which to add elements from
     */
    void insertAll(const EquivalenceRelation<TupleType>& other) {
        other.genAllDisjointSetLists();

        // iterate over partitions at a time
        for (auto&& [rep, pl] : other.equivalencePartition) {
            const std::size_t ksize = pl->size();
            for (std::size_t i = 0; i < ksize; ++i) {
                this->sds.unionNodes(rep, pl->get(i));
            }
        }
        // invalidate iterators unconditionally
        this->statesMapStale.store(true, std::memory_order_relaxed);
    }

    /**
     * Extend this relation with another relation, expanding this equivalence
     * relation and inserting it into the other relation.
     *
     * The supplied relation is the old knowledge, whilst this relation only
     * contains explicitly new knowledge. After this operation the "implicitly
     * new tuples" are now explicitly inserted this relation, and all of the new
     * tuples in this relation are inserted into the old relation.
     */
    void extendAndInsert(EquivalenceRelation<TupleType>& other) {
        if (other.size() == 0 && this->size() == 0) return;

        std::unordered_set<value_type> repsCovered;

        // This vector holds all of the elements of this equivalence relation
        // that aren't yet in other, which get inserted after extending this
        // relation by other. These operations are interleaved for maximum
        // efficiency - either extend or inserting first would make the other
        // operation unnecessarily slow.
        std::vector<std::pair<value_type, value_type>> toInsert;
        auto size = std::distance(this->sds.sparseToDenseMap.begin(), this->sds.sparseToDenseMap.end());
        toInsert.reserve(size);

        // find all the disjoint sets that need to be added to this relation
        // that exist in other (and exist in this)
        {
            auto it = this->sds.sparseToDenseMap.begin();
            auto end = this->sds.sparseToDenseMap.end();
            value_type el;
            for (; it != end; ++it) {
                std::tie(el, std::ignore) = *it;
                if (other.containsElement(el)) {
                    value_type rep = other.sds.findNode(el);
                    if (repsCovered.count(rep) == 0) {
                        repsCovered.emplace(rep);
                    }
                }
                toInsert.emplace_back(el, this->sds.findNode(el));
            }
        }
        assert(size >= 0);
        assert(toInsert.size() == (std::size_t)size);

        // add the intersecting dj sets into this one
        {
            value_type el;
            value_type rep;
            auto it = other.sds.sparseToDenseMap.begin();
            auto end = other.sds.sparseToDenseMap.end();
            for (; it != end; ++it) {
                std::tie(el, std::ignore) = *it;
                rep = other.sds.findNode(el);
                if (repsCovered.count(rep) != 0) {
                    this->insert(el, rep);
                }
            }
        }

        // Insert all new tuples from this relation into the old relation
        {
            value_type el;
            value_type rep;
            for (std::pair<value_type, value_type> p : toInsert) {
                std::tie(el, rep) = p;
                other.insert(el, rep);
            }
        }
    }

    /**
     * Returns whether there exists a pair with these two nodes
     * @param x front of pair
     * @param y back of pair
     */
    bool contains(value_type x, value_type y) const {
        return sds.contains(x, y);
    }

    /**
     * Returns whether there exists given tuple.
     * @param tuple The tuple to search for.
     */
    bool contains(const TupleType& tuple, operation_hints&) const {
        return contains(tuple[0], tuple[1]);
    };

    bool contains(const TupleType& tuple) const {
        return contains(tuple[0], tuple[1]);
    };

    void emptyPartition() const {
        // delete the beautiful values inside (they're raw ptrs, so they need to be.)
        for (auto& pair : equivalencePartition) {
            delete pair.second;
        }
        // invalidate it my dude
        this->statesMapStale.store(true, std::memory_order_relaxed);

        equivalencePartition.clear();
    }

    /**
     * Empty the relation
     */
    void clear() {
        statesLock.lock();

        sds.clear();
        emptyPartition();

        statesLock.unlock();
    }

    /**
     * Size of relation
     * @return the sum of the number of pairs per disjoint set
     */
    std::size_t size() const {
        genAllDisjointSetLists();

        statesLock.lock_shared();

        std::size_t retVal = 0;
        for (auto& e : this->equivalencePartition) {
            const std::size_t s = e.second->size();
            retVal += s * s;
        }

        statesLock.unlock_shared();
        return retVal;
    }

    // an almighty iterator for several types of iteration.
    // Unfortunately, subclassing isn't an option with souffle
    //   - we don't deal with pointers (so no virtual)
    //   - and a single iter type is expected (see Relation::iterator e.g.) (i think)
    class iterator {
    public:
        typedef std::forward_iterator_tag iterator_category;
        using value_type = TupleType;
        using difference_type = ptrdiff_t;
        using pointer = value_type*;
        using reference = value_type&;

        // one iterator for signalling the end (simplifies)
        explicit iterator(const EquivalenceRelation* br, bool /* signalIsEndIterator */)
                : br(br), isEndVal(true){};

        explicit iterator(const EquivalenceRelation* br)
                : br(br), ityp(IterType::ALL), djSetMapListIt(br->equivalencePartition.begin()),
                  djSetMapListEnd(br->equivalencePartition.end()) {
            // no need to fast forward if this iterator is empty
            if (djSetMapListIt == djSetMapListEnd) {
                isEndVal = true;
                return;
            }
            // grab the pointer to the list, and make it our current list
            djSetList = (*djSetMapListIt).second;
            assert(djSetList->size() != 0);

            updateAnterior();
            updatePosterior();
        }

        // WITHIN: iterator for everything within the same DJset (used for EquivalenceRelation.partition())
        explicit iterator(const EquivalenceRelation* br, const StatesBucket within)
                : br(br), ityp(IterType::WITHIN), djSetList(within) {
            // empty dj set
            if (djSetList->size() == 0) {
                isEndVal = true;
            }

            updateAnterior();
            updatePosterior();
        }

        // ANTERIOR: iterator that yields all (former, _) \in djset(former) (djset(former) === within)
        explicit iterator(const EquivalenceRelation* br, const typename TupleType::value_type former,
                const StatesBucket within)
                : br(br), ityp(IterType::ANTERIOR), djSetList(within) {
            if (djSetList->size() == 0) {
                isEndVal = true;
            }

            setAnterior(former);
            updatePosterior();
        }

        // ANTPOST: iterator that yields all (former, latter) \in djset(former), (djset(former) ==
        // djset(latter) == within)
        explicit iterator(const EquivalenceRelation* br, const typename TupleType::value_type former,
                typename TupleType::value_type latter, const StatesBucket within)
                : br(br), ityp(IterType::ANTPOST), djSetList(within) {
            if (djSetList->size() == 0) {
                isEndVal = true;
            }

            setAnterior(former);
            setPosterior(latter);
        }

        /** explicit set first half of cPair */
        inline void setAnterior(const typename TupleType::value_type a) {
            this->cPair[0] = a;
        }

        /** quick update to whatever the current index is pointing to */
        inline void updateAnterior() {
            this->cPair[0] = this->djSetList->get(this->cAnteriorIndex);
        }

        /** explicit set second half of cPair */
        inline void setPosterior(const typename TupleType::value_type b) {
            this->cPair[1] = b;
        }

        /** quick update to whatever the current index is pointing to */
        inline void updatePosterior() {
            this->cPair[1] = this->djSetList->get(this->cPosteriorIndex);
        }

        // copy ctor
        iterator(const iterator& other) = default;
        // move ctor
        iterator(iterator&& other) = default;
        // assign iter
        iterator& operator=(const iterator& other) = default;

        bool operator==(const iterator& other) const {
            if (isEndVal && other.isEndVal) return br == other.br;
            return isEndVal == other.isEndVal && cPair == other.cPair;
        }

        bool operator!=(const iterator& other) const {
            return !((*this) == other);
        }

        const TupleType& operator*() const {
            return cPair;
        }

        const TupleType* operator->() const {
            return &cPair;
        }

        /* pre-increment */
        iterator& operator++() {
            if (isEndVal) {
                throw std::out_of_range("error: incrementing an out of range iterator");
            }

            switch (ityp) {
                case IterType::ALL:
                    // move posterior along one
                    // see if we can't move the posterior along
                    if (++cPosteriorIndex == djSetList->size()) {
                        // move anterior along one
                        // see if we can't move the anterior along one
                        if (++cAnteriorIndex == djSetList->size()) {
                            // move the djset it along one
                            // see if we can't move it along one (we're at the end)
                            if (++djSetMapListIt == djSetMapListEnd) {
                                isEndVal = true;
                                return *this;
                            }

                            // we can't iterate along this djset if it is empty
                            djSetList = (*djSetMapListIt).second;
                            if (djSetList->size() == 0) {
                                throw std::out_of_range("error: encountered a zero size djset");
                            }

                            // update our cAnterior and cPosterior
                            cAnteriorIndex = 0;
                            cPosteriorIndex = 0;
                            updateAnterior();
                            updatePosterior();
                        }

                        // we moved our anterior along one
                        updateAnterior();

                        cPosteriorIndex = 0;
                        updatePosterior();
                    }
                    // we just moved our posterior along one
                    updatePosterior();

                    break;
                case IterType::ANTERIOR:
                    // step posterior along one, and if we can't, then we're done.
                    if (++cPosteriorIndex == djSetList->size()) {
                        isEndVal = true;
                        return *this;
                    }
                    updatePosterior();

                    break;
                case IterType::ANTPOST:
                    // fixed anterior and posterior literally only points to one, so if we increment, its the
                    // end
                    isEndVal = true;
                    break;
                case IterType::WITHIN:
                    // move posterior along one
                    // see if we can't move the posterior along
                    if (++cPosteriorIndex == djSetList->size()) {
                        // move anterior along one
                        // see if we can't move the anterior along one
                        if (++cAnteriorIndex == djSetList->size()) {
                            isEndVal = true;
                            return *this;
                        }

                        // we moved our anterior along one
                        updateAnterior();

                        cPosteriorIndex = 0;
                        updatePosterior();
                    }
                    // we just moved our posterior along one
                    updatePosterior();
                    break;
            }

            return *this;
        }

    private:
        const EquivalenceRelation* br = nullptr;
        // special tombstone value to notify that this iter represents the end
        bool isEndVal = false;

        // all the different types of iterator this can be
        enum IterType { ALL, ANTERIOR, ANTPOST, WITHIN };
        IterType ityp;

        TupleType cPair;

        // the disjoint set that we're currently iterating through
        StatesBucket djSetList;
        typename StatesMap::iterator djSetMapListIt;
        typename StatesMap::iterator djSetMapListEnd;

        // used for ALL, and POSTERIOR (just a current index in the cList)
        std::size_t cAnteriorIndex = 0;
        // used for ALL, and ANTERIOR (just a current index in the cList)
        std::size_t cPosteriorIndex = 0;
    };

public:
    /**
     * iterator pointing to the beginning of the tuples, with no restrictions
     * @return the iterator that corresponds to the beginning of the binary relation
     */
    iterator begin() const {
        genAllDisjointSetLists();
        return iterator(this);
    }

    /**
     * iterator pointing to the end of the tuples
     * @return the iterator which represents the end of the binary rel
     */
    iterator end() const {
        return iterator(this, true);
    }

    /**
     * Obtains a range of elements matching the prefix of the given entry up to
     * levels elements.
     *
     * @tparam levels the length of the requested matching prefix
     * @param entry the entry to be looking for
     * @return the corresponding range of matching elements
     */
    template <unsigned levels>
    range<iterator> getBoundaries(const TupleType& entry) const {
        operation_hints ctxt;
        return getBoundaries<levels>(entry, ctxt);
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
    range<iterator> getBoundaries(const TupleType& entry, operation_hints&) const {
        // if nothing is bound => just use begin and end
        if (levels == 0) return make_range(begin(), end());

        // as disjoint set is exactly two args (equiv relation)
        // we only need to handle these cases

        if (levels == 1) {
            // need to test if the entry actually exists
            if (!sds.nodeExists(entry[0])) return make_range(end(), end());

            // return an iterator over all (entry[0], _)
            return make_range(anteriorIt(entry[0]), end());
        }

        if (levels == 2) {
            // need to test if the entry actually exists
            if (!sds.contains(entry[0], entry[1])) return make_range(end(), end());

            // if so return an iterator containing exactly that node
            return make_range(antpostit(entry[0], entry[1]), end());
        }

        std::cerr << "invalid state, cannot search for >2 arg start point in getBoundaries, in 2 arg tuple "
                     "store\n";
        throw "invalid state, cannot search for >2 arg start point in getBoundaries, in 2 arg tuple store";

        return make_range(end(), end());
    }

    /**
     * Act similar to getBoundaries. But non-static.
     * This function should be used ONLY by interpreter,
     * and its behavior is tightly coupling with InterpreterIndex.
     * Do Not rely on this interface outside the interpreter.
     *
     * @param entry the entry to be looking for
     * @return the corresponding range of matching elements
     */
    iterator lower_bound(const TupleType& entry, operation_hints&) const {
        if (entry[0] == MIN_RAM_SIGNED && entry[1] == MIN_RAM_SIGNED) {
            // Return an iterator over all tuples.
            return begin();
        }

        if (entry[0] != MIN_RAM_SIGNED && entry[1] == MIN_RAM_SIGNED) {
            // Return an iterator over all (entry[0], _)

            if (!sds.nodeExists(entry[0])) {
                return end();
            }
            return anteriorIt(entry[0]);
        }

        if (entry[0] != MIN_RAM_SIGNED && entry[1] != MIN_RAM_SIGNED) {
            // Return an iterator point to the exact same node.

            if (!sds.contains(entry[0], entry[1])) {
                return end();
            }
            return antpostit(entry[0], entry[1]);
        }

        return end();
    }

    iterator lower_bound(const TupleType& entry) const {
        operation_hints hints;
        return lower_bound(entry, hints);
    }

    /**
     * This function is only here in order to unify interfaces in InterpreterIndex.
     * Unlike the name suggestes, it omit the arguments and simply return the end
     * iterator of the relation.
     *
     * @param omitted
     * @return the end iterator.
     */
    iterator upper_bound(const TupleType&, operation_hints&) const {
        return end();
    }

    iterator upper_bound(const TupleType& entry) const {
        operation_hints hints;
        return upper_bound(entry, hints);
    }

    /**
     * Check emptiness.
     */
    bool empty() const {
        return this->size() == 0;
    }

    /**
     * Creates an iterator that generates all pairs (A, X)
     * for a given A, and X are elements within A's disjoint set.
     * @param anteriorVal: The first value of the tuple to be generated for
     * @return the iterator representing this.
     */
    iterator anteriorIt(value_type anteriorVal) const {
        genAllDisjointSetLists();

        // locate the blocklist that the anterior val resides in
        auto found = equivalencePartition.find({sds.findNode(anteriorVal), nullptr});
        assert(found != equivalencePartition.end() && "iterator called on partition that doesn't exist");

        return iterator(static_cast<const EquivalenceRelation*>(this),
                static_cast<const value_type>(anteriorVal), static_cast<const StatesBucket>((*found).second));
    }

    /**
     * Creates an iterator that generates the pair (A, B)
     * for a given A and B. If A and B don't exist, or aren't in the same set,
     * then the end() iterator is returned.
     * @param anteriorVal: the A value of the tuple
     * @param posteriorVal: the B value of the tuple
     * @return the iterator representing this
     */
    iterator antpostit(value_type anteriorVal, value_type posteriorVal) const {
        // obv if they're in diff sets, then iteration for this pair just ends.
        if (!sds.sameSet(anteriorVal, posteriorVal)) return end();

        genAllDisjointSetLists();

        // locate the blocklist that the val resides in
        auto found = equivalencePartition.find({sds.findNode(posteriorVal), nullptr});
        assert(found != equivalencePartition.end() && "iterator called on partition that doesn't exist");

        return iterator(this, anteriorVal, posteriorVal, (*found).second);
    }

    /**
     * Begin an iterator over all pairs within a single disjoint set - This is used for partition().
     * @param rep the representative of (or element within) a disjoint set of which to generate all pairs
     * @return an iterator that will generate all pairs within the disjoint set
     */
    iterator closure(value_type rep) const {
        genAllDisjointSetLists();

        // locate the blocklist that the val resides in
        auto found = equivalencePartition.find({sds.findNode(rep), nullptr});
        return iterator(this, (*found).second);
    }

    /**
     * Generate an approximate number of iterators for parallel iteration
     * The iterators returned are not necessarily equal in size, but in practise are approximately similarly
     * sized
     * Depending on the structure of the data, there can be more or less partitions returned than requested.
     * @param chunks the number of requested partitions
     * @return a list of the iterators as ranges
     */
    std::vector<souffle::range<iterator>> partition(std::size_t chunks) const {
        // generate all reps
        genAllDisjointSetLists();

        std::size_t numPairs = this->size();
        if (numPairs == 0) return {};
        if (numPairs == 1 || chunks <= 1) return {souffle::make_range(begin(), end())};

        // if there's more dj sets than requested chunks, then just return an iter per dj set
        std::vector<souffle::range<iterator>> ret;
        if (chunks <= equivalencePartition.size()) {
            for (auto& p : equivalencePartition) {
                ret.push_back(souffle::make_range(closure(p.first), end()));
            }
            return ret;
        }

        // keep it simple stupid
        // just go through and if the size of the binrel is > numpairs/chunks, then generate an anteriorIt for
        // each
        const std::size_t perchunk = numPairs / chunks;
        for (const auto& itp : equivalencePartition) {
            const std::size_t s = itp.second->size();
            if (s * s > perchunk) {
                for (const auto& i : *itp.second) {
                    ret.push_back(souffle::make_range(anteriorIt(i), end()));
                }
            } else {
                ret.push_back(souffle::make_range(closure(itp.first), end()));
            }
        }

        return ret;
    }

    iterator find(const TupleType&, operation_hints&) const {
        throw std::runtime_error("error: find() is not compatible with equivalence relations");
        return begin();
    }

    iterator find(const TupleType& t) const {
        operation_hints context;
        return find(t, context);
    }

protected:
    bool containsElement(value_type e) const {
        return this->sds.nodeExists(e);
    }

private:
    // marked as mutable due to difficulties with the const enforcement via the Relation API
    // const operations *may* safely change internal state (i.e. collapse djset forest)
    mutable souffle::SparseDisjointSet<value_type> sds;

    // read/write lock on equivalencePartition
    mutable std::shared_mutex statesLock;

    mutable StatesMap equivalencePartition;
    // whether the cache is stale
    mutable std::atomic<bool> statesMapStale;

    /**
     * Generate a cache of the sets such that they can be iterated over efficiently.
     * Each set is partitioned into a PiggyList.
     */
    void genAllDisjointSetLists() const {
        statesLock.lock();

        // no need to generate again, already done.
        if (!this->statesMapStale.load(std::memory_order_acquire)) {
            statesLock.unlock();
            return;
        }

        // btree version
        emptyPartition();

        std::size_t dSetSize = this->sds.ds.a_blocks.size();
        for (std::size_t i = 0; i < dSetSize; ++i) {
            typename TupleType::value_type sparseVal = this->sds.toSparse(i);
            parent_t rep = this->sds.findNode(sparseVal);

            StorePair p = {static_cast<value_type>(rep), nullptr};
            StatesList* mapList = equivalencePartition.insert(p, [&](StorePair& sp) {
                auto* r = new StatesList(1);
                sp.second = r;
                return r;
            });
            mapList->append(sparseVal);
        }

        statesMapStale.store(false, std::memory_order_release);
        statesLock.unlock();
    }
};
}  // namespace souffle
