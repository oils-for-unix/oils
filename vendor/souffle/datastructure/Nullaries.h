/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Nullaries.h
 *
 * Datastructure for Nullary relations
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/SouffleInterface.h"
#include <atomic>

namespace souffle {

/** Nullary relations */
class t_nullaries {
private:
    std::atomic<bool> data{false};

public:
    static constexpr Relation::arity_type Arity = 0;

    t_nullaries() = default;
    using t_tuple = Tuple<RamDomain, 0>;
    struct context {};
    context createContext() {
        return context();
    }
    class iterator {
        bool value;

    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = RamDomain*;
        using difference_type = ptrdiff_t;
        using pointer = value_type*;
        using reference = value_type&;

        iterator(bool v = false) : value(v) {}

        const RamDomain* operator*() {
            return nullptr;
        }

        bool operator==(const iterator& other) const {
            return other.value == value;
        }

        bool operator!=(const iterator& other) const {
            return other.value != value;
        }

        iterator& operator++() {
            if (value) {
                value = false;
            }
            return *this;
        }
    };
    iterator begin() const {
        return iterator(data);
    }
    iterator end() const {
        return iterator();
    }
    void insert(const t_tuple& /* t */) {
        data = true;
    }
    void insert(const t_tuple& /* t */, context& /* ctxt */) {
        data = true;
    }
    void insert(const RamDomain* /* ramDomain */) {
        data = true;
    }
    bool insert() {
        bool result = data;
        data = true;
        return !result;
    }
    bool contains(const t_tuple& /* t */) const {
        return data;
    }
    bool contains(const t_tuple& /* t */, context& /* ctxt */) const {
        return data;
    }
    std::size_t size() const {
        return data ? 1 : 0;
    }
    bool empty() const {
        return !data;
    }
    void purge() {
        data = false;
    }
    void printStatistics(std::ostream& /* o */) const {}
};

}  // namespace souffle
