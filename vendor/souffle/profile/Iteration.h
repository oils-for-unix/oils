/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include "souffle/profile/Rule.h"
#include <chrono>
#include <cstddef>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>

namespace souffle {
namespace profile {

/*
 * Represents recursive profile data
 */
class Iteration {
private:
    std::chrono::microseconds starttime{};
    std::chrono::microseconds endtime{};
    std::size_t numTuples = 0;
    std::chrono::microseconds copytime{};
    std::string locator = "";

    std::unordered_map<std::string, std::shared_ptr<Rule>> rules;

public:
    Iteration() : rules() {}

    void addRule(const std::string& ruleKey, std::shared_ptr<Rule>& rule) {
        rules[ruleKey] = rule;
    }

    const std::unordered_map<std::string, std::shared_ptr<Rule>>& getRules() const {
        return rules;
    }

    std::string toString() const {
        std::ostringstream output;

        output << getRuntime().count() << "," << numTuples << "," << copytime.count() << ",";
        output << " recRule:";
        for (auto& rul : rules) {
            output << rul.second->toString();
        }
        output << "\n";
        return output.str();
    }

    std::chrono::microseconds getRuntime() const {
        return endtime - starttime;
    }

    std::chrono::microseconds getStarttime() const {
        return starttime;
    }

    std::chrono::microseconds getEndtime() const {
        return endtime;
    }

    std::size_t size() const {
        return numTuples;
    }

    void setNumTuples(std::size_t numTuples) {
        this->numTuples = numTuples;
    }

    std::chrono::microseconds getCopytime() const {
        return copytime;
    }

    void setCopytime(std::chrono::microseconds copy_time) {
        this->copytime = copy_time;
    }

    void setStarttime(std::chrono::microseconds time) {
        starttime = time;
    }

    void setEndtime(std::chrono::microseconds time) {
        endtime = time;
    }

    const std::string& getLocator() const {
        return locator;
    }

    void setLocator(std::string locator) {
        this->locator = locator;
    }
};

}  // namespace profile
}  // namespace souffle
