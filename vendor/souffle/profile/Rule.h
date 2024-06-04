/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2016, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#pragma once

#include <chrono>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>

namespace souffle {
namespace profile {

/*
 * Class to hold information about souffle Atom profile information
 */
class Atom {
public:
    const std::string identifier;
    const std::string rule;
    const std::size_t level;
    const std::size_t frequency;

    Atom(std::string identifier, std::string rule, std::size_t level, std::size_t frequency)
            : identifier(std::move(identifier)), rule(std::move(rule)), level(level), frequency(frequency) {}

    bool operator<(const Atom& other) const {
        if (rule != other.rule) {
            return rule < other.rule;
        } else if (level != other.level) {
            return level < other.level;
        }
        return identifier < other.identifier;
    }
};

/*
 * Class to hold information about souffle Rule profile information
 */
class Rule {
protected:
    const std::string name;
    std::chrono::microseconds starttime{};
    std::chrono::microseconds endtime{};
    std::size_t numTuples{0};
    std::string identifier;
    std::string locator{};
    std::set<Atom> atoms;

private:
    bool recursive = false;
    int version = 0;

public:
    Rule(std::string name, std::string id) : name(std::move(name)), identifier(std::move(id)) {}

    Rule(std::string name, int version, std::string id)
            : name(std::move(name)), identifier(std::move(id)), recursive(true), version(version) {}

    std::string getId() const {
        return identifier;
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

    std::size_t size() {
        return numTuples;
    }

    void setStarttime(std::chrono::microseconds time) {
        starttime = time;
    }

    void setEndtime(std::chrono::microseconds time) {
        endtime = time;
    }

    void setNumTuples(std::size_t numTuples) {
        this->numTuples = numTuples;
    }

    void addAtomFrequency(
            const std::string& subruleName, std::string atom, std::size_t level, std::size_t frequency) {
        atoms.emplace(atom, subruleName, level, frequency);
    }

    const std::set<Atom>& getAtoms() const {
        return atoms;
    }
    std::string getName() const {
        return name;
    }

    void setId(std::string id) {
        identifier = id;
    }

    std::string getLocator() const {
        return locator;
    }

    void setLocator(std::string locator) {
        this->locator = locator;
    }

    bool isRecursive() const {
        return recursive;
    }

    void setRecursive(bool recursive) {
        this->recursive = recursive;
    }

    int getVersion() const {
        return version;
    }

    void setVersion(int version) {
        this->version = version;
    }

    std::string toString() const {
        std::ostringstream output;
        if (recursive) {
            output << "{" << name << "," << version << ":";
        } else {
            output << "{" << name << ":";
        }
        output << "[" << getRuntime().count() << "," << numTuples << "]}";
        return output.str();
    }
};

}  // namespace profile
}  // namespace souffle
