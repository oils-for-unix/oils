/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file CompiledSouffle.h
 *
 * Main include file for generated C++ classes of Souffle
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SignalHandler.h"
#include "souffle/SouffleInterface.h"
#include "souffle/SymbolTable.h"
#include "souffle/datastructure/BTreeDelete.h"
#include "souffle/datastructure/Brie.h"
#include "souffle/datastructure/ConcurrentCache.h"
#include "souffle/datastructure/EqRel.h"
#include "souffle/datastructure/Info.h"
#include "souffle/datastructure/Nullaries.h"
#include "souffle/datastructure/RecordTableImpl.h"
#include "souffle/datastructure/SymbolTableImpl.h"
#include "souffle/datastructure/Table.h"
#include "souffle/io/IOSystem.h"
#include "souffle/io/WriteStream.h"
#include "souffle/utility/EvaluatorUtil.h"

#if defined(_OPENMP)
#include <omp.h>
#endif

namespace souffle {

extern "C" {
inline souffle::SouffleProgram* getInstance(const char* p) {
    return souffle::ProgramFactory::newInstance(p);
}
}

/**
 * Relation wrapper used internally in the generated Datalog program
 */
template <class RelType>
class RelationWrapper : public souffle::Relation {
public:
    static constexpr arity_type Arity = RelType::Arity;
    using TupleType = Tuple<RamDomain, Arity>;
    using AttrStrSeq = std::array<const char*, Arity>;

private:
    RelType& relation;
    SouffleProgram& program;
    std::string name;
    AttrStrSeq attrTypes;
    AttrStrSeq attrNames;
    const uint32_t id;
    const arity_type numAuxAttribs;

    // NB: internal wrapper. does not satisfy the `iterator` concept.
    class iterator_wrapper : public iterator_base {
        typename RelType::iterator it;
        const Relation* relation;
        tuple t;

    public:
        iterator_wrapper(uint32_t arg_id, const Relation* rel, typename RelType::iterator arg_it)
                : iterator_base(arg_id), it(std::move(arg_it)), relation(rel), t(rel) {}
        void operator++() override {
            ++it;
        }
        tuple& operator*() override {
            auto&& value = *it;
            t.rewind();
            for (std::size_t i = 0; i < Arity; i++)
                t[i] = value[i];
            return t;
        }
        iterator_base* clone() const override {
            return new iterator_wrapper(*this);
        }

    protected:
        bool equal(const iterator_base& o) const override {
            const auto& casted = asAssert<iterator_wrapper>(o);
            return it == casted.it;
        }
    };

public:
    RelationWrapper(uint32_t id, RelType& r, SouffleProgram& p, std::string name, const AttrStrSeq& t,
            const AttrStrSeq& n, arity_type numAuxAttribs)
            : relation(r), program(p), name(std::move(name)), attrTypes(t), attrNames(n), id(id),
              numAuxAttribs(numAuxAttribs) {}

    iterator begin() const override {
        return iterator(mk<iterator_wrapper>(id, this, relation.begin()));
    }
    iterator end() const override {
        return iterator(mk<iterator_wrapper>(id, this, relation.end()));
    }

    void insert(const tuple& arg) override {
        TupleType t;
        assert(&arg.getRelation() == this && "wrong relation");
        assert(arg.size() == Arity && "wrong tuple arity");
        for (std::size_t i = 0; i < Arity; i++) {
            t[i] = arg[i];
        }
        relation.insert(t);
    }
    bool contains(const tuple& arg) const override {
        TupleType t;
        assert(arg.size() == Arity && "wrong tuple arity");
        for (std::size_t i = 0; i < Arity; i++) {
            t[i] = arg[i];
        }
        return relation.contains(t);
    }
    std::size_t size() const override {
        return relation.size();
    }
    std::string getName() const override {
        return name;
    }
    const char* getAttrType(std::size_t arg) const override {
        assert(arg < Arity && "attribute out of bound");
        return attrTypes[arg];
    }
    const char* getAttrName(std::size_t arg) const override {
        assert(arg < Arity && "attribute out of bound");
        return attrNames[arg];
    }
    arity_type getArity() const override {
        return Arity;
    }
    arity_type getAuxiliaryArity() const override {
        return numAuxAttribs;
    }
    SymbolTable& getSymbolTable() const override {
        return program.getSymbolTable();
    }

    /** Eliminate all the tuples in relation*/
    void purge() override {
        relation.purge();
    }
};

}  // namespace souffle
