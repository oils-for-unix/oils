/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/CellInterface.h"

#include <memory>
#include <vector>

namespace souffle {
namespace profile {

/*
 * Row class for Tables, holds a vector of cells.
 */
class Row {
public:
    std::vector<std::shared_ptr<CellInterface>> cells;

    Row(unsigned long size) : cells() {
        for (unsigned long i = 0; i < size; i++) {
            cells.emplace_back(std::shared_ptr<CellInterface>(nullptr));
        }
    }

    std::shared_ptr<CellInterface>& operator[](unsigned long i) {
        return cells.at(i);
    }

    //    void addCell(int location, std::shared_ptr<CellInterface> cell) {
    //        cells[location] = cell;
    //    }

    inline std::vector<std::shared_ptr<CellInterface>> getCells() {
        return cells;
    }
};

}  // namespace profile
}  // namespace souffle
