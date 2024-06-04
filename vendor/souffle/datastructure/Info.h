/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Info.h
 *
 * Datastructure for Info relations
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/SouffleInterface.h"
#include "souffle/utility/ParallelUtil.h"

namespace souffle {

/** Info relations */
template <Relation::arity_type Arity_>
class t_info {
public:
    static constexpr Relation::arity_type Arity = Arity_;

    t_info() = default;
    using t_tuple = Tuple<RamDomain, Arity>;
    struct context {};
    context createContext() {
        return context();
    }
    class iterator : public std::iterator<std::forward_iterator_tag, Tuple<RamDomain, Arity>> {
        typename std::vector<Tuple<RamDomain, Arity>>::const_iterator it;

    public:
        iterator(const typename std::vector<t_tuple>::const_iterator& o) : it(o) {}

        const t_tuple operator*() {
            return *it;
        }

        bool operator==(const iterator& other) const {
            return other.it == it;
        }

        bool operator!=(const iterator& other) const {
            return !(*this == other);
        }

        iterator& operator++() {
            it++;
            return *this;
        }
    };
    iterator begin() const {
        return iterator(data.begin());
    }
    iterator end() const {
        return iterator(data.end());
    }
    void insert(const t_tuple& t) {
        insert_lock.lock();
        if (!contains(t)) {
            data.push_back(t);
        }
        insert_lock.unlock();
    }
    void insert(const t_tuple& t, context& /* ctxt */) {
        insert(t);
    }
    void insert(const RamDomain* ramDomain) {
        insert_lock.lock();
        t_tuple t;
        for (std::size_t i = 0; i < Arity; ++i) {
            t.data[i] = ramDomain[i];
        }
        data.push_back(t);
        insert_lock.unlock();
    }
    bool contains(const t_tuple& t) const {
        for (const auto& o : data) {
            if (t == o) {
                return true;
            }
        }
        return false;
    }
    bool contains(const t_tuple& t, context& /* ctxt */) const {
        return contains(t);
    }
    std::size_t size() const {
        return data.size();
    }
    bool empty() const {
        return data.size() == 0;
    }
    void purge() {
        data.clear();
    }
    void printStatistics(std::ostream& /* o */) const {}

private:
    std::vector<Tuple<RamDomain, Arity>> data;
    Lock insert_lock;
};

}  // namespace souffle
