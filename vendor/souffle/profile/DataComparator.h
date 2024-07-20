/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/CellInterface.h"
#include "souffle/profile/Row.h"

#include <cmath>
#include <memory>
#include <vector>

namespace souffle {
namespace profile {

/*
 * Data comparison functions for sorting tables
 *
 * Will sort the values of only one column, in descending order
 *
 */
class DataComparator {
public:
    /** Sort by total time. */
    static bool TIME(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return a->cells[0]->getDoubleVal() > b->cells[0]->getDoubleVal();
    }

    /** Sort by non-recursive time. */
    static bool NR_T(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return a->cells[1]->getDoubleVal() > b->cells[1]->getDoubleVal();
    }

    /** Sort by recursive time. */
    static bool R_T(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return a->cells[2]->getDoubleVal() > b->cells[2]->getDoubleVal();
    }

    /** Sort by copy time. */
    static bool C_T(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return a->cells[3]->getDoubleVal() > b->cells[3]->getDoubleVal();
    }

    /** Sort by tuple count. */
    static bool TUP(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return b->cells[4]->getLongVal() < a->cells[4]->getLongVal();
    }

    /** Sort by name. */
    static bool NAME(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return b->cells[5]->getStringVal() > a->cells[5]->getStringVal();
    }

    /** Sort by ID. */
    static bool ID(const std::shared_ptr<Row>& a, const std::shared_ptr<Row>& b) {
        return b->cells[6]->getStringVal() > a->cells[6]->getStringVal();
    }
};

}  // namespace profile
}  // namespace souffle
