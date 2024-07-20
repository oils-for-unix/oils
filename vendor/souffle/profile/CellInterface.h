/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include <chrono>
#include <string>

namespace souffle {
namespace profile {

class CellInterface {
public:
    virtual std::string toString(int precision) const = 0;

    virtual double getDoubleVal() const = 0;

    virtual int64_t getLongVal() const = 0;

    virtual std::string getStringVal() const = 0;

    virtual std::chrono::microseconds getTimeVal() const = 0;

    virtual ~CellInterface() = default;
};

}  // namespace profile
}  // namespace souffle
