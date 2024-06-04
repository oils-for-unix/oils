/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/Cell.h"
#include "souffle/profile/CellInterface.h"
#include "souffle/profile/Iteration.h"
#include "souffle/profile/ProgramRun.h"
#include "souffle/profile/Relation.h"
#include "souffle/profile/Row.h"
#include "souffle/profile/Rule.h"
#include "souffle/profile/Table.h"
#include <chrono>
#include <memory>
#include <ratio>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace souffle {
namespace profile {

/*
 * Class to format profiler data structures into tables
 */
class OutputProcessor {
private:
    std::shared_ptr<ProgramRun> programRun;

public:
    OutputProcessor() {
        programRun = std::make_shared<ProgramRun>(ProgramRun());
    }

    const std::shared_ptr<ProgramRun>& getProgramRun() const {
        return programRun;
    }

    Table getRelTable() const;

    Table getRulTable() const;

    Table getSubrulTable(std::string strRel, std::string strRul) const;

    Table getAtomTable(std::string strRel, std::string strRul) const;

    Table getVersions(std::string strRel, std::string strRul) const;

    Table getVersionAtoms(std::string strRel, std::string strRul, int version) const;
};

/*
 * rel table :
 * ROW[0] = TOT_T
 * ROW[1] = NREC_T
 * ROW[2] = REC_T
 * ROW[3] = COPY_T
 * ROW[4] = TUPLES
 * ROW[5] = REL NAME
 * ROW[6] = ID
 * ROW[7] = SRC
 * ROW[8] = PERFOR
 * ROW[9] = LOADTIME
 * ROW[10] = SAVETIME
 * ROW[11] = MAXRSSDIFF
 * ROW[12] = READS
 *
 */
Table inline OutputProcessor::getRelTable() const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();
    Table table;
    for (auto& rel : relationMap) {
        std::shared_ptr<Relation> r = rel.second;
        Row row(13);
        auto total_time = r->getNonRecTime() + r->getRecTime() + r->getCopyTime();
        row[0] = std::make_shared<Cell<std::chrono::microseconds>>(total_time);
        row[1] = std::make_shared<Cell<std::chrono::microseconds>>(r->getNonRecTime());
        row[2] = std::make_shared<Cell<std::chrono::microseconds>>(r->getRecTime());
        row[3] = std::make_shared<Cell<std::chrono::microseconds>>(r->getCopyTime());
        row[4] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(r->size()));
        row[5] = std::make_shared<Cell<std::string>>(r->getName());
        row[6] = std::make_shared<Cell<std::string>>(r->getId());
        row[7] = std::make_shared<Cell<std::string>>(r->getLocator());
        if (total_time.count() != 0) {
            row[8] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(
                    static_cast<double>(r->size()) / (static_cast<double>(total_time.count()) / 1000000.0)));
        } else {
            row[8] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(r->size()));
        }
        row[9] = std::make_shared<Cell<std::chrono::microseconds>>(r->getLoadtime());
        row[10] = std::make_shared<Cell<std::chrono::microseconds>>(r->getSavetime());
        row[11] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(r->getMaxRSSDiff()));
        row[12] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(r->getReads()));

        table.addRow(std::make_shared<Row>(row));
    }
    return table;
}
/*
 * rul table :
 * ROW[0] = TOT_T
 * ROW[1] = NREC_T
 * ROW[2] = REC_T
 * ROW[3] = COPY_T
 * ROW[4] = TUPLES
 * ROW[5] = RUL NAME
 * ROW[6] = ID
 * ROW[7] = SRC
 * ROW[8] = PERFOR
 * ROW[9] = VER
 * ROW[10]= REL_NAME
 */
Table inline OutputProcessor::getRulTable() const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();
    std::unordered_map<std::string, std::shared_ptr<Row>> ruleMap;

    for (auto& rel : relationMap) {
        for (auto& current : rel.second->getRuleMap()) {
            Row row(11);
            std::shared_ptr<Rule> rule = current.second;
            row[0] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
            row[1] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
            row[2] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
            row[3] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
            row[4] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(rule->size()));
            row[5] = std::make_shared<Cell<std::string>>(rule->getName());
            row[6] = std::make_shared<Cell<std::string>>(rule->getId());
            row[7] = std::make_shared<Cell<std::string>>(rel.second->getName());
            row[8] = std::make_shared<Cell<int64_t>>(0);
            row[10] = std::make_shared<Cell<std::string>>(rule->getLocator());
            ruleMap.emplace(rule->getName(), std::make_shared<Row>(row));
        }
        for (auto& iter : rel.second->getIterations()) {
            for (auto& current : iter->getRules()) {
                std::shared_ptr<Rule> rule = current.second;
                if (ruleMap.find(rule->getName()) != ruleMap.end()) {
                    Row row = *ruleMap[rule->getName()];
                    row[2] = std::make_shared<Cell<std::chrono::microseconds>>(
                            row[2]->getTimeVal() + rule->getRuntime());
                    row[4] = std::make_shared<Cell<int64_t>>(
                            row[4]->getLongVal() + static_cast<int64_t>(rule->size()));
                    row[0] = std::make_shared<Cell<std::chrono::microseconds>>(
                            row[0]->getTimeVal() + rule->getRuntime());
                    ruleMap[rule->getName()] = std::make_shared<Row>(row);
                } else {
                    Row row(11);
                    row[0] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
                    row[1] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
                    row[2] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
                    row[3] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
                    row[4] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(rule->size()));
                    row[5] = std::make_shared<Cell<std::string>>(rule->getName());
                    row[6] = std::make_shared<Cell<std::string>>(rule->getId());
                    row[7] = std::make_shared<Cell<std::string>>(rel.second->getName());
                    row[8] = std::make_shared<Cell<int64_t>>(rule->getVersion());
                    row[10] = std::make_shared<Cell<std::string>>(rule->getLocator());
                    ruleMap[rule->getName()] = std::make_shared<Row>(row);
                }
            }
        }
        for (auto& current : ruleMap) {
            std::shared_ptr<Row> row = current.second;
            Row t = *row;
            std::chrono::microseconds val = t[1]->getTimeVal() + t[2]->getTimeVal() + t[3]->getTimeVal();

            t[0] = std::make_shared<Cell<std::chrono::microseconds>>(val);

            if (t[0]->getTimeVal().count() != 0) {
                t[9] = std::make_shared<Cell<double>>(t[4]->getLongVal() / (t[0]->getDoubleVal() * 1000));
            } else {
                t[9] = std::make_shared<Cell<double>>(t[4]->getLongVal() / 1.0);
            }
            current.second = std::make_shared<Row>(t);
        }
    }

    Table table;
    for (auto& current : ruleMap) {
        table.addRow(current.second);
    }
    return table;
}

/*
 * atom table :
 * ROW[0] = clause
 * ROW[1] = atom
 * ROW[2] = level
 * ROW[3] = frequency
 */
Table inline OutputProcessor::getAtomTable(std::string strRel, std::string strRul) const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();

    Table table;
    for (auto& current : relationMap) {
        std::shared_ptr<Relation> rel = current.second;

        if (rel->getId() != strRel) {
            continue;
        }

        for (auto& current : rel->getRuleMap()) {
            std::shared_ptr<Rule> rule = current.second;
            if (rule->getId() != strRul) {
                continue;
            }
            for (auto& atom : rule->getAtoms()) {
                Row row(4);
                row[0] = std::make_shared<Cell<std::string>>(atom.rule);
                row[1] = std::make_shared<Cell<std::string>>(atom.identifier);
                row[2] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(atom.level));
                row[3] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(atom.frequency));

                table.addRow(std::make_shared<Row>(row));
            }
        }
    }
    return table;
}

/*
 * subrule table :
 * ROW[0] = subrule
 */
Table inline OutputProcessor::getSubrulTable(std::string strRel, std::string strRul) const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();

    Table table;
    for (auto& current : relationMap) {
        std::shared_ptr<Relation> rel = current.second;

        if (rel->getId() != strRel) {
            continue;
        }

        for (auto& current : rel->getRuleMap()) {
            std::shared_ptr<Rule> rule = current.second;
            if (rule->getId() != strRul) {
                continue;
            }
            for (auto& atom : rule->getAtoms()) {
                Row row(1);
                row[0] = std::make_shared<Cell<std::string>>(atom.rule);

                table.addRow(std::make_shared<Row>(row));
            }
        }
    }
    return table;
}

/*
 * ver table :
 * ROW[0] = TOT_T
 * ROW[1] = NREC_T
 * ROW[2] = REC_T
 * ROW[3] = COPY_T
 * ROW[4] = TUPLES
 * ROW[5] = RUL NAME
 * ROW[6] = ID
 * ROW[7] = SRC
 * ROW[8] = PERFOR
 * ROW[9] = VER
 * ROW[10]= REL_NAME
 */
Table inline OutputProcessor::getVersions(std::string strRel, std::string strRul) const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();
    Table table;

    std::shared_ptr<Relation> rel;
    for (auto& current : relationMap) {
        if (current.second->getId() == strRel) {
            rel = current.second;
            break;
        }
    }
    if (rel == nullptr) {
        return table;
    }

    std::unordered_map<std::string, std::shared_ptr<Row>> ruleMap;
    for (auto& iter : rel->getIterations()) {
        for (auto& current : iter->getRules()) {
            std::shared_ptr<Rule> rule = current.second;
            if (rule->getId() == strRul) {
                std::string strTemp =
                        rule->getName() + rule->getLocator() + std::to_string(rule->getVersion());

                if (ruleMap.find(strTemp) != ruleMap.end()) {
                    Row row = *ruleMap[strTemp];
                    row[2] = std::make_shared<Cell<std::chrono::microseconds>>(
                            row[2]->getTimeVal() + rule->getRuntime());
                    row[4] = std::make_shared<Cell<int64_t>>(
                            row[4]->getLongVal() + static_cast<int64_t>(rule->size()));
                    row[0] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
                    ruleMap[strTemp] = std::make_shared<Row>(row);
                } else {
                    Row row(10);
                    row[1] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
                    row[2] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
                    row[3] = std::make_shared<Cell<std::chrono::microseconds>>(std::chrono::microseconds(0));
                    row[4] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(rule->size()));
                    row[5] = std::make_shared<Cell<std::string>>(rule->getName());
                    row[6] = std::make_shared<Cell<std::string>>(rule->getId());
                    row[7] = std::make_shared<Cell<std::string>>(rel->getName());
                    row[8] = std::make_shared<Cell<int64_t>>(rule->getVersion());
                    row[9] = std::make_shared<Cell<std::string>>(rule->getLocator());
                    row[0] = std::make_shared<Cell<std::chrono::microseconds>>(rule->getRuntime());
                    ruleMap[strTemp] = std::make_shared<Row>(row);
                }
            }
        }
    }

    for (auto row : ruleMap) {
        Row t = *row.second;
        t[0] = std::make_shared<Cell<std::chrono::microseconds>>(
                t[1]->getTimeVal() + t[2]->getTimeVal() + t[3]->getTimeVal());
        ruleMap[row.first] = std::make_shared<Row>(t);
    }

    for (auto& current : ruleMap) {
        table.addRow(current.second);
    }
    return table;
}

/*
 * atom table :
 * ROW[0] = rule
 * ROW[1] = atom
 * ROW[2] = level
 * ROW[3] = frequency
 */
Table inline OutputProcessor::getVersionAtoms(std::string strRel, std::string srcLocator, int version) const {
    const std::unordered_map<std::string, std::shared_ptr<Relation>>& relationMap =
            programRun->getRelationMap();
    Table table;
    std::shared_ptr<Relation> rel;

    for (auto& current : relationMap) {
        if (current.second->getId() == strRel) {
            rel = current.second;
            break;
        }
    }
    if (rel == nullptr) {
        return table;
    }

    for (auto& iter : rel->getIterations()) {
        for (auto& current : iter->getRules()) {
            std::shared_ptr<Rule> rule = current.second;
            if (rule->getLocator() == srcLocator && rule->getVersion() == version) {
                for (auto& atom : rule->getAtoms()) {
                    Row row(4);
                    row[0] = std::make_shared<Cell<std::string>>(atom.rule);
                    row[1] = std::make_shared<Cell<std::string>>(atom.identifier);
                    row[2] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(atom.level));
                    row[3] = std::make_shared<Cell<int64_t>>(static_cast<int64_t>(atom.frequency));
                    table.addRow(std::make_shared<Row>(row));
                }
            }
        }
    }

    return table;
}

}  // namespace profile
}  // namespace souffle
