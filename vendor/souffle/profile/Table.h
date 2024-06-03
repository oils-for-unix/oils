/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/DataComparator.h"
#include "souffle/profile/Row.h"
#include <algorithm>
#include <memory>
#include <vector>

namespace souffle {
namespace profile {

/*
 * Table class for holding a vector of rows
 * And sorting the rows based on a datacomparator function
 */
class Table {
public:
    std::vector<std::shared_ptr<Row>> rows;

    Table() : rows() {}

    void addRow(std::shared_ptr<Row> row) {
        rows.push_back(row);
    }

    inline std::vector<std::shared_ptr<Row>> getRows() {
        return rows;
    }

    void sort(int col_num) {
        switch (col_num) {
            case 1: std::sort(rows.begin(), rows.end(), DataComparator::NR_T); break;
            case 2: std::sort(rows.begin(), rows.end(), DataComparator::R_T); break;
            case 3: std::sort(rows.begin(), rows.end(), DataComparator::C_T); break;
            case 4: std::sort(rows.begin(), rows.end(), DataComparator::TUP); break;
            case 5: std::sort(rows.begin(), rows.end(), DataComparator::ID); break;
            case 6: std::sort(rows.begin(), rows.end(), DataComparator::NAME); break;
            case 0:
            default:  // if the col_num isn't defined use TIME
                std::sort(rows.begin(), rows.end(), DataComparator::TIME);
                break;
        }
    }
};

}  // namespace profile
}  // namespace souffle
