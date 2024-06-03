/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/Iteration.h"
#include "souffle/profile/ProfileDatabase.h"
#include "souffle/profile/ProfileEvent.h"
#include "souffle/profile/ProgramRun.h"
#include "souffle/profile/Relation.h"
#include "souffle/profile/Rule.h"
#include "souffle/profile/StringUtils.h"
#include <cassert>
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>
#ifndef _MSC_VER
#include <dirent.h>
#endif
#include <sys/stat.h>

namespace souffle {
namespace profile {

namespace {
template <typename T>
class DSNVisitor : public Visitor {
public:
    DSNVisitor(T& base) : base(base) {}
    void visit(TextEntry& text) override {
        if (text.getKey() == "source-locator") {
            base.setLocator(text.getText());
        }
    }
    void visit(DurationEntry& duration) override {
        if (duration.getKey() == "runtime") {
            base.setStarttime(duration.getStart());
            base.setEndtime(duration.getEnd());
        }
    }
    void visit(SizeEntry& size) override {
        if (size.getKey() == "num-tuples") {
            base.setNumTuples(size.getSize());
        }
    }
    void visit(DirectoryEntry& /* ruleEntry */) override {}

protected:
    T& base;
};

/**
 * Visit ProfileDB atom frequencies.
 * atomrule : {atom: {num-tuples: num}}
 */
class AtomFrequenciesVisitor : public Visitor {
public:
    AtomFrequenciesVisitor(Rule& rule) : rule(rule) {}
    void visit(DirectoryEntry& directory) override {
        const std::string& clause = directory.getKey();

        for (auto& key : directory.getKeys()) {
            auto* level = as<SizeEntry>(directory.readDirectoryEntry(key)->readEntry("level"));
            auto* frequency = as<SizeEntry>(directory.readDirectoryEntry(key)->readEntry("num-tuples"));
            // Handle older logs
            std::size_t intFreq = frequency == nullptr ? 0 : frequency->getSize();
            std::size_t intLevel = level == nullptr ? 0 : level->getSize();
            rule.addAtomFrequency(clause, key, intLevel, intFreq);
        }
    }

private:
    Rule& rule;
};

/**
 * Visit ProfileDB recursive rule.
 * ruleversion: {DSN}
 */
class RecursiveRuleVisitor : public DSNVisitor<Rule> {
public:
    RecursiveRuleVisitor(Rule& rule) : DSNVisitor(rule) {}
    void visit(DirectoryEntry& directory) override {
        if (directory.getKey() == "atom-frequency") {
            AtomFrequenciesVisitor atomFrequenciesVisitor(base);
            for (auto& key : directory.getKeys()) {
                directory.readDirectoryEntry(key)->accept(atomFrequenciesVisitor);
            }
        }
    }
};

/**
 * Visit ProfileDB non-recursive rules.
 * rule: {versionNum : {DSN}, versionNum+1: {DSN}}
 */
class RecursiveRulesVisitor : public Visitor {
public:
    RecursiveRulesVisitor(Iteration& iteration, Relation& relation)
            : iteration(iteration), relation(relation) {}
    void visit(DirectoryEntry& ruleEntry) override {
        for (const auto& key : ruleEntry.getKeys()) {
            auto& versions = *ruleEntry.readDirectoryEntry(key);
            auto rule = std::make_shared<Rule>(
                    ruleEntry.getKey(), std::stoi(key), relation.createRecID(ruleEntry.getKey()));
            RecursiveRuleVisitor visitor(*rule);
            for (const auto& versionKey : versions.getKeys()) {
                versions.readEntry(versionKey)->accept(visitor);
            }
            // To match map keys defined in Iteration::addRule()
            std::string ruleKey = key + rule->getLocator() + key;
            iteration.addRule(ruleKey, rule);
        }
    }

protected:
    Iteration& iteration;
    Relation& relation;
};

/**
 * Visit ProfileDB non-recursive rule.
 * rule: {DSN}
 */
class NonRecursiveRuleVisitor : public DSNVisitor<Rule> {
public:
    NonRecursiveRuleVisitor(Rule& rule) : DSNVisitor(rule) {}
    void visit(DirectoryEntry& directory) override {
        if (directory.getKey() == "atom-frequency") {
            AtomFrequenciesVisitor atomFrequenciesVisitor(base);
            for (auto& key : directory.getKeys()) {
                directory.readDirectoryEntry(key)->accept(atomFrequenciesVisitor);
            }
        }
    }
};

/**
 * Visit ProfileDB non-recursive rules.
 * non-recursive-rule: {rule1: {DSN}, ...}
 */
class NonRecursiveRulesVisitor : public Visitor {
public:
    NonRecursiveRulesVisitor(Relation& relation) : relation(relation) {}
    void visit(DirectoryEntry& ruleEntry) override {
        auto rule = std::make_shared<Rule>(ruleEntry.getKey(), relation.createID());
        NonRecursiveRuleVisitor visitor(*rule);
        for (const auto& key : ruleEntry.getKeys()) {
            ruleEntry.readEntry(key)->accept(visitor);
        }
        relation.addRule(rule);
    }

protected:
    Relation& relation;
};

/**
 * Visit a ProfileDB relation iteration.
 * iterationNumber: {DSN, recursive-rule: {}}
 */
class IterationVisitor : public DSNVisitor<Iteration> {
public:
    IterationVisitor(Iteration& iteration, Relation& relation) : DSNVisitor(iteration), relation(relation) {}
    void visit(DurationEntry& duration) override {
        if (duration.getKey() == "copytime") {
            auto copytime = (duration.getEnd() - duration.getStart());
            base.setCopytime(copytime);
        }
        DSNVisitor::visit(duration);
    }
    void visit(DirectoryEntry& directory) override {
        if (directory.getKey() == "recursive-rule") {
            RecursiveRulesVisitor rulesVisitor(base, relation);
            for (const auto& key : directory.getKeys()) {
                directory.readEntry(key)->accept(rulesVisitor);
            }
        }
        if (directory.getKey() == "maxRSS") {
            auto* preMaxRSS = as<SizeEntry>(directory.readEntry("pre"));
            auto* postMaxRSS = as<SizeEntry>(directory.readEntry("post"));
            relation.setPreMaxRSS(preMaxRSS->getSize());
            relation.setPostMaxRSS(postMaxRSS->getSize());
        }
    }

protected:
    Relation& relation;
};

/**
 * Visit ProfileDB iterations.
 * iteration: {num: {}, num2: {}, ...}
 */
class IterationsVisitor : public Visitor {
public:
    IterationsVisitor(Relation& relation) : relation(relation) {}
    void visit(DirectoryEntry& ruleEntry) override {
        auto iteration = std::make_shared<Iteration>();
        relation.addIteration(iteration);
        IterationVisitor visitor(*iteration, relation);
        for (const auto& key : ruleEntry.getKeys()) {
            ruleEntry.readEntry(key)->accept(visitor);
        }
    }

protected:
    Relation& relation;
};

/**
 * Visit ProfileDB relations.
 * relname: {DSN, non-recursive-rule: {}, iteration: {...}}
 */
class RelationVisitor : public DSNVisitor<Relation> {
public:
    RelationVisitor(Relation& relation) : DSNVisitor(relation) {}
    void visit(DurationEntry& duration) override {
        if (duration.getKey() == "loadtime") {
            base.setLoadtime(duration.getStart(), duration.getEnd());
        } else if (duration.getKey() == "savetime") {
            auto savetime = (duration.getEnd() - duration.getStart());
            base.setSavetime(savetime);
        }
        DSNVisitor::visit(duration);
    }
    void visit(DirectoryEntry& directory) override {
        if (directory.getKey() == "iteration") {
            IterationsVisitor iterationsVisitor(base);
            for (const auto& key : directory.getKeys()) {
                directory.readEntry(key)->accept(iterationsVisitor);
            }
        } else if (directory.getKey() == "non-recursive-rule") {
            NonRecursiveRulesVisitor rulesVisitor(base);
            for (const auto& key : directory.getKeys()) {
                directory.readEntry(key)->accept(rulesVisitor);
            }
        } else if (directory.getKey() == "maxRSS") {
            auto* preMaxRSS = as<SizeEntry>(directory.readEntry("pre"));
            auto* postMaxRSS = as<SizeEntry>(directory.readEntry("post"));
            base.setPreMaxRSS(preMaxRSS->getSize());
            base.setPostMaxRSS(postMaxRSS->getSize());
        }
    }
    void visit(SizeEntry& size) override {
        if (size.getKey() == "reads") {
            base.addReads(size.getSize());
        } else {
            DSNVisitor::visit(size);
        }
    }
};
}  // namespace

/*
 * Input reader and processor for log files
 */
class Reader {
private:
    std::string file_loc;
    std::streampos gpos;
    const ProfileDatabase& db = ProfileEventSingleton::instance().getDB();
    bool loaded = false;
    bool online{true};

    std::unordered_map<std::string, std::shared_ptr<Relation>> relationMap{};
    std::unordered_map<std::string, std::unordered_map<std::string, double>> countRecursiveJoinSizeMap{};
    std::unordered_map<std::string, double> countNonRecursiveJoinSizeMap{};
    int rel_id{0};

public:
    std::shared_ptr<ProgramRun> run;

    Reader(std::string filename, std::shared_ptr<ProgramRun> run)
            : file_loc(std::move(filename)), run(std::move(run)) {
        try {
            ProfileEventSingleton::instance().setDBFromFile(file_loc);
        } catch (const std::exception& e) {
            fatal("exception whilst reading profile DB: %s", e.what());
        }
    }

    Reader(std::shared_ptr<ProgramRun> run) : run(std::move(run)) {}
    /**
     * Read the contents from file into the class
     */
    void processFile() {
        rel_id = 0;
        relationMap.clear();
        auto programDuration = as<DurationEntry>(db.lookupEntry({"program", "runtime"}));
        if (programDuration == nullptr) {
            auto startTimeEntry = as<TimeEntry>(db.lookupEntry({"program", "starttime"}));
            if (startTimeEntry != nullptr) {
                run->setStarttime(startTimeEntry->getTime());
                run->setEndtime(std::chrono::duration_cast<microseconds>(now().time_since_epoch()));
                loaded = true;
            }
        } else {
            run->setStarttime(programDuration->getStart());
            run->setEndtime(programDuration->getEnd());
            online = false;
        }

        auto prefix = as<DirectoryEntry>(db.lookupEntry({"program", "statistics", "relation"}));
        if (prefix != nullptr) {
            for (const auto& rel : prefix->getKeys()) {
                auto prefixWithRel = as<DirectoryEntry>(
                        db.lookupEntry({"program", "statistics", "relation", rel, "attributes"}));
                if (prefixWithRel != nullptr) {
                    for (const auto& attributes : prefixWithRel->getKeys()) {
                        auto prefixWithAttributes = as<DirectoryEntry>(db.lookupEntry({"program",
                                "statistics", "relation", rel, "attributes", attributes, "constants"}));
                        if (prefixWithAttributes == nullptr) {
                            continue;
                        }
                        for (const auto& constants : prefixWithAttributes->getKeys()) {
                            auto fullKey = as<TextEntry>(db.lookupEntry({"program", "statistics", "relation",
                                    rel, "attributes", attributes, "constants", constants}));
                            if (fullKey != nullptr) {
                                double joinSize = std::stod(fullKey->getText());
                                std::string key = rel + " " + attributes + " " + constants;
                                countNonRecursiveJoinSizeMap[key] = joinSize;
                            }
                        }
                    }
                }

                auto prefixWithRecursiveRel = as<DirectoryEntry>(
                        db.lookupEntry({"program", "statistics", "relation", rel, "iteration"}));
                if (prefixWithRecursiveRel != nullptr) {
                    for (const auto& iteration : prefixWithRecursiveRel->getKeys()) {
                        auto prefixWithIteration = as<DirectoryEntry>(db.lookupEntry({"program", "statistics",
                                "relation", rel, "iteration", iteration, "attributes"}));
                        if (prefixWithIteration == nullptr) {
                            continue;
                        }

                        for (const auto& attributes : prefixWithIteration->getKeys()) {
                            auto prefixWithAttributes = as<DirectoryEntry>(
                                    db.lookupEntry({"program", "statistics", "relation", rel, "iteration",
                                            iteration, "attributes", attributes, "constants"}));
                            if (prefixWithAttributes == nullptr) {
                                continue;
                            }
                            for (const auto& constants : prefixWithAttributes->getKeys()) {
                                auto fullKey = as<TextEntry>(db.lookupEntry(
                                        {"program", "statistics", "relation", rel, "iteration", iteration,
                                                "attributes", attributes, "constants", constants}));
                                double joinSize = std::stod(fullKey->getText());
                                if (fullKey != nullptr) {
                                    std::string key = rel + " " + attributes + " " + constants;
                                    countRecursiveJoinSizeMap[key][iteration] = joinSize;
                                }
                            }
                        }
                    }
                }
            }
        }

        auto relations = as<DirectoryEntry>(db.lookupEntry({"program", "relation"}));
        if (relations == nullptr) {
            // Souffle hasn't generated any profiling information yet
            // or program is empty.
            return;
        }
        for (const auto& cur : relations->getKeys()) {
            auto relation = as<DirectoryEntry>(db.lookupEntry({"program", "relation", cur}));
            if (relation != nullptr) {
                addRelation(*relation);
            }
        }
        for (const auto& relation : relationMap) {
            for (const auto& rule : relation.second->getRuleMap()) {
                for (const auto& atom : rule.second->getAtoms()) {
                    std::string relationName = extractRelationNameFromAtom(atom);
                    relationMap[relationName]->addReads(atom.frequency);
                }
            }
            for (const auto& iteration : relation.second->getIterations()) {
                for (const auto& rule : iteration->getRules()) {
                    for (const auto& atom : rule.second->getAtoms()) {
                        std::string relationName = extractRelationNameFromAtom(atom);
                        if (relationName.substr(0, 6) == "@delta") {
                            relationName = relationName.substr(7);
                        }
                        if (relationName.substr(0, 4) == "@new") {
                            relationName = relationName.substr(5);
                        }
                        assert(relationMap.count(relationName) > 0 || "Relation name for atom not found");
                        relationMap[relationName]->addReads(atom.frequency);
                    }
                }
            }
        }
        run->setRelationMap(this->relationMap);
        loaded = true;
    }

    void save(std::string f_name);

    inline bool isLive() {
        return online;
    }

    bool hasAutoSchedulerStats() {
        return !countNonRecursiveJoinSizeMap.empty() || !countRecursiveJoinSizeMap.empty();
    }

    double getNonRecursiveEstimateJoinSize(
            const std::string& rel, const std::string& attributes, const std::string& constants) {
        auto key = rel + " " + attributes + " " + constants;
        return countNonRecursiveJoinSizeMap.at(key);
    }

    std::size_t getIterations(const std::string& rel) {
        for (auto& [key, m] : countRecursiveJoinSizeMap) {
            std::string token = key.substr(0, key.find(" "));
            if (token == rel) {
                return m.size();
            }
        }
        assert(false);
        return 0;
    }

    double getRecursiveEstimateJoinSize(const std::string& rel, const std::string& attributes,
            const std::string& constants, const std::string& iteration) {
        auto key = rel + " " + attributes + " " + constants;
        auto& m = countRecursiveJoinSizeMap.at(key);
        return m.at(iteration);
    }

    void addRelation(const DirectoryEntry& relation) {
        const std::string& name = cleanRelationName(relation.getKey());

        relationMap.emplace(name, std::make_shared<Relation>(name, createId()));
        auto& rel = *relationMap[name];
        RelationVisitor relationVisitor(rel);

        for (const auto& key : relation.getKeys()) {
            relation.readEntry(key)->accept(relationVisitor);
        }
    }

    inline bool isLoaded() {
        return loaded;
    }

    std::string RelationcreateId() {
        return "R" + std::to_string(++rel_id);
    }

    std::string createId() {
        return "R" + std::to_string(++rel_id);
    }

protected:
    std::string cleanRelationName(const std::string& relationName) {
        std::string cleanName = relationName;
        for (auto& cur : cleanName) {
            if (cur == '-') {
                cur = '.';
            }
        }
        return cleanName;
    }
    std::string extractRelationNameFromAtom(const Atom& atom) {
        return cleanRelationName(atom.identifier.substr(0, atom.identifier.find('(')));
    }
};

}  // namespace profile
}  // namespace souffle
