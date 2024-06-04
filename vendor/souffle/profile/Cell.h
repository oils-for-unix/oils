/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/CellInterface.h"
#include "souffle/profile/StringUtils.h"

#include <chrono>
#include <iostream>
#include <string>
#include <utility>

namespace souffle {
namespace profile {

template <typename T>
class Cell : public CellInterface {
    const T value;

public:
    Cell(T value) : value(value){};
    ~Cell() override = default;
};

template <>
class Cell<std::chrono::microseconds> : public CellInterface {
    const std::chrono::microseconds value;

public:
    Cell(std::chrono::microseconds value) : value(value){};
    double getDoubleVal() const override {
        return value.count() / 1000000.0;
    }
    int64_t getLongVal() const override {
        std::cerr << "getting long on time cell\n";
        throw this;
    }
    std::string getStringVal() const override {
        std::cerr << "getting string on time cell\n";
        throw this;
    }
    std::string toString(int /* precision */) const override {
        return Tools::formatTime(value);
    }
    std::chrono::microseconds getTimeVal() const override {
        return value;
    }
};

template <>
class Cell<double> : public CellInterface {
    const double value;

public:
    Cell(double value) : value(value){};
    double getDoubleVal() const override {
        return value;
    }
    int64_t getLongVal() const override {
        std::cerr << "getting long on double cell\n";
        throw this;
    }
    std::string getStringVal() const override {
        std::cerr << "getting string on double cell\n";
        throw this;
    }
    std::chrono::microseconds getTimeVal() const override {
        std::cerr << "getting time on double cell\n";
        throw this;
    }
    std::string toString(int /* precision */) const override {
        return Tools::formatNum(value);
    }
};

template <>
class Cell<std::string> : public CellInterface {
    const std::string value;

public:
    Cell(std::string value) : value(std::move(value)){};
    double getDoubleVal() const override {
        std::cerr << "getting double on string cell\n";
        throw this;
    }
    int64_t getLongVal() const override {
        std::cerr << "getting long on string cell\n";
        throw this;
    }
    std::string getStringVal() const override {
        return value;
    }
    std::chrono::microseconds getTimeVal() const override {
        std::cerr << "getting time on double cell\n";
        throw this;
    }
    std::string toString(int /* precision */) const override {
        return Tools::cleanString(value);
    }
};

template <>
class Cell<int64_t> : public CellInterface {
    const int64_t value;

public:
    Cell(int64_t value) : value(value){};
    double getDoubleVal() const override {
        std::cerr << "getting double on long cell\n";
        throw this;
    }
    std::string getStringVal() const override {
        std::cerr << "getting string on long cell\n";
        throw this;
    }
    int64_t getLongVal() const override {
        return value;
    }
    std::chrono::microseconds getTimeVal() const override {
        std::cerr << "getting time on long cell\n";
        throw this;
    }
    std::string toString(int precision) const override {
        return Tools::formatNum(precision, value);
    };
};

template <>
class Cell<void> : public CellInterface, std::false_type {
public:
    Cell() = default;
    double getDoubleVal() const override {
        std::cerr << "getting double on void cell";
        throw this;
    }
    int64_t getLongVal() const override {
        std::cerr << "getting long on void cell";
        throw this;
    }
    std::string getStringVal() const override {
        std::cerr << "getting string on void cell\n";
        throw this;
    }
    std::chrono::microseconds getTimeVal() const override {
        std::cerr << "getting time on void cell\n";
        throw this;
    }
    std::string toString(int /* precision */) const override {
        return "-";
    }
};

}  // namespace profile
}  // namespace souffle
