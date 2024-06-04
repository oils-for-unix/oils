/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ExplainProvenanceImpl.h
 *
 * Implementation of abstract class in ExplainProvenance.h for guided Impl provenance
 *
 ***********************************************************************/

#pragma once

#include "souffle/BinaryConstraintOps.h"
#include "souffle/RamTypes.h"
#include "souffle/SouffleInterface.h"
#include "souffle/SymbolTable.h"
#include "souffle/provenance/ExplainProvenance.h"
#include "souffle/provenance/ExplainTree.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StreamUtil.h"
#include "souffle/utility/StringUtil.h"
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <sstream>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace souffle {

using namespace stream_write_qualified_char_as_number;

class ExplainProvenanceImpl : public ExplainProvenance {
    using arity_type = Relation::arity_type;

public:
    ExplainProvenanceImpl(SouffleProgram& prog) : ExplainProvenance(prog) {
        setup();
    }

    void setup() override {
        // for each clause, store a mapping from the head relation name to body relation names
        for (auto& rel : prog.getAllRelations()) {
            std::string name = rel->getName();

            // only process info relations
            if (name.find("@info") == std::string::npos) {
                continue;
            }

            // find all the info tuples
            for (auto& tuple : *rel) {
                std::vector<std::string> bodyLiterals;

                // first field is rule number
                RamDomain ruleNum;
                tuple >> ruleNum;

                // middle fields are body literals
                for (std::size_t i = 1; i + 1 < rel->getArity(); i++) {
                    std::string bodyLit;
                    tuple >> bodyLit;
                    bodyLiterals.push_back(bodyLit);
                }

                // last field is the rule itself
                std::string rule;
                tuple >> rule;

                std::string relName = name.substr(0, name.find(".@info"));
                info.insert({std::make_pair(relName, ruleNum), bodyLiterals});
                rules.insert({std::make_pair(relName, ruleNum), rule});
            }
        }
    }

    Own<TreeNode> explain(std::string relName, std::vector<RamDomain> tuple, int ruleNum, int levelNum,
            std::size_t depthLimit) {
        std::stringstream joinedArgs;
        joinedArgs << join(decodeArguments(relName, tuple), ", ");
        auto joinedArgsStr = joinedArgs.str();

        // if fact
        if (levelNum == 0) {
            return mk<LeafNode>(relName + "(" + joinedArgsStr + ")");
        }

        assert(contains(info, std::make_pair(relName, ruleNum)) && "invalid rule for tuple");

        // if depth limit exceeded
        if (depthLimit <= 1) {
            tuple.push_back(ruleNum);
            tuple.push_back(levelNum);

            // find if subproof exists already
            std::size_t idx = 0;
            auto it = std::find(subproofs.begin(), subproofs.end(), tuple);
            if (it != subproofs.end()) {
                idx = it - subproofs.begin();
            } else {
                subproofs.push_back(tuple);
                idx = subproofs.size() - 1;
            }

            return mk<LeafNode>("subproof " + relName + "(" + std::to_string(idx) + ")");
        }

        tuple.push_back(levelNum);

        auto internalNode =
                mk<InnerNode>(relName + "(" + joinedArgsStr + ")", "(R" + std::to_string(ruleNum) + ")");

        // make return vector pointer
        std::vector<RamDomain> ret;

        // execute subroutine to get subproofs
        prog.executeSubroutine(relName + "_" + std::to_string(ruleNum) + "_subproof", tuple, ret);

        // recursively get nodes for subproofs
        std::size_t tupleCurInd = 0;
        auto bodyRelations = info.at(std::make_pair(relName, ruleNum));

        // start from begin + 1 because the first element represents the head atom
        for (auto it = bodyRelations.begin() + 1; it < bodyRelations.end(); it++) {
            std::string bodyLiteral = *it;
            // split bodyLiteral since it contains relation name plus arguments
            std::string bodyRel = splitString(bodyLiteral, ',')[0];

            // check whether the current atom is a constraint
            assert(bodyRel.size() > 0 && "body of a relation should have positive length");
            bool isConstraint = contains(constraintList, bodyRel);

            // handle negated atom names
            auto bodyRelAtomName = bodyRel;
            if (bodyRel[0] == '!' && bodyRel != "!=") {
                bodyRelAtomName = bodyRel.substr(1);
            }

            // traverse subroutine return
            std::size_t arity;
            std::size_t auxiliaryArity;
            if (isConstraint) {
                // we only handle binary constraints, and assume arity is 4 to account for hidden provenance
                // annotations
                arity = 4;
                auxiliaryArity = 2;
            } else {
                arity = prog.getRelation(bodyRelAtomName)->getArity();
                auxiliaryArity = prog.getRelation(bodyRelAtomName)->getAuxiliaryArity();
            }
            auto tupleEnd = tupleCurInd + arity;

            // store current tuple
            std::vector<RamDomain> subproofTuple;

            for (; tupleCurInd < tupleEnd - auxiliaryArity; tupleCurInd++) {
                subproofTuple.push_back(ret[tupleCurInd]);
            }

            int subproofRuleNum = ret[tupleCurInd];
            int subproofLevelNum = ret[tupleCurInd + 1];

            tupleCurInd += 2;

            // for a negation, display the corresponding tuple and do not recurse
            if (bodyRel[0] == '!' && bodyRel != "!=") {
                std::stringstream joinedTuple;
                joinedTuple << join(decodeArguments(bodyRelAtomName, subproofTuple), ", ");
                auto joinedTupleStr = joinedTuple.str();
                internalNode->add_child(mk<LeafNode>(bodyRel + "(" + joinedTupleStr + ")"));
                internalNode->setSize(internalNode->getSize() + 1);
                // for a binary constraint, display the corresponding values and do not recurse
            } else if (isConstraint) {
                std::stringstream joinedConstraint;

                // FIXME: We need type info in order to figure out how to print arguments.
                BinaryConstraintOp rawBinOp = toBinaryConstraintOp(bodyRel);
                if (isOrderedBinaryConstraintOp(rawBinOp)) {
                    joinedConstraint << subproofTuple[0] << " " << bodyRel << " " << subproofTuple[1];
                } else {
                    joinedConstraint << bodyRel << "(\"" << symTable.decode(subproofTuple[0]) << "\", \""
                                     << symTable.decode(subproofTuple[1]) << "\")";
                }

                internalNode->add_child(mk<LeafNode>(joinedConstraint.str()));
                internalNode->setSize(internalNode->getSize() + 1);
                // otherwise, for a normal tuple, recurse
            } else {
                auto child =
                        explain(bodyRel, subproofTuple, subproofRuleNum, subproofLevelNum, depthLimit - 1);
                internalNode->setSize(internalNode->getSize() + child->getSize());
                internalNode->add_child(std::move(child));
            }

            tupleCurInd = tupleEnd;
        }

        return internalNode;
    }

    Own<TreeNode> explain(
            std::string relName, std::vector<std::string> args, std::size_t depthLimit) override {
        auto tuple = argsToNums(relName, args);
        if (tuple.empty()) {
            return mk<LeafNode>("Relation not found");
        }

        std::tuple<int, int> tupleInfo = findTuple(relName, tuple);

        int ruleNum = std::get<0>(tupleInfo);
        int levelNum = std::get<1>(tupleInfo);

        if (ruleNum < 0 || levelNum == -1) {
            return mk<LeafNode>("Tuple not found");
        }

        return explain(relName, tuple, ruleNum, levelNum, depthLimit);
    }

    Own<TreeNode> explainSubproof(
            std::string relName, RamDomain subproofNum, std::size_t depthLimit) override {
        if (subproofNum >= (int)subproofs.size()) {
            return mk<LeafNode>("Subproof not found");
        }

        auto tup = subproofs[subproofNum];

        auto rel = prog.getRelation(relName);

        assert(rel->getAuxiliaryArity() == 2 && "unexpected auxiliary arity in provenance context");

        RamDomain ruleNum;
        ruleNum = tup[rel->getArity() - 2];

        RamDomain levelNum;
        levelNum = tup[rel->getArity() - 1];

        tup.erase(tup.begin() + rel->getArity() - 2, tup.end());

        return explain(relName, tup, ruleNum, levelNum, depthLimit);
    }

    std::vector<std::string> explainNegationGetVariables(
            std::string relName, std::vector<std::string> args, std::size_t ruleNum) override {
        std::vector<std::string> variables;

        // check that the tuple actually doesn't exist
        std::tuple<int, int> foundTuple = findTuple(relName, argsToNums(relName, args));
        if (std::get<0>(foundTuple) != -1 || std::get<1>(foundTuple) != -1) {
            // return a sentinel value
            return std::vector<std::string>({"@"});
        }

        // atom meta information stored for the current rule
        auto atoms = info[std::make_pair(relName, ruleNum)];

        // the info stores the set of atoms, if there is only 1 atom, then it must be the head, so it must be
        // a fact
        if (atoms.size() <= 1) {
            return std::vector<std::string>({"@fact"});
        }

        // atoms[0] represents variables in the head atom
        auto headVariables = splitString(atoms[0], ',');

        auto isVariable = [&](std::string arg) {
            return !(isNumber(arg.c_str()) || arg[0] == '\"' || arg == "_");
        };

        // check that head variable bindings make sense, i.e. for a head like a(x, x), make sure both x are
        // the same value
        std::map<std::string, std::string> headVariableMapping;
        for (std::size_t i = 0; i < headVariables.size(); i++) {
            if (!isVariable(headVariables[i])) {
                continue;
            }

            if (headVariableMapping.find(headVariables[i]) == headVariableMapping.end()) {
                headVariableMapping[headVariables[i]] = args[i];
            } else {
                if (headVariableMapping[headVariables[i]] != args[i]) {
                    return std::vector<std::string>({"@non_matching"});
                }
            }
        }

        // get body variables
        std::vector<std::string> uniqueBodyVariables;
        for (auto it = atoms.begin() + 1; it < atoms.end(); it++) {
            auto atomRepresentation = splitString(*it, ',');

            // atomRepresentation.begin() + 1 because the first element is the relation name of the atom
            // which is not relevant for finding variables
            for (auto atomIt = atomRepresentation.begin() + 1; atomIt < atomRepresentation.end(); atomIt++) {
                if (!isVariable(*atomIt)) {
                    continue;
                }

                if (!contains(uniqueBodyVariables, *atomIt) && !contains(headVariables, *atomIt)) {
                    uniqueBodyVariables.push_back(*atomIt);
                }
            }
        }

        return uniqueBodyVariables;
    }

    Own<TreeNode> explainNegation(std::string relName, std::size_t ruleNum,
            const std::vector<std::string>& tuple,
            std::map<std::string, std::string>& bodyVariables) override {
        // construct a vector of unique variables that occur in the rule
        std::vector<std::string> uniqueVariables;

        // we also need to know the type of each variable
        std::map<std::string, char> variableTypes;

        // atom meta information stored for the current rule
        auto atoms = info.at(std::make_pair(relName, ruleNum));

        // atoms[0] represents variables in the head atom
        auto headVariables = splitString(atoms[0], ',');

        uniqueVariables.insert(uniqueVariables.end(), headVariables.begin(), headVariables.end());

        auto isVariable = [&](std::string arg) {
            return !(isNumber(arg.c_str()) || arg[0] == '\"' || arg == "_");
        };

        // get body variables
        for (auto it = atoms.begin() + 1; it < atoms.end(); it++) {
            auto atomRepresentation = splitString(*it, ',');

            // atomRepresentation.begin() + 1 because the first element is the relation name of the atom
            // which is not relevant for finding variables
            for (auto atomIt = atomRepresentation.begin() + 1; atomIt < atomRepresentation.end(); atomIt++) {
                if (!contains(uniqueVariables, *atomIt) && !contains(headVariables, *atomIt)) {
                    // ignore non-variables
                    if (!isVariable(*atomIt)) {
                        continue;
                    }

                    uniqueVariables.push_back(*atomIt);

                    if (!contains(constraintList, atomRepresentation[0])) {
                        // store type of variable
                        auto currentRel = prog.getRelation(atomRepresentation[0]);
                        assert(currentRel != nullptr &&
                                ("relation " + atomRepresentation[0] + " doesn't exist").c_str());
                        variableTypes[*atomIt] =
                                *currentRel->getAttrType(atomIt - atomRepresentation.begin() - 1);
                    } else if (atomIt->find("agg_") != std::string::npos) {
                        variableTypes[*atomIt] = 'i';
                    }
                }
            }
        }

        std::vector<RamDomain> args;

        std::size_t varCounter = 0;

        // construct arguments to pass in to the subroutine
        // - this contains the variable bindings selected by the user

        // add number representation of tuple
        auto tupleNums = argsToNums(relName, tuple);
        args.insert(args.end(), tupleNums.begin(), tupleNums.end());
        varCounter += tuple.size();

        while (varCounter < uniqueVariables.size()) {
            auto var = uniqueVariables[varCounter];
            auto varValue = bodyVariables[var];
            if (variableTypes[var] == 's') {
                if (varValue.size() >= 2 && varValue[0] == '"' && varValue[varValue.size() - 1] == '"') {
                    auto originalStr = varValue.substr(1, varValue.size() - 2);
                    args.push_back(symTable.encode(originalStr));
                } else {
                    // assume no quotation marks
                    args.push_back(symTable.encode(varValue));
                }
            } else {
                args.push_back(std::stoi(varValue));
            }

            varCounter++;
        }

        // set up return and error vectors for subroutine calling
        std::vector<RamDomain> ret;

        // execute subroutine to get subproofs
        prog.executeSubroutine(relName + "_" + std::to_string(ruleNum) + "_negation_subproof", args, ret);

        // ensure the subroutine returns the correct number of results
        assert(ret.size() == atoms.size() - 1);

        // construct tree nodes
        std::stringstream joinedArgsStr;
        joinedArgsStr << join(tuple, ",");
        auto internalNode = mk<InnerNode>(
                relName + "(" + joinedArgsStr.str() + ")", "(R" + std::to_string(ruleNum) + ")");

        // store the head tuple in bodyVariables so we can print
        for (std::size_t i = 0; i < headVariables.size(); i++) {
            bodyVariables[headVariables[i]] = tuple[i];
        }

        // traverse return vector and construct child nodes
        // making sure we display existent and non-existent tuples correctly
        int literalCounter = 1;
        for (RamDomain returnCounter : ret) {
            // check what the next contained atom is
            bool atomExists = true;
            if (returnCounter == 0) {
                atomExists = false;
            }

            // get the relation of the current atom
            auto atomRepresentation = splitString(atoms[literalCounter], ',');
            std::string bodyRel = atomRepresentation[0];

            // check whether the current atom is a constraint
            bool isConstraint = contains(constraintList, bodyRel);

            // handle negated atom names
            auto bodyRelAtomName = bodyRel;
            if (bodyRel[0] == '!' && bodyRel != "!=") {
                bodyRelAtomName = bodyRel.substr(1);
            }

            // construct a label for a node containing a literal (either constraint or atom)
            std::stringstream childLabel;
            if (isConstraint) {
                // for a binary constraint, display the corresponding values and do not recurse
                assert(atomRepresentation.size() == 3 && "not a binary constraint");

                childLabel << bodyVariables[atomRepresentation[1]] << " " << bodyRel << " "
                           << bodyVariables[atomRepresentation[2]];
            } else {
                childLabel << bodyRel << "(";
                for (std::size_t i = 1; i < atomRepresentation.size(); i++) {
                    // if it's a non-variable, print either _ for unnamed, or constant value
                    if (!isVariable(atomRepresentation[i])) {
                        childLabel << atomRepresentation[i];
                    } else {
                        childLabel << bodyVariables[atomRepresentation[i]];
                    }
                    if (i < atomRepresentation.size() - 1) {
                        childLabel << ", ";
                    }
                }
                childLabel << ")";
            }

            // build a marker for existence of body atoms
            if (atomExists) {
                childLabel << " ✓";
            } else {
                childLabel << " x";
            }

            internalNode->add_child(mk<LeafNode>(childLabel.str()));
            internalNode->setSize(internalNode->getSize() + 1);

            literalCounter++;
        }

        return internalNode;
    }

    std::string getRule(std::string relName, std::size_t ruleNum) override {
        auto key = make_pair(relName, ruleNum);

        auto rule = rules.find(key);
        if (rule == rules.end()) {
            return "Rule not found";
        } else {
            return rule->second;
        }
    }

    std::vector<std::string> getRules(const std::string& relName) override {
        std::vector<std::string> relRules;
        // go through all rules
        for (auto& rule : rules) {
            if (rule.first.first == relName) {
                relRules.push_back(rule.second);
            }
        }

        return relRules;
    }

    std::string measureRelation(std::string relName) override {
        auto rel = prog.getRelation(relName);

        if (rel == nullptr) {
            return "No relation found\n";
        }

        auto size = rel->size();
        int skip = size / 10;

        if (skip == 0) {
            skip = 1;
        }

        std::stringstream ss;

        auto before_time = std::chrono::high_resolution_clock::now();

        int numTuples = 0;
        int proc = 0;
        for (auto& tuple : *rel) {
            auto tupleStart = std::chrono::high_resolution_clock::now();

            if (numTuples % skip != 0) {
                numTuples++;
                continue;
            }

            std::vector<RamDomain> currentTuple;
            for (arity_type i = 0; i < rel->getPrimaryArity(); i++) {
                RamDomain n;
                if (*rel->getAttrType(i) == 's') {
                    std::string s;
                    tuple >> s;
                    n = lookupExisting(s);
                } else if (*rel->getAttrType(i) == 'f') {
                    RamFloat element;
                    tuple >> element;
                    n = ramBitCast(element);
                } else if (*rel->getAttrType(i) == 'u') {
                    RamUnsigned element;
                    tuple >> element;
                    n = ramBitCast(element);
                } else {
                    tuple >> n;
                }

                currentTuple.push_back(n);
            }

            RamDomain ruleNum;
            tuple >> ruleNum;

            RamDomain levelNum;
            tuple >> levelNum;

            std::cout << "Tuples expanded: "
                      << explain(relName, currentTuple, ruleNum, levelNum, 10000)->getSize();

            numTuples++;
            proc++;

            auto tupleEnd = std::chrono::high_resolution_clock::now();
            auto tupleDuration =
                    std::chrono::duration_cast<std::chrono::duration<double>>(tupleEnd - tupleStart);

            std::cout << ", Time: " << tupleDuration.count() << "\n";
        }

        auto after_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::duration<double>>(after_time - before_time);

        ss << "total: " << proc << " ";
        ss << duration.count() << std::endl;

        return ss.str();
    }

    void printRulesJSON(std::ostream& os) override {
        os << "\"rules\": [\n";
        bool first = true;
        for (auto const& cur : rules) {
            if (first) {
                first = false;
            } else {
                os << ",\n";
            }
            os << "\t{ \"rule-number\": \"(R" << cur.first.second << ")\", \"rule\": \""
               << stringify(cur.second) << "\"}";
        }
        os << "\n]\n";
    }

    void queryProcess(const std::vector<std::pair<std::string, std::vector<std::string>>>& rels) override {
        std::regex varRegex("[a-zA-Z_][a-zA-Z_0-9]*", std::regex_constants::extended);
        std::regex symbolRegex("\"([^\"]*)\"", std::regex_constants::extended);
        std::regex numberRegex("[0-9]+", std::regex_constants::extended);

        std::smatch argsMatcher;

        // map for variable name and corresponding equivalence class
        std::map<std::string, Equivalence> nameToEquivalence;

        // const constraints that solution must satisfy
        ConstConstraint constConstraints;

        // relations of tuples containing variables
        std::vector<Relation*> varRels;

        // counter for adding element to varRels
        std::size_t idx = 0;

        // parse arguments in each relation Tuple
        for (const auto& rel : rels) {
            Relation* relation = prog.getRelation(rel.first);
            // number/symbol index for constant arguments in tuple
            std::vector<RamDomain> constTuple;
            // relation does not exist
            if (relation == nullptr) {
                std::cout << "Relation <" << rel.first << "> does not exist" << std::endl;
                return;
            }
            // arity error
            if (relation->getPrimaryArity() != rel.second.size()) {
                std::cout << "<" + rel.first << "> has arity of " << relation->getPrimaryArity() << std::endl;
                return;
            }

            // check if args contain variable
            bool containVar = false;
            for (std::size_t j = 0; j < rel.second.size(); ++j) {
                // arg is a variable
                if (std::regex_match(rel.second[j], argsMatcher, varRegex)) {
                    containVar = true;
                    auto nameToEquivalenceIter = nameToEquivalence.find(argsMatcher[0]);
                    // if variable has not shown up before, create an equivalence class for add it to
                    // nameToEquivalence map, otherwise add its indices to corresponding equivalence class
                    if (nameToEquivalenceIter == nameToEquivalence.end()) {
                        nameToEquivalence.insert(
                                {argsMatcher[0], Equivalence(*(relation->getAttrType(j)), argsMatcher[0],
                                                         std::make_pair(idx, j))});
                    } else {
                        nameToEquivalenceIter->second.push_back(std::make_pair(idx, j));
                    }
                    continue;
                }

                RamDomain rd;
                switch (*(relation->getAttrType(j))) {
                    case 's':
                        if (!std::regex_match(rel.second[j], argsMatcher, symbolRegex)) {
                            std::cout << argsMatcher.str(0) << " does not match type defined in relation"
                                      << std::endl;
                            return;
                        }
                        rd = prog.getSymbolTable().encode(argsMatcher[1]);
                        break;
                    case 'f':
                        if (!canBeParsedAsRamFloat(rel.second[j])) {
                            std::cout << rel.second[j] << " does not match type defined in relation"
                                      << std::endl;
                            return;
                        }
                        rd = ramBitCast(RamFloatFromString(rel.second[j]));
                        break;
                    case 'i':
                        if (!canBeParsedAsRamSigned(rel.second[j])) {
                            std::cout << rel.second[j] << " does not match type defined in relation"
                                      << std::endl;
                            return;
                        }
                        rd = ramBitCast(RamSignedFromString(rel.second[j]));
                        break;
                    case 'u':
                        if (!canBeParsedAsRamUnsigned(rel.second[j])) {
                            std::cout << rel.second[j] << " does not match type defined in relation"
                                      << std::endl;
                            return;
                        }
                        rd = ramBitCast(RamUnsignedFromString(rel.second[j]));
                        break;
                    default: continue;
                }

                constConstraints.push_back(std::make_pair(std::make_pair(idx, j), rd));
                if (!containVar) {
                    constTuple.push_back(rd);
                }
            }

            // if tuple does not contain any variable, check if existence of the tuple
            if (!containVar) {
                bool tupleExist = containsTuple(relation, constTuple);

                // if relation contains this tuple, remove all related constraints
                if (tupleExist) {
                    constConstraints.getConstraints().erase(constConstraints.getConstraints().end() -
                                                                    relation->getArity() +
                                                                    relation->getAuxiliaryArity(),
                            constConstraints.getConstraints().end());
                    // otherwise, there is no solution for given query
                } else {
                    std::cout << "false." << std::endl;
                    std::cout << "Tuple " << rel.first << "(";
                    for (std::size_t l = 0; l < rel.second.size() - 1; ++l) {
                        std::cout << rel.second[l] << ", ";
                    }
                    std::cout << rel.second.back() << ") does not exist" << std::endl;
                    return;
                }
            } else {
                varRels.push_back(relation);
                ++idx;
            }
        }

        // if varRels size is 0, all given tuples only contain constant args and exist, no variable to
        // decode, Output true and return
        if (varRels.size() == 0) {
            std::cout << "true." << std::endl;
            return;
        }

        // find solution for parameterised query
        findQuerySolution(varRels, nameToEquivalence, constConstraints);
    }

private:
    std::map<std::pair<std::string, std::size_t>, std::vector<std::string>> info;
    std::map<std::pair<std::string, std::size_t>, std::string> rules;
    std::vector<std::vector<RamDomain>> subproofs;
    std::vector<std::string> constraintList = {
            "=", "!=", "<", "<=", ">=", ">", "match", "contains", "not_match", "not_contains"};

    RamDomain lookupExisting(const std::string& symbol) {
        auto Res = symTable.findOrInsert(symbol);
        if (Res.second) {
            fatal("Error string did not exist before call to `SymbolTable::findOrInsert`: `%s`", symbol);
        }
        return Res.first;
    }

    std::tuple<int, int> findTuple(const std::string& relName, std::vector<RamDomain> tup) {
        auto rel = prog.getRelation(relName);

        if (rel == nullptr) {
            return std::make_tuple(-1, -1);
        }

        // find correct tuple
        for (auto& tuple : *rel) {
            bool match = true;
            std::vector<RamDomain> currentTuple;

            for (arity_type i = 0; i < rel->getPrimaryArity(); i++) {
                RamDomain n;
                if (*rel->getAttrType(i) == 's') {
                    std::string s;
                    tuple >> s;
                    n = lookupExisting(s);
                } else if (*rel->getAttrType(i) == 'f') {
                    RamFloat element;
                    tuple >> element;
                    n = ramBitCast(element);
                } else if (*rel->getAttrType(i) == 'u') {
                    RamUnsigned element;
                    tuple >> element;
                    n = ramBitCast(element);
                } else {
                    tuple >> n;
                }

                currentTuple.push_back(n);

                if (n != tup[i]) {
                    match = false;
                    break;
                }
            }

            if (match) {
                RamDomain ruleNum;
                tuple >> ruleNum;

                RamDomain levelNum;
                tuple >> levelNum;

                return std::make_tuple(ruleNum, levelNum);
            }
        }

        // if no tuple exists
        return std::make_tuple(-1, -1);
    }

    /*
     * Find solution for parameterised query satisfying constant constraints and equivalence constraints
     * @param varRels, reference to vector of relation of tuple contains at least one variable in its
     * arguments
     * @param nameToEquivalence, reference to variable name and corresponding equivalence class
     * @param constConstraints, reference to const constraints must be satisfied
     * */
    void findQuerySolution(const std::vector<Relation*>& varRels,
            const std::map<std::string, Equivalence>& nameToEquivalence,
            const ConstConstraint& constConstraints) {
        // vector of iterators for relations in varRels
        std::vector<Relation::iterator> varRelationIterators;
        for (auto relation : varRels) {
            varRelationIterators.push_back(relation->begin());
        }

        std::size_t solutionCount = 0;
        std::stringstream solution;

        // iterate through the vector of iterators to find solution
        while (true) {
            bool isSolution = true;

            // vector contains the tuples the iterators currently points to
            std::vector<tuple> element;
            for (auto it : varRelationIterators) {
                element.push_back(*it);
            }
            // check if tuple satisfies variable equivalence
            for (auto var : nameToEquivalence) {
                if (!var.second.verify(element)) {
                    isSolution = false;
                    break;
                }
            }
            if (isSolution) {
                // check if tuple satisfies constant constraints
                isSolution = constConstraints.verify(element);
            }

            if (isSolution) {
                // print previous solution (if any)
                if (solutionCount != 0) {
                    std::cout << solution.str() << std::endl;
                }
                solution.str(std::string());  // reset solution and process

                std::size_t c = 0;
                for (auto&& var : nameToEquivalence) {
                    auto idx = var.second.getFirstIdx();
                    auto raw = element[idx.first][idx.second];

                    solution << var.second.getSymbol() << " = ";
                    switch (var.second.getType()) {
                        case 'i': solution << ramBitCast<RamSigned>(raw); break;
                        case 'f': solution << ramBitCast<RamFloat>(raw); break;
                        case 'u': solution << ramBitCast<RamUnsigned>(raw); break;
                        case 's': solution << prog.getSymbolTable().decode(raw); break;
                        default: fatal("invalid type: `%c`", var.second.getType());
                    }

                    if (++c < nameToEquivalence.size()) {
                        solution << ", ";
                    }
                }

                solutionCount++;
                // query has more than one solution; query whether to find next solution or stop
                if (1 < solutionCount) {
                    for (std::string input; getline(std::cin, input);) {
                        if (input == ";") break;   // print next solution?
                        if (input == ".") return;  // break from query?

                        std::cout << "use ; to find next solution, use . to break from current query\n";
                    }
                }
            }

            // increment the iterators
            std::size_t i = varRels.size() - 1;
            bool terminate = true;
            for (auto it = varRelationIterators.rbegin(); it != varRelationIterators.rend(); ++it) {
                if ((++(*it)) != varRels[i]->end()) {
                    terminate = false;
                    break;
                } else {
                    (*it) = varRels[i]->begin();
                    --i;
                }
            }

            if (terminate) {
                // if there is no solution, output false
                if (solutionCount == 0) {
                    std::cout << "false." << std::endl;
                    // otherwise print the last solution
                } else {
                    std::cout << solution.str() << "." << std::endl;
                }
                break;
            }
        }
    }

    // check if constTuple exists in relation
    bool containsTuple(Relation* relation, const std::vector<RamDomain>& constTuple) {
        bool tupleExist = false;
        for (auto it = relation->begin(); it != relation->end(); ++it) {
            bool eq = true;
            for (std::size_t j = 0; j < constTuple.size(); ++j) {
                if (constTuple[j] != (*it)[j]) {
                    eq = false;
                    break;
                }
            }
            if (eq) {
                tupleExist = true;
                break;
            }
        }
        return tupleExist;
    }
};

}  // end of namespace souffle
