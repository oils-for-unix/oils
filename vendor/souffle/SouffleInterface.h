/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SouffleInterface.h
 *
 * Main include file for generated C++ classes of Souffle
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/datastructure/ConcurrentCache.h"
#include "souffle/utility/MiscUtil.h"
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <regex>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace souffle {

class tuple;

/**
 * Object-oriented wrapper class for Souffle's templatized relations.
 */
class Relation {
public:
    using arity_type = std::size_t;

protected:
    /**
     * Abstract iterator class.
     *
     * When tuples are inserted into a relation, they will be stored contiguously.
     * Intially, the iterator_base of a relation will point to the first tuple inserted.
     * iterator_base can be moved to point to the next tuple until the end.
     * The tuple iterator_base is pointing to can be accessed.
     * However, users can not use this to access tuples since iterator class is protected.
     * Instead, they should use the public class - iterator which interacts with iterator_base.
     */
    class iterator_base {
    protected:
        /**
         * Required for identifying type of iterator
         * (NB: LLVM has no typeinfo).
         *
         * Note: The above statement is not true anymore - should this be made to work the same
         * as Node::operator==?
         *
         * TODO (Honghyw) : Provide a clear documentation of what id is used for.
         */
        std::size_t id;

    public:
        /**
         * Get the ID of the iterator_base object.
         *
         * @return ID of the iterator_base object (std::size_t)
         */
        virtual std::size_t getId() const {
            return id;
        }

        /**
         * Constructor.
         *
         * Create an instance of iterator_base and set its ID to be arg_id.
         *
         * @param arg_id ID of an iterator object (std::size_t)
         */
        iterator_base(std::size_t arg_id) : id(arg_id) {}

        /**
         * Destructor.
         */
        virtual ~iterator_base() = default;

        /**
         * Overload the "++" operator.
         *
         * Increment the iterator_base so that the iterator_base will now point to the next tuple.
         * The definition of this overloading has to be defined by the child class of iterator_base.
         */
        virtual void operator++() = 0;

        /**
         * Overload the "*" operator.
         *
         * Return the tuple that is pointed to by the iterator_base.
         * The definition of this overloading has to be defined by the child class of iterator_base.
         *
         * @return tuple Reference to a tuple object
         */
        virtual tuple& operator*() = 0;

        /**
         * Overload the "==" operator.
         *
         * @param o Reference to an object of the iterator_base class
         * @return A boolean value, if the ID of o is the same as the ID of the current object and equal(o)
         * returns true. Otherwise return false
         */
        bool operator==(const iterator_base& o) const {
            return this->getId() == o.getId() && equal(o);
        }

        /**
         * Clone the iterator_base.
         * The definition of clone has to be defined by the child class of iterator_base.
         *
         * @return An iterator_base pointer
         */
        virtual iterator_base* clone() const = 0;

    protected:
        /**
         * Check if the passed-in object of o is the the same as the current iterator_base.
         *
         * TODO (Honghyw) : Provide a clear documentation of what equal function does.
         *
         * @param o Reference to an object of the iterator_base class
         * @return A boolean value. If two iterator_base are the same return true. Otherwise return false
         */
        virtual bool equal(const iterator_base& o) const = 0;
    };

public:
    /**
     * Destructor.
     */
    virtual ~Relation() = default;

    /**
     * Wrapper class for abstract iterator.
     *
     * Users must use iterator class to access the tuples stored in a relation.
     */
    class iterator {
    protected:
        /*
         * iterator_base class pointer.
         *
         */
        std::unique_ptr<iterator_base> iter = nullptr;

    public:
        /**
         * Constructor.
         */
        iterator() = default;

        /**
         * Move constructor.
         *
         * The new iterator now has ownerhsip of the iterator base.
         *
         * @param arg lvalue reference to an iterator object
         */
        iterator(iterator&& arg) = default;

        /**
         * Constructor.
         *
         * Initialise this iterator with a given iterator base
         *
         * The new iterator has ownership of the iterator base.
         *
         * @param arg An iterator_base class pointer
         */
        iterator(std::unique_ptr<iterator_base> it) : iter(std::move(it)) {}

        /**
         * Destructor.
         *
         * The iterator_base instance iter is pointing is destructed.
         */
        ~iterator() = default;

        /**
         * Constructor.
         *
         * Initialise the iter to be the clone of arg.
         *
         * @param o Reference to an iterator object
         */
        iterator(const iterator& o) : iter(o.iter->clone()) {}

        /**
         * Overload the "=" operator.
         *
         * The original iterator_base instance is destructed.
         */
        iterator& operator=(const iterator& o) {
            iter.reset(o.iter->clone());
            return *this;
        }

        iterator& operator=(iterator&& o) {
            iter.swap(o.iter);
            return *this;
        }

        /**
         * Overload the "++" operator.
         *
         * Increment the iterator_base object that iter is pointing to so that iterator_base object points to
         * next tuple.
         *
         * @return Reference to the iterator object which points to the next tuple in a relation
         */
        iterator& operator++() {
            ++(*iter);
            return *this;
        }

        /**
         * Overload the "++" operator.
         *
         * Copies the iterator, increments itself, and returns the (pre-increment) copy.
         * WARNING: Expensive due to copy! Included for API compatibility.
         *
         * @return Pre-increment copy of `this`.
         */
        iterator operator++(int) {
            auto cpy = *this;
            ++(*this);
            return cpy;
        }

        /**
         * Overload the "*" operator.
         *
         * This will return the tuple that the iterator is pointing to.
         *
         * @return Reference to a tuple object
         */

        tuple& operator*() const {
            return *(*iter);
        }

        /**
         * Overload the "==" operator.
         *
         * Check if either the iter of o and the iter of current object are the same or the corresponding
         * iterator_base objects are the same.
         *
         * @param o Reference to a iterator object
         * @return Boolean. True, if either of them is true. False, otherwise
         */
        bool operator==(const iterator& o) const {
            return (iter == o.iter) || (*iter == *o.iter);
        }

        /**
         * Overload the "!=" operator.
         *
         * Check if the iterator object o is not the same as the current object.
         *
         * @param o Reference to a iterator object
         * @return Boolean. True, if they are not the same. False, otherwise
         */
        bool operator!=(const iterator& o) const {
            return !(*this == o);
        }
    };

    /**
     * Insert a new tuple into the relation.
     * The definition of insert function has to be defined by the child class of relation class.
     *
     * @param t Reference to a tuple class object
     */
    virtual void insert(const tuple& t) = 0;

    /**
     * Check whether a tuple exists in a relation.
     * The definition of contains has to be defined by the child class of relation class.
     *
     * @param t Reference to a tuple object
     * @return Boolean. True, if the tuple exists. False, otherwise
     */
    virtual bool contains(const tuple& t) const = 0;

    /**
     * Return an iterator pointing to the first tuple of the relation.
     * This iterator is used to access the tuples of the relation.
     *
     * @return Iterator
     */
    virtual iterator begin() const = 0;

    /**
     * Return an iterator pointing to next to the last tuple of the relation.
     *
     * @return Iterator
     */
    virtual iterator end() const = 0;

    /**
     * Get the number of tuples in a relation.
     *
     * @return The number of tuples in a relation (std::size_t)
     */
    virtual std::size_t size() const = 0;

    /**
     * Get the name of a relation.
     *
     * @return The name of a relation (std::string)
     */
    virtual std::string getName() const = 0;

    /**
     * Get the attribute type of a relation at the column specified by the parameter.
     * The attribute type is in the form "<primitive type>:<type name>".
     * <primitive type> can be s, f, u, i, r, or + standing for symbol, float,
     * unsigned, integer, record, and ADT respectively,
     * which are the primitive types in Souffle.
     * <type name> is the name given by the user in the Souffle program
     *
     * @param The index of the column starting starting from 0 (std::size_t)
     * @return The constant string of the attribute type
     */
    virtual const char* getAttrType(std::size_t) const = 0;

    /**
     * Get the attribute name of a relation at the column specified by the parameter.
     * The attribute name is the name given to the type by the user in the .decl statement. For example, for
     * ".decl edge (node1:Node, node2:Node)", the attribute names are node1 and node2.
     *
     * @param The index of the column starting starting from 0 (std::size_t)
     * @return The constant string of the attribute name
     */
    virtual const char* getAttrName(std::size_t) const = 0;

    /**
     * Return the arity of a relation.
     * For example for a tuple (1 2) the arity is 2 and for a tuple (1 2 3) the arity is 3.
     *
     * @return Arity of a relation (`arity_type`)
     */
    virtual arity_type getArity() const = 0;

    /**
     * Return the number of auxiliary attributes. Auxiliary attributes
     * are used for provenance and and other alternative evaluation
     * strategies. They are stored as the last attributes of a tuple.
     *
     * @return Number of auxiliary attributes of a relation (`arity_type`)
     */
    virtual arity_type getAuxiliaryArity() const = 0;

    /**
     * Return the number of non-auxiliary attributes.
     * Auxiliary attributes are used for provenance and and other alternative
     * evaluation strategies.
     * They are stored as the last attributes of a tuple.
     *
     * @return Number of non-auxiliary attributes of a relation (`arity_type`)
     */
    arity_type getPrimaryArity() const {
        assert(getAuxiliaryArity() <= getArity());
        return getArity() - getAuxiliaryArity();
    }

    /**
     * Get the symbol table of a relation.
     * The symbols in a tuple to be stored into a relation are stored and assigned with a number in a table
     * called symbol table. For example, to insert ("John","Student") to a relation, "John" and "Student" are
     * stored in symbol table and they are assigned with number say 0 and 1. After this, instead of inserting
     * ("John","Student"), (0, 1) is inserted. When accessing this tuple, 0 and 1 will be looked up in the
     * table and replaced by "John" and "Student". This is done so to save memory space if same symbols are
     * inserted many times. Symbol table has many rows where each row contains a symbol and its corresponding
     * assigned number.
     *
     * @return Reference to a symbolTable object
     */
    virtual SymbolTable& getSymbolTable() const = 0;

    /**
     * Get the signature of a relation.
     * The signature is in the form <<primitive type 1>:<type name 1>,<primitive type 2>:<type name 2>...> for
     * all the attributes in a relation. For example, <s:Node,s:Node>. The primitive type and type name are
     * explained in getAttrType.
     *
     * @return String of the signature of a relation
     */
    std::string getSignature() {
        if (getArity() == 0) {
            return "<>";
        }

        std::string signature = "<" + std::string(getAttrType(0));
        for (arity_type i = 1; i < getArity(); i++) {
            signature += "," + std::string(getAttrType(i));
        }
        signature += ">";
        return signature;
    }

    /**
     * Delete all the tuples in relation.
     *
     * When purge() is called, it sets the head and tail of the table (table is a
     * singly-linked list structure) to nullptr, and for every elements
     * in the table, set the next element pointer points to the current element itself.
     */
    virtual void purge() = 0;
};

/**
 * Defines a tuple for the OO interface such that
 * relations with varying columns can be accessed.
 *
 * Tuples are stored in relations.
 * In Souffle, one row of data to be stored into a relation is represented as a tuple.
 * For example if we have a relation called dog with attributes name, colour and age which are string, string
 * and interger type respectively. One row of data a relation to be stored can be (mydog, black, 3). However,
 * this is not directly stored as a tuple. There will be a symbol table storing the actual content and
 * associate them with numbers (For example, |1|mydog| |2|black| |3|3|). And when this row of data is stored
 * as a tuple, (1, 2, 3) will be stored.
 */
class tuple {
    /**
     * The relation to which the tuple belongs.
     */
    const Relation& relation;

    /**
     * Dynamic array used to store the elements in a tuple.
     */
    std::vector<RamDomain> array;

    /**
     * pos shows what the current position of a tuple is.
     * Initially, pos is 0 meaning we are at the head of the tuple.
     * If we have an empty tuple and try to insert things, pos lets us know where to insert the element. After
     * the element is inserted, pos will be incremented by 1. If we have a tuple with content, pos lets us
     * know where to read the element. After we have read one element, pos will be incremented by 1. pos also
     * helps to make sure we access an insert a tuple within the bound by making sure pos never exceeds the
     * arity of the relation.
     */
    std::size_t pos;

public:
    /**
     * Constructor.
     *
     * Tuples are constructed here by passing a relation, then may be subsequently inserted into that same
     * passed relation. The passed relation pointer will be stored within the tuple instance, while the arity
     * of the relation will be used to initialize the vector holding the elements of the tuple. Where such an
     * element is of integer type, it will be stored directly within the vector. Otherwise, if the element is
     * of a string type, the index of that string within the associated symbol table will be stored instead.
     * The tuple also stores the index of some "current" element, referred to as its position. The constructor
     * initially sets this position to the first (zeroth) element of the tuple, while subsequent methods of
     * this class use that position for element access and modification.
     *
     * @param r Relation pointer pointing to a relation
     */
    tuple(const Relation* r) : relation(*r), array(r->getArity()), pos(0), data(array.data()) {}

    /**
     * Constructor.
     *
     * Tuples are constructed here by passing a tuple.
     * The relation to which the passed tuple belongs to will be stored.
     * The array of the passed tuple, which stores the elements will be stroed.
     * The pos will be set to be the same as the pos of passed tuple.
     * belongs to.
     *
     * @param Reference to a tuple object.
     */
    tuple(const tuple& t) : relation(t.relation), array(t.array), pos(t.pos), data(array.data()) {}

    /**
     * Allows printing using WriteStream.
     */
    const RamDomain* data = nullptr;

    /**
     * Get the reference to the relation to which the tuple belongs.
     *
     * @return Reference to a relation.
     */
    const Relation& getRelation() const {
        return relation;
    }

    /**
     * Return the number of elements in the tuple.
     *
     * @return the number of elements in the tuple (std::size_t).
     */
    Relation::arity_type size() const {
        assert(array.size() <= std::numeric_limits<Relation::arity_type>::max());
        return Relation::arity_type(array.size());
    }

    /**
     * Overload the operator [].
     *
     * Direct access to tuple elements via index and
     * return the element in idx position of a tuple.
     *
     * TODO (Honghyw) : This interface should be hidden and
     * only be used by friendly classes such as
     * iterators; users should not use this interface.
     *
     * @param idx This is the idx of element in a tuple (std::size_t).
     */
    RamDomain& operator[](std::size_t idx) {
        return array[idx];
    }

    /**
     * Overload the operator [].
     *
     * Direct access to tuple elements via index and
     * Return the element in idx position of a tuple. The returned element can not be changed.
     *
     * TODO (Honghyw) : This interface should be hidden and
     * only be used by friendly classes such as
     * iterators; users should not use this interface.
     *
     * @param idx This is the idx of element in a tuple (std::size_t).
     */
    const RamDomain& operator[](std::size_t idx) const {
        return array[idx];
    }

    /**
     * Reset the index giving the "current element" of the tuple to zero.
     */
    void rewind() {
        pos = 0;
    }

    /**
     * Set the "current element" of the tuple to the given string, then increment the index giving the current
     * element.
     *
     * @param str Symbol to be added (std::string)
     * @return Reference to the tuple
     */
    tuple& operator<<(const std::string& str) {
        assert(pos < size() && "exceeded tuple's size");
        assert(*relation.getAttrType(pos) == 's' && "wrong element type");
        array[pos++] = relation.getSymbolTable().encode(str);
        return *this;
    }

    /**
     * Set the "current element" of the tuple to the given int, then increment the index giving the current
     * element.
     *
     * @param integer Integer to be added
     * @return Reference to the tuple
     */
    tuple& operator<<(RamSigned integer) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'i' || *relation.getAttrType(pos) == 'r' ||
                       *relation.getAttrType(pos) == '+') &&
                "wrong element type");
        array[pos++] = integer;
        return *this;
    }

    /**
     * Set the "current element" of the tuple to the given uint, then increment the index giving the current
     * element.
     *
     * @param uint Unsigned number to be added
     * @return Reference to the tuple
     */
    tuple& operator<<(RamUnsigned uint) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'u') && "wrong element type");
        array[pos++] = ramBitCast(uint);
        return *this;
    }

    /**
     * Set the "current element" of the tuple to the given float, then increment the index giving the current
     * element.
     *
     * @param float float to be added
     * @return Reference to the tuple
     */
    tuple& operator<<(RamFloat ramFloat) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'f') && "wrong element type");
        array[pos++] = ramBitCast(ramFloat);
        return *this;
    }

    /**
     * Get the "current element" of the tuple as a string, then increment the index giving the current
     * element.
     *
     * @param str Symbol to be loaded from the tuple(std::string)
     * @return Reference to the tuple
     */
    tuple& operator>>(std::string& str) {
        assert(pos < size() && "exceeded tuple's size");
        assert(*relation.getAttrType(pos) == 's' && "wrong element type");
        str = relation.getSymbolTable().decode(array[pos++]);
        return *this;
    }

    /**
     * Get the "current element" of the tuple as a int, then increment the index giving the current
     * element.
     *
     * @param integer Integer to be loaded from the tuple
     * @return Reference to the tuple
     */
    tuple& operator>>(RamSigned& integer) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'i' || *relation.getAttrType(pos) == 'r' ||
                       *relation.getAttrType(pos) == '+') &&
                "wrong element type");
        integer = ramBitCast<RamSigned>(array[pos++]);
        return *this;
    }

    /**
     * Get the "current element" of the tuple as a unsigned, then increment the index giving the current
     * element.
     *
     * @param uint Unsigned number to be loaded from the tuple
     * @return Reference to the tuple
     */
    tuple& operator>>(RamUnsigned& uint) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'u') && "wrong element type");
        uint = ramBitCast<RamUnsigned>(array[pos++]);
        return *this;
    }

    /**
     * Get the "current element" of the tuple as a float, then increment the index giving the current
     * element.
     *
     * @param ramFloat Float to be loaded from the tuple
     * @return Reference to the tuple
     */
    tuple& operator>>(RamFloat& ramFloat) {
        assert(pos < size() && "exceeded tuple's size");
        assert((*relation.getAttrType(pos) == 'f') && "wrong element type");
        ramFloat = ramBitCast<RamFloat>(array[pos++]);
        return *this;
    }

    /**
     * Iterator for direct access to tuple's data.
     *
     * @see Relation::iteraor::begin()
     */
    decltype(array)::iterator begin() {
        return array.begin();
    }

    /**
     * Construct using initialisation list.
     */
    tuple(const Relation* relation, std::initializer_list<RamDomain> tupleList)
            : relation(*relation), array(tupleList), pos(tupleList.size()), data(array.data()) {
        assert(tupleList.size() == relation->getArity() && "tuple arity does not match relation arity");
    }
};

/**
 * Abstract base class for generated Datalog programs.
 */
class SouffleProgram {
protected:
    /**
     * Define a relation map for external access, when getRelation(name) is called,
     * the relation with the given name will be returned from this map,
     * relationMap stores all the relations in a map with its name
     * as the key and relation as the value.
     */
    std::map<std::string, Relation*> relationMap;

    /**
     * inputRelations stores all the input relation in a vector.
     */
    std::vector<Relation*> inputRelations;

    /**
     * outputRelations stores all the output relation in a vector.
     */
    std::vector<Relation*> outputRelations;

    /**
     * internalRelation stores all the relation in a vector that are neither an input or an output.
     */
    std::vector<Relation*> internalRelations;

    /**
     * allRelations store all the relation in a vector.
     */
    std::vector<Relation*> allRelations;

    /**
     * The number of threads used by OpenMP
     */
    std::size_t numThreads = 1;

    /**
     * Enable I/O
     */
    bool performIO = false;

    /**
     * Prune Intermediate Relations when there is no further use for them.
     */
    bool pruneImdtRels = true;

    /**
     * Add the relation to relationMap (with its name) and allRelations,
     * depends on the properties of the relation, if the relation is an input relation, it will be added to
     * inputRelations, else if the relation is an output relation, it will be added to outputRelations,
     * otherwise will add to internalRelations. (a relation could be both input and output at the same time.)
     *
     * @param name the name of the relation (std::string)
     * @param rel a reference to the relation
     * @param isInput a bool argument, true if the relation is a input relation, else false (bool)
     * @param isOnput a bool argument, true if the relation is a ouput relation, else false (bool)
     */
    void addRelation(const std::string& name, Relation& rel, bool isInput, bool isOutput) {
        relationMap[name] = &rel;
        allRelations.push_back(&rel);
        if (isInput) {
            inputRelations.push_back(&rel);
        }
        if (isOutput) {
            outputRelations.push_back(&rel);
        }
        if (!isInput && !isOutput) {
            internalRelations.push_back(&rel);
        }
    }

    [[deprecated("pass `rel` by reference; `rel` may not be null"), maybe_unused]] void addRelation(
            const std::string& name, Relation* rel, bool isInput, bool isOutput) {
        assert(rel && "`rel` may not be null");
        addRelation(name, *rel, isInput, isOutput);
    }

public:
    /**
     * Destructor.
     *
     * Destructor of SouffleProgram.
     */
    virtual ~SouffleProgram() = default;

    /**
     * Execute the souffle program, without any loads or stores, and live-profiling (in case it is switched
     * on).
     */
    virtual void run() {}

    /**
     * Execute program, loading inputs and storing outputs as required.
     * File IO types can use the given directories to find their input file.
     *
     * @param inputDirectory If non-empty, specifies the input directory
     * @param outputDirectory If non-empty, specifies the output directory
     * @param performIO Enable I/O operations
     * @param pruneImdtRels Prune intermediate relations
     */
    virtual void runAll(std::string inputDirectory = "", std::string outputDirectory = "",
            bool performIO = false, bool pruneImdtRels = true) = 0;

    /**
     * Read all input relations.
     *
     * File IO types can use the given directory to find their input file.
     * @param inputDirectory If non-empty, specifies the input directory
     */
    virtual void loadAll(std::string inputDirectory = "") = 0;

    /**
     * Store all output relations.
     *
     * File IO types can use the given directory to find their input file.
     * @param outputDirectory If non-empty, specifies the output directory
     */
    virtual void printAll(std::string outputDirectory = "") = 0;

    /**
     * Output all the input relations in stdout, without generating any files. (for debug purposes).
     */
    virtual void dumpInputs() = 0;

    /**
     * Output all the output relations in stdout, without generating any files. (for debug purposes).
     */
    virtual void dumpOutputs() = 0;

    /**
     * Set the number of threads to be used
     */
    virtual void setNumThreads(std::size_t numThreadsValue) {
        this->numThreads = numThreadsValue;
    }

    /**
     * Get the number of threads to be used
     */
    std::size_t getNumThreads() {
        return numThreads;
    }

    /**
     * Get Relation by its name from relationMap, if relation not found, return a nullptr.
     *
     * @param name The name of the target relation (const std::string)
     * @return The pointer of the target relation, or null pointer if the relation not found (Relation*)
     */
    Relation* getRelation(const std::string& name) const {
        auto it = relationMap.find(name);
        if (it != relationMap.end()) {
            return (*it).second;
        } else {
            return nullptr;
        }
    };

    /**
     * Return the size of the target relation from relationMap.
     *
     * @param name The name of the target relation (const std::string)
     * @return The size of the target relation (std::size_t)
     */
    std::optional<std::size_t> getRelationSize(const std::string& name) const {
        if (auto* rel = getRelation(name)) {
            return rel->size();
        }

        return std::nullopt;
    }

    /**
     * Return the name of the target relation from relationMap.
     *
     * @param name The name of the target relation (const std::string)
     * @return The name of the target relation (std::string)
     */
    std::optional<std::string> getRelationName(const std::string& name) const {
        if (auto* rel = getRelation(name)) {
            return rel->getName();
        }

        return std::nullopt;
    }

    /**
     * Getter of outputRelations, which this vector structure contains all output relations.
     *
     * @return outputRelations (std::vector)
     * @see outputRelations
     */
    std::vector<Relation*> getOutputRelations() const {
        return outputRelations;
    }

    /**
     * Getter of inputRelations, which this vector structure contains all input relations.
     *
     * @return intputRelations (std::vector)
     * @see inputRelations
     */
    std::vector<Relation*> getInputRelations() const {
        return inputRelations;
    }

    /**
     * Getter of internalRelations, which this vector structure contains all relations
     * that are neither an input relation or an output relation.
     *
     * @return internalRelations (std::vector)
     * @see internalRelations
     */
    std::vector<Relation*> getInternalRelations() const {
        return internalRelations;
    }

    /**
     * Getter of allRelations, which this vector structure contains all relations.
     *
     * @return allRelations (std::vector)
     * @see allRelations
     */
    std::vector<Relation*> getAllRelations() const {
        return allRelations;
    }

    /**
     * Execute a subroutine
     * @param name  Name of a subroutine (std:string)
     * @param arg Arguments of the subroutine (std::vector<RamDomain>&)
     * @param ret Return values of the subroutine (std::vector<RamDomain>&)
     */
    virtual void executeSubroutine(std::string /* name */, const std::vector<RamDomain>& /* args */,
            std::vector<RamDomain>& /* ret */) {
        fatal("unknown subroutine");
    }

    /**
     * Get the symbol table of the program.
     */
    virtual SymbolTable& getSymbolTable() = 0;

    /**
     * Get the record table of the program.
     */
    virtual RecordTable& getRecordTable() = 0;

    /**
     * Remove all the tuples from the outputRelations, calling the purge method of each.
     *
     * @see Relation::purge()
     */
    void purgeOutputRelations() {
        for (Relation* relation : outputRelations) {
            relation->purge();
        }
    }

    /**
     * Remove all the tuples from the inputRelations, calling the purge method of each.
     *
     * @see Relation::purge()
     */
    void purgeInputRelations() {
        for (Relation* relation : inputRelations) {
            relation->purge();
        }
    }

    /**
     * Remove all the tuples from the internalRelations, calling the purge method of each.
     *
     * @see Relation::purge()
     */
    void purgeInternalRelations() {
        for (Relation* relation : internalRelations) {
            relation->purge();
        }
    }

    /**
     * Helper function for the wrapper function Relation::insert() and Relation::contains().
     */
    template <typename Tuple, std::size_t N>
    struct tuple_insert {
        static void add(const Tuple& t, souffle::tuple& t1) {
            tuple_insert<Tuple, N - 1>::add(t, t1);
            t1 << std::get<N - 1>(t);
        }
    };

    /**
     * Helper function for the wrapper function Relation::insert() and Relation::contains() for the
     * first element of the tuple.
     */
    template <typename Tuple>
    struct tuple_insert<Tuple, 1> {
        static void add(const Tuple& t, souffle::tuple& t1) {
            t1 << std::get<0>(t);
        }
    };

    /**
     * Insert function with std::tuple as input (wrapper)
     *
     * @param t The insert tuple (std::tuple)
     * @param relation The relation that perform insert operation (Relation*)
     * @see Relation::insert()
     */
    template <typename... Args>
    void insert(const std::tuple<Args...>& t, Relation* relation) {
        tuple t1(relation);
        tuple_insert<decltype(t), sizeof...(Args)>::add(t, t1);
        relation->insert(t1);
    }

    /**
     * Contains function with std::tuple as input (wrapper)
     *
     * @param t The existence searching tuple (std::tuple)
     * @param relation The relation that perform contains operation (Relation*)
     * @return A boolean value, return true if the tuple found, otherwise return false
     * @see Relation::contains()
     */
    template <typename... Args>
    bool contains(const std::tuple<Args...>& t, Relation* relation) {
        tuple t1(relation);
        tuple_insert<decltype(t), sizeof...(Args)>::add(t, t1);
        return relation->contains(t1);
    }

    /**
     * Set perform-I/O flag
     */
    void setPerformIO(bool performIOArg) {
        performIO = performIOArg;
    }

    /**
     * Set prune-intermediate-relations flag
     */
    void setPruneImdtRels(bool pruneImdtRelsArg) {
        pruneImdtRels = pruneImdtRelsArg;
    }
};

/**
 * Abstract program factory class.
 */
class ProgramFactory {
protected:
    /**
     * Singly linked-list to store all program factories
     * Note that STL data-structures are not possible due
     * to "static initialization order fiasco (problem)".
     * (The problem of the order static objects get initialized, causing effect
     * such as program access static variables before they initialized.)
     * The static container needs to be a primitive type such as pointer
     * set to NULL.
     * Link to next factory.
     */
    ProgramFactory* link = nullptr;

    /**
     * The name of factory.
     */
    std::string name;

protected:
    /**
     * Constructor.
     *
     * Constructor adds factory to static singly-linked list
     * for registration.
     */
    ProgramFactory(std::string name) : name(std::move(name)) {
        registerFactory(this);
    }

private:
    /**
     * Helper method for creating a factory map, which map key is the name of the program factory, map value
     * is the pointer of the ProgramFactory.
     *
     * TODO (NubKel) : Improve documentation of use and interaction between inline and static, here and for
     * the whole class.
     *
     * @return The factory registration map (std::map)
     */
    static inline std::map<std::string, ProgramFactory*>& getFactoryRegistry() {
        static std::map<std::string, ProgramFactory*> factoryReg;
        return factoryReg;
    }

protected:
    /**
     * Create and insert a factory into the factoryReg map.
     *
     * @param factory Pointer of the program factory (ProgramFactory*)
     */
    static inline void registerFactory(ProgramFactory* factory) {
        auto& entry = getFactoryRegistry()[factory->name];
        assert(!entry && "double-linked/defined souffle analyis");
        entry = factory;
    }

    /**
     * Find a factory by its name, return the fatory if found, return nullptr if the
     * factory not found.
     *
     * @param factoryName The factory name (const std::string)
     * @return The pointer of the target program factory, or null pointer if the program factory not found
     * (ProgramFactory*)
     */
    static inline ProgramFactory* find(const std::string& factoryName) {
        const auto& reg = getFactoryRegistry();
        auto pos = reg.find(factoryName);
        return (pos == reg.end()) ? nullptr : pos->second;
    }

    /**
     * Create new instance (abstract).
     */
    virtual SouffleProgram* newInstance() = 0;

public:
    /**
     * Destructor.
     *
     * Destructor of ProgramFactory.
     */
    virtual ~ProgramFactory() = default;

    /**
     * Create an instance by finding the name of the program factory, return nullptr if the instance not
     * found.
     *
     * @param name Instance name (const std::string)
     * @return The new instance(SouffleProgram*), or null pointer if the instance not found
     */
    static SouffleProgram* newInstance(const std::string& name) {
        ProgramFactory* factory = find(name);
        if (factory != nullptr) {
            return factory->newInstance();
        } else {
            return nullptr;
        }
    }
};
}  // namespace souffle
