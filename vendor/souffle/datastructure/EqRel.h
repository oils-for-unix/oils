/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file EqRel.h
 *
 * Datastructure for Equivalence relations
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/SouffleInterface.h"
#include "souffle/datastructure/EquivalenceRelation.h"

namespace souffle {

/** Equivalence relations */
struct t_eqrel {
    static constexpr Relation::arity_type Arity = 2;
    using t_tuple = Tuple<RamDomain, 2>;
    using t_ind = EquivalenceRelation<t_tuple>;
    t_ind ind;
    class iterator_0 : public std::iterator<std::forward_iterator_tag, t_tuple> {
        using nested_iterator = typename t_ind::iterator;
        nested_iterator nested;
        t_tuple value;

    public:
        iterator_0(const nested_iterator& iter) : nested(iter), value(*iter) {}
        iterator_0(const iterator_0& other) = default;
        iterator_0& operator=(const iterator_0& other) = default;
        bool operator==(const iterator_0& other) const {
            return nested == other.nested;
        }
        bool operator!=(const iterator_0& other) const {
            return !(*this == other);
        }
        const t_tuple& operator*() const {
            return value;
        }
        const t_tuple* operator->() const {
            return &value;
        }
        iterator_0& operator++() {
            ++nested;
            value = *nested;
            return *this;
        }
    };
    class iterator_1 : public std::iterator<std::forward_iterator_tag, t_tuple> {
        using nested_iterator = typename t_ind::iterator;
        nested_iterator nested;
        t_tuple value;

    public:
        iterator_1(const nested_iterator& iter) : nested(iter), value(reorder(*iter)) {}
        iterator_1(const iterator_1& other) = default;
        iterator_1& operator=(const iterator_1& other) = default;
        bool operator==(const iterator_1& other) const {
            return nested == other.nested;
        }
        bool operator!=(const iterator_1& other) const {
            return !(*this == other);
        }
        const t_tuple& operator*() const {
            return value;
        }
        const t_tuple* operator->() const {
            return &value;
        }
        iterator_1& operator++() {
            ++nested;
            value = reorder(*nested);
            return *this;
        }
    };
    using iterator = iterator_0;
    struct context {
        t_ind::operation_hints hints;
    };
    context createContext() {
        return context();
    }
    bool insert(const t_tuple& t) {
        return ind.insert(t[0], t[1]);
    }
    bool insert(const t_tuple& t, context& h) {
        return ind.insert(t[0], t[1], h.hints);
    }
    bool insert(const RamDomain* ramDomain) {
        RamDomain data[2];
        std::copy(ramDomain, ramDomain + 2, data);
        auto& tuple = reinterpret_cast<const t_tuple&>(data);
        context h;
        return insert(tuple, h);
    }
    bool insert(RamDomain a1, RamDomain a2) {
        RamDomain data[2] = {a1, a2};
        return insert(data);
    }
    void extendAndInsert(t_eqrel& other) {
        ind.extendAndInsert(other.ind);
    }
    bool contains(const t_tuple& t) const {
        return ind.contains(t[0], t[1]);
    }
    bool contains(const t_tuple& t, context&) const {
        return ind.contains(t[0], t[1]);
    }
    std::size_t size() const {
        return ind.size();
    }
    iterator find(const t_tuple& t) const {
        return ind.find(t);
    }
    iterator find(const t_tuple& t, context&) const {
        return ind.find(t);
    }
    range<iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& /*upper*/, context& h) const {
        auto r = ind.template getBoundaries<1>((lower), h.hints);
        return make_range(iterator(r.begin()), iterator(r.end()));
    }
    range<iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper) const {
        context h;
        return lowerUpperRange_10(lower, upper, h);
    }
    range<iterator_1> lowerUpperRange_01(const t_tuple& lower, const t_tuple& /*upper*/, context& h) const {
        auto r = ind.template getBoundaries<1>(reorder(lower), h.hints);
        return make_range(iterator_1(r.begin()), iterator_1(r.end()));
    }
    range<iterator_1> lowerUpperRange_01(const t_tuple& lower, const t_tuple& upper) const {
        context h;
        return lowerUpperRange_01(lower, upper, h);
    }
    range<iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& /*upper*/, context& h) const {
        auto r = ind.template getBoundaries<2>((lower), h.hints);
        return make_range(iterator(r.begin()), iterator(r.end()));
    }
    range<iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const {
        context h;
        return lowerUpperRange_11(lower, upper, h);
    }
    bool empty() const {
        return ind.size() == 0;
    }
    std::vector<range<iterator>> partition() const {
        std::vector<range<iterator>> res;
        for (const auto& cur : ind.partition(10000)) {
            res.push_back(make_range(iterator(cur.begin()), iterator(cur.end())));
        }
        return res;
    }
    void purge() {
        ind.clear();
    }
    iterator begin() const {
        return iterator(ind.begin());
    }
    iterator end() const {
        return iterator(ind.end());
    }
    static t_tuple reorder(const t_tuple& t) {
        t_tuple res;
        res[0] = t[1];
        res[1] = t[0];
        return res;
    }
    void printStatistics(std::ostream& /* o */) const {}
};

}  // namespace souffle