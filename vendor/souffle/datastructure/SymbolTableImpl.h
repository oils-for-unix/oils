/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/**
 * @file SymbolTableImpl.h
 *
 * SymbolTable definition
 */

#pragma once

#include "souffle/SymbolTable.h"
#include "souffle/datastructure/ConcurrentFlyweight.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/ParallelUtil.h"
#include "souffle/utility/StreamUtil.h"

#include <algorithm>
#include <cstdlib>
#include <deque>
#include <initializer_list>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace souffle {

/**
 * @class SymbolTableImpl
 *
 * Implementation of the symbol table.
 */
class SymbolTableImpl : public SymbolTable, protected FlyweightImpl<std::string> {
private:
    using Base = FlyweightImpl<std::string>;

public:
    class IteratorImpl : public SymbolTableIteratorInterface, private Base::iterator {
    public:
        IteratorImpl(Base::iterator&& it) : Base::iterator(it) {}

        IteratorImpl(const Base::iterator& it) : Base::iterator(it) {}

        const std::pair<const std::string, const std::size_t>& get() const {
            return **this;
        }

        bool equals(const SymbolTableIteratorInterface& other) {
            return (*this) == static_cast<const IteratorImpl&>(other);
        }

        SymbolTableIteratorInterface& incr() {
            ++(*this);
            return *this;
        }

        std::unique_ptr<SymbolTableIteratorInterface> copy() const {
            return std::make_unique<IteratorImpl>(*this);
        }
    };

    using iterator = SymbolTable::Iterator;

    /** @brief Construct a symbol table with the given number of concurrent access lanes. */
    SymbolTableImpl(const std::size_t LaneCount = 1) : Base(LaneCount) {}

    /** @brief Construct a symbol table with the given initial symbols. */
    SymbolTableImpl(std::initializer_list<std::string> symbols) : Base(1, symbols.size()) {
        for (const auto& symbol : symbols) {
            findOrInsert(symbol);
        }
    }

    /** @brief Construct a symbol table with the given number of concurrent access lanes and initial symbols.
     */
    SymbolTableImpl(const std::size_t LaneCount, std::initializer_list<std::string> symbols)
            : Base(LaneCount, symbols.size()) {
        for (const auto& symbol : symbols) {
            findOrInsert(symbol);
        }
    }

    /**
     * @brief Set the number of concurrent access lanes.
     * This function is not thread-safe, do not call when other threads are using the datastructure.
     */
    void setNumLanes(const std::size_t NumLanes) {
        Base::setNumLanes(NumLanes);
    }

    iterator begin() const override {
        return SymbolTable::Iterator(std::make_unique<IteratorImpl>(Base::begin()));
    }

    iterator end() const override {
        return SymbolTable::Iterator(std::make_unique<IteratorImpl>(Base::end()));
    }

    bool weakContains(const std::string& symbol) const override {
        return Base::weakContains(symbol);
    }

    RamDomain encode(const std::string& symbol) override {
        return Base::findOrInsert(symbol).first;
    }

    const std::string& decode(const RamDomain index) const override {
        return Base::fetch(index);
    }

    RamDomain unsafeEncode(const std::string& symbol) override {
        return encode(symbol);
    }

    const std::string& unsafeDecode(const RamDomain index) const override {
        return decode(index);
    }

    std::pair<RamDomain, bool> findOrInsert(const std::string& symbol) override {
        auto Res = Base::findOrInsert(symbol);
        return std::make_pair(static_cast<RamDomain>(Res.first), Res.second);
    }
};

}  // namespace souffle
