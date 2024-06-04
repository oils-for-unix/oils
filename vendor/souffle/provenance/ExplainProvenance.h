/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ExplainProvenance.h
 *
 * Abstract class for implementing an instance of the explain interface for provenance
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/SouffleInterface.h"
#include "souffle/SymbolTable.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StringUtil.h"
#include "souffle/utility/tinyformat.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace souffle {
class TreeNode;

/** Equivalence class for variables in query command */
class Equivalence {
public:
    /** Destructor */
    ~Equivalence() = default;

    /**
     * Constructor for Equvialence class
     * @param t, type of the variable
     * @param s, symbol of the variable
     * @param idx, first occurence of the variable
     * */
    Equivalence(char t, std::string s, std::pair<std::size_t, std::size_t> idx)
            : type(t), symbol(std::move(s)) {
        indices.push_back(idx);
    }

    /** Copy constructor */
    Equivalence(const Equivalence& o) = default;

    /** Copy assignment operator */
    Equivalence& operator=(const Equivalence& o) = default;

    /** Add index at the end of indices vector */
    void push_back(std::pair<std::size_t, std::size_t> idx) {
        indices.push_back(idx);
    }

    /** Verify if elements at the indices are equivalent in the given product */
    bool verify(const std::vector<tuple>& product) const {
        for (std::size_t i = 1; i < indices.size(); ++i) {
            if (product[indices[i].first][indices[i].second] !=
                    product[indices[i - 1].first][indices[i - 1].second]) {
                return false;
            }
        }
        return true;
    }

    /** Extract index of the first occurrence of the varible */
    const std::pair<std::size_t, std::size_t>& getFirstIdx() const {
        return indices[0];
    }

    /** Get indices of equivalent variables */
    const std::vector<std::pair<std::size_t, std::size_t>>& getIndices() const {
        return indices;
    }

    /** Get type of the variable of the equivalence class,
     * 'i' for RamSigned, 's' for symbol
     * 'u' for RamUnsigned, 'f' for RamFloat
     */
    char getType() const {
        return type;
    }

    /** Get the symbol of variable */
    const std::string& getSymbol() const {
        return symbol;
    }

private:
    char type;
    std::string symbol;
    std::vector<std::pair<std::size_t, std::size_t>> indices;
};

/** Constant constraints for values in query command */
class ConstConstraint {
public:
    /** Constructor */
    ConstConstraint() = default;

    /** Destructor */
    ~ConstConstraint() = default;

    /** Add constant constraint at the end of constConstrs vector */
    void push_back(std::pair<std::pair<std::size_t, std::size_t>, RamDomain> constr) {
        constConstrs.push_back(constr);
    }

    /** Verify if the query product satisfies constant constraint */
    bool verify(const std::vector<tuple>& product) const {
        return std::all_of(constConstrs.begin(), constConstrs.end(), [&product](auto constr) {
            return product[constr.first.first][constr.first.second] == constr.second;
        });
    }

    /** Get the constant constraint vector */
    std::vector<std::pair<std::pair<std::size_t, std::size_t>, RamDomain>>& getConstraints() {
        return constConstrs;
    }

    const std::vector<std::pair<std::pair<std::size_t, std::size_t>, RamDomain>>& getConstraints() const {
        return constConstrs;
    }

private:
    std::vector<std::pair<std::pair<std::size_t, std::size_t>, RamDomain>> constConstrs;
};

/** utility function to split a string */
inline std::vector<std::string> split(const std::string& s, char delim, int times = -1) {
    std::vector<std::string> v;
    std::stringstream ss(s);
    std::string item;

    while ((times > 0 || times <= -1) && std::getline(ss, item, delim)) {
        v.push_back(item);
        times--;
    }

    if (ss.peek() != EOF) {
        std::string remainder;
        std::getline(ss, remainder);
        v.push_back(remainder);
    }

    return v;
}

class ExplainProvenance {
public:
    ExplainProvenance(SouffleProgram& prog) : prog(prog), symTable(prog.getSymbolTable()) {}
    virtual ~ExplainProvenance() = default;

    virtual void setup() = 0;

    virtual Own<TreeNode> explain(
            std::string relName, std::vector<std::string> tuple, std::size_t depthLimit) = 0;

    virtual Own<TreeNode> explainSubproof(std::string relName, RamDomain label, std::size_t depthLimit) = 0;

    virtual std::vector<std::string> explainNegationGetVariables(
            std::string relName, std::vector<std::string> args, std::size_t ruleNum) = 0;

    virtual Own<TreeNode> explainNegation(std::string relName, std::size_t ruleNum,
            const std::vector<std::string>& tuple, std::map<std::string, std::string>& bodyVariables) = 0;

    virtual std::string getRule(std::string relName, std::size_t ruleNum) = 0;

    virtual std::vector<std::string> getRules(const std::string& relName) = 0;

    virtual std::string measureRelation(std::string relName) = 0;

    virtual void printRulesJSON(std::ostream& os) = 0;

    /**
     * Process query with given arguments
     * @param rels, vector of relation, argument pairs
     * */
    virtual void queryProcess(const std::vector<std::pair<std::string, std::vector<std::string>>>& rels) = 0;

protected:
    SouffleProgram& prog;
    SymbolTable& symTable;

    std::vector<RamDomain> argsToNums(
            const std::string& relName, const std::vector<std::string>& args) const {
        std::vector<RamDomain> nums;

        auto rel = prog.getRelation(relName);
        if (rel == nullptr) {
            return nums;
        }

        for (std::size_t i = 0; i < args.size(); i++) {
            nums.push_back(valueRead(rel->getAttrType(i)[0], args[i]));
        }

        return nums;
    }

    /**
     * Decode arguments from their ram representation and return as strings.
     **/
    std::vector<std::string> decodeArguments(
            const std::string& relName, const std::vector<RamDomain>& nums) const {
        std::vector<std::string> args;

        auto rel = prog.getRelation(relName);
        if (rel == nullptr) {
            return args;
        }

        for (std::size_t i = 0; i < nums.size(); i++) {
            args.push_back(valueShow(rel->getAttrType(i)[0], nums[i]));
        }

        return args;
    }

    std::string valueShow(const char type, const RamDomain value) const {
        switch (type) {
            case 'i': return tfm::format("%d", ramBitCast<RamSigned>(value));
            case 'u': return tfm::format("%d", ramBitCast<RamUnsigned>(value));
            case 'f': return tfm::format("%f", ramBitCast<RamFloat>(value));
            case 's': return tfm::format("\"%s\"", symTable.decode(value));
            case 'r': return tfm::format("record #%d", value);
            default: fatal("unhandled type attr code");
        }
    }

    RamDomain valueRead(const char type, const std::string& value) const {
        switch (type) {
            case 'i': return ramBitCast(RamSignedFromString(value));
            case 'u': return ramBitCast(RamUnsignedFromString(value));
            case 'f': return ramBitCast(RamFloatFromString(value));
            case 's':
                assert(2 <= value.size() && value[0] == '"' && value.back() == '"');
                return symTable.encode(value.substr(1, value.size() - 2));
            case 'r': fatal("not implemented");
            default: fatal("unhandled type attr code");
        }
    }
};

}  // end of namespace souffle
