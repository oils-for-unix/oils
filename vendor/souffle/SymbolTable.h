/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2014, 2015 Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SymbolTable.h
 *
 * Encodes/decodes symbols to numbers (and vice versa).
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"

#include <memory>
#include <string>

namespace souffle {

/** Interface of a generic SymbolTable iterator. */
class SymbolTableIteratorInterface {
public:
    virtual ~SymbolTableIteratorInterface() {}

    virtual const std::pair<const std::string, const std::size_t>& get() const = 0;

    virtual bool equals(const SymbolTableIteratorInterface& other) = 0;

    virtual SymbolTableIteratorInterface& incr() = 0;

    virtual std::unique_ptr<SymbolTableIteratorInterface> copy() const = 0;
};

/**
 * @class SymbolTable
 *
 * SymbolTable encodes symbols to numbers and decodes numbers to symbols.
 */
class SymbolTable {
public:
    virtual ~SymbolTable() {}

    /**
     * @brief Iterator on a symbol table.
     *
     * Iterator over pairs of a symbol and its encoding index.
     */
    class Iterator {
    public:
        using value_type = const std::pair<const std::string, const std::size_t>;
        using reference = value_type&;
        using pointer = value_type*;

        Iterator(std::unique_ptr<SymbolTableIteratorInterface> ptr) : impl(std::move(ptr)) {}

        Iterator(const Iterator& it) : impl(it.impl->copy()) {}

        Iterator(Iterator&& it) : impl(std::move(it.impl)) {}

        reference operator*() const {
            return impl->get();
        }

        pointer operator->() const {
            return &impl->get();
        }

        Iterator& operator++() {
            impl->incr();
            return *this;
        }

        Iterator operator++(int) {
            Iterator prev(impl->copy());
            impl->incr();
            return prev;
        }

        bool operator==(const Iterator& I) const {
            return impl->equals(*I.impl);
        }

        bool operator!=(const Iterator& I) const {
            return !impl->equals(*I.impl);
        }

    private:
        std::unique_ptr<SymbolTableIteratorInterface> impl;
    };

    using iterator = Iterator;

    /** @brief Return an iterator on the first symbol. */
    virtual iterator begin() const = 0;

    /** @brief Return an iterator past the last symbol. */
    virtual iterator end() const = 0;

    /** @brief Check if the given symbol exist. */
    virtual bool weakContains(const std::string& symbol) const = 0;

    /** @brief Encode a symbol to a symbol index. */
    virtual RamDomain encode(const std::string& symbol) = 0;

    /** @brief Decode a symbol index to a symbol. */
    virtual const std::string& decode(const RamDomain index) const = 0;

    /** @brief Encode a symbol to a symbol index; aliases encode. */
    virtual RamDomain unsafeEncode(const std::string& symbol) = 0;

    /** @brief Decode a symbol index to a symbol; aliases decode. */
    virtual const std::string& unsafeDecode(const RamDomain index) const = 0;

    /**
     * @brief Encode the symbol, it is inserted if it does not exist.
     *
     * @return the symbol index and a boolean indicating if an insertion
     * happened.
     */
    virtual std::pair<RamDomain, bool> findOrInsert(const std::string& symbol) = 0;
};

}  // namespace souffle
