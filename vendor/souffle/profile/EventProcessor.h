/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2018, The Souffle Developers. All rights reserved.
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file EventProcessor.h
 *
 * Declares classes for event processor that parse profile events and
 * populate the profile database
 *
 ***********************************************************************/

#pragma once

#include "souffle/profile/ProfileDatabase.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StreamUtil.h"
#include <cassert>
#include <chrono>
#include <cstdarg>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace souffle {
namespace profile {
/**
 * Abstract Class for EventProcessor
 */
class EventProcessor {
public:
    virtual ~EventProcessor() = default;

    /** abstract interface for processing an profile event */
    virtual void process(ProfileDatabase&, const std::vector<std::string>& signature, va_list&) {
        fatal("Unknown profiling processing event: %s", join(signature, " "));
    }
};

/**
 * Event Processor Singleton
 *
 * Singleton that is the connection point for events
 */
class EventProcessorSingleton {
public:
    /** get instance */
    static EventProcessorSingleton& instance() {
        static EventProcessorSingleton singleton;
        return singleton;
    }

    /** register an event processor with its keyword */
    void registerEventProcessor(const std::string& keyword, EventProcessor* processor) {
        registry[keyword] = processor;
    }

    /** process a profile event */
    void process(ProfileDatabase& db, const char* txt, ...) {
        va_list args;
        va_start(args, txt);

        // escape signature
        std::string escapedText = escape(txt);
        // obtain event signature by splitting event text
        std::vector<std::string> eventSignature = splitSignature(escapedText);

        // invoke the event processor of the event
        const std::string& keyword = eventSignature[0];
        assert(eventSignature.size() > 0 && "no keyword in event description");
        assert(registry.find(keyword) != registry.end() && "EventProcessor not found!");
        registry[keyword]->process(db, eventSignature, args);

        // terminate access to variadic arguments
        va_end(args);
    }

private:
    /** keyword / event processor mapping */
    std::map<std::string, EventProcessor*> registry;

    EventProcessorSingleton() = default;

    /**
     * Escape escape characters.
     *
     * Remove all escapes, then escape double quotes.
     */
    std::string escape(const std::string& text) {
        std::string str(text);
        std::size_t start_pos = 0;
        // replace backslashes with double backslash
        while ((start_pos = str.find('\\', start_pos)) != std::string::npos) {
            if (start_pos == str.size()) {
                break;
            }
            ++start_pos;
            if (str[start_pos] != 't' && str[start_pos] != '"' && str[start_pos] != '\\' &&
                    str[start_pos] != 'n' && str[start_pos] != ';') {
                str.replace(start_pos - 1, 1, "\\\\");
            }
            ++start_pos;
        }
        return str;
    }

    /** split string */
    static std::vector<std::string> split(std::string str, std::string split_str) {
        // repeat value when splitting so "a   b" -> ["a","b"] not ["a","","","","b"]
        bool repeat = (split_str == " ");

        std::vector<std::string> elems;

        std::string temp;
        std::string hold;
        for (std::size_t i = 0; i < str.size(); i++) {
            if (repeat) {
                if (str.at(i) == split_str.at(0)) {
                    while (str.at(++i) == split_str.at(0)) {
                        ;  // set i to be at the end of the search string
                    }
                    elems.push_back(temp);
                    temp = "";
                }
                temp += str.at(i);
            } else {
                temp += str.at(i);
                hold += str.at(i);
                for (std::size_t j = 0; j < hold.size(); j++) {
                    if (hold[j] != split_str[j]) {
                        hold = "";
                    }
                }
                if (hold.size() == split_str.size()) {
                    elems.push_back(temp.substr(0, temp.size() - hold.size()));
                    hold = "";
                    temp = "";
                }
            }
        }
        if (!temp.empty()) {
            elems.push_back(temp);
        }

        return elems;
    }

    /** split string separated by semi-colon */
    static std::vector<std::string> splitSignature(std::string str) {
        for (std::size_t i = 0; i < str.size(); i++) {
            if (i > 0 && str[i] == ';' && str[i - 1] == '\\') {
                // I'm assuming this isn't a thing that will be naturally found in souffle profiler files
                str[i - 1] = '\b';
                str.erase(i--, 1);
            }
        }
        std::vector<std::string> result = split(str, ";");
        for (auto& i : result) {
            for (char& j : i) {
                if (j == '\b') {
                    j = ';';
                }
            }
        }
        return result;
    }
};

/**
 * Non-Recursive Rule Timing Profile Event Processor
 */
const class NonRecursiveRuleTimingProcessor : public EventProcessor {
public:
    NonRecursiveRuleTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@t-nonrecursive-rule", this);
    }
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        const std::string& rule = signature[3];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        std::size_t startMaxRSS = va_arg(args, std::size_t);
        std::size_t endMaxRSS = va_arg(args, std::size_t);
        std::size_t size = va_arg(args, std::size_t);
        db.addSizeEntry(
                {"program", "relation", relation, "non-recursive-rule", rule, "maxRSS", "pre"}, startMaxRSS);
        db.addSizeEntry(
                {"program", "relation", relation, "non-recursive-rule", rule, "maxRSS", "post"}, endMaxRSS);
        db.addTextEntry(
                {"program", "relation", relation, "non-recursive-rule", rule, "source-locator"}, srcLocator);
        db.addDurationEntry(
                {"program", "relation", relation, "non-recursive-rule", rule, "runtime"}, start, end);
        db.addSizeEntry({"program", "relation", relation, "non-recursive-rule", rule, "num-tuples"}, size);
    }
} nonRecursiveRuleTimingProcessor;

/**
 * Non-Recursive Rule Number Profile Event Processor
 */
const class NonRecursiveRuleNumberProcessor : public EventProcessor {
public:
    NonRecursiveRuleNumberProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@n-nonrecursive-rule", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        const std::string& rule = signature[3];
        std::size_t num = va_arg(args, std::size_t);
        db.addTextEntry(
                {"program", "relation", relation, "non-recursive-rule", rule, "source-locator"}, srcLocator);
        db.addSizeEntry({"program", "relation", relation, "non-recursive-rule", rule, "num-tuples"}, num);
    }
} nonRecursiveRuleNumberProcessor;

/**
 * Non-Recursive Estimate Join Size Profile Event Processor
 */
const class NonRecursiveEstimateJoinSizeProcessor : public EventProcessor {
public:
    NonRecursiveEstimateJoinSizeProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@non-recursive-estimate-join-size", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& attributes = signature[2];
        const std::string& constants = signature[3];
        std::string joinSize = std::to_string(va_arg(args, double));
        db.addTextEntry({"program", "statistics", "relation", relation, "attributes", attributes, "constants",
                                constants},
                joinSize);
    }
} nonRecursiveEstimateJoinSizeProcessor;

/**
 * Recursive Estimate Join Size Profile Event Processor
 */
const class RecursiveEstimateJoinSizeProcessor : public EventProcessor {
public:
    RecursiveEstimateJoinSizeProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@recursive-estimate-join-size", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& attributes = signature[2];
        const std::string& constants = signature[3];
        std::string joinSize = std::to_string(va_arg(args, double));
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addTextEntry({"program", "statistics", "relation", relation, "iteration", iteration, "attributes",
                                attributes, "constants", constants},
                joinSize);
    }
} recursiveEstimateJoinSizeProcessor;

/**
 * Recursive Rule Timing Profile Event Processor
 */
const class RecursiveRuleTimingProcessor : public EventProcessor {
public:
    RecursiveRuleTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@t-recursive-rule", this);
    }
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& version = signature[2];
        const std::string& srcLocator = signature[3];
        const std::string& rule = signature[4];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        std::size_t startMaxRSS = va_arg(args, std::size_t);
        std::size_t endMaxRSS = va_arg(args, std::size_t);
        std::size_t size = va_arg(args, std::size_t);
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "maxRSS", "pre"},
                startMaxRSS);
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "maxRSS", "post"},
                endMaxRSS);
        db.addTextEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "source-locator"},
                srcLocator);
        db.addDurationEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                    version, "runtime"},
                start, end);
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "num-tuples"},
                size);
    }
} recursiveRuleTimingProcessor;

/**
 * Recursive Rule Number Profile Event Processor
 */
const class RecursiveRuleNumberProcessor : public EventProcessor {
public:
    RecursiveRuleNumberProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@n-recursive-rule", this);
    }
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& version = signature[2];
        const std::string& srcLocator = signature[3];
        const std::string& rule = signature[4];
        std::size_t number = va_arg(args, std::size_t);
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addTextEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "source-locator"},
                srcLocator);
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "recursive-rule", rule,
                                version, "num-tuples"},
                number);
    }
} recursiveRuleNumberProcessor;

/**
 * Non-Recursive Relation Number Profile Event Processor
 */
const class NonRecursiveRelationTimingProcessor : public EventProcessor {
public:
    NonRecursiveRelationTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@t-nonrecursive-relation", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        std::size_t startMaxRSS = va_arg(args, std::size_t);
        std::size_t endMaxRSS = va_arg(args, std::size_t);
        std::size_t size = va_arg(args, std::size_t);
        db.addSizeEntry({"program", "relation", relation, "maxRSS", "pre"}, startMaxRSS);
        db.addSizeEntry({"program", "relation", relation, "maxRSS", "post"}, endMaxRSS);
        db.addSizeEntry({"program", "relation", relation, "num-tuples"}, size);
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addDurationEntry({"program", "relation", relation, "runtime"}, start, end);
    }
} nonRecursiveRelationTimingProcessor;

/**
 * Non-Recursive Relation Number Profile Event Processor
 */
const class NonRecursiveRelationNumberProcessor : public EventProcessor {
public:
    NonRecursiveRelationNumberProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@n-nonrecursive-relation", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        std::size_t num = va_arg(args, std::size_t);
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addSizeEntry({"program", "relation", relation, "num-tuples"}, num);
    }
} nonRecursiveRelationNumberProcessor;

/**
 * Recursive Relation Timing Profile Event Processor
 */
const class RecursiveRelationTimingProcessor : public EventProcessor {
public:
    RecursiveRelationTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@t-recursive-relation", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        std::size_t startMaxRSS = va_arg(args, std::size_t);
        std::size_t endMaxRSS = va_arg(args, std::size_t);
        std::size_t size = va_arg(args, std::size_t);
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addDurationEntry({"program", "relation", relation, "iteration", iteration, "runtime"}, start, end);
        db.addSizeEntry(
                {"program", "relation", relation, "iteration", iteration, "maxRSS", "pre"}, startMaxRSS);
        db.addSizeEntry(
                {"program", "relation", relation, "iteration", iteration, "maxRSS", "post"}, endMaxRSS);
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "num-tuples"}, size);
    }
} recursiveRelationTimingProcessor;

/**
 * Recursive Relation Timing Profile Event Processor
 */
const class RecursiveRelationNumberProcessor : public EventProcessor {
public:
    RecursiveRelationNumberProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@n-recursive-relation", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        std::size_t number = va_arg(args, std::size_t);
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addSizeEntry({"program", "relation", relation, "iteration", iteration, "num-tuples"}, number);
    }
} recursiveRelationNumberProcessor;

/**
 * Recursive Relation Copy Timing Profile Event Processor
 */
const class RecursiveRelationCopyTimingProcessor : public EventProcessor {
public:
    RecursiveRelationCopyTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@c-recursive-relation", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        std::size_t startMaxRSS = va_arg(args, std::size_t);
        std::size_t endMaxRSS = va_arg(args, std::size_t);
        va_arg(args, std::size_t);
        std::string iteration = std::to_string(va_arg(args, std::size_t));
        db.addSizeEntry(
                {"program", "relation", relation, "iteration", iteration, "maxRSS", "pre"}, startMaxRSS);
        db.addSizeEntry(
                {"program", "relation", relation, "iteration", iteration, "maxRSS", "post"}, endMaxRSS);
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addDurationEntry(
                {"program", "relation", relation, "iteration", iteration, "copytime"}, start, end);
    }
} recursiveRelationCopyTimingProcessor;

/**
 * Recursive Relation Copy Timing Profile Event Processor
 */
const class RelationIOTimingProcessor : public EventProcessor {
public:
    RelationIOTimingProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@t-relation-savetime", this);
        EventProcessorSingleton::instance().registerEventProcessor("@t-relation-loadtime", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& srcLocator = signature[2];
        const std::string ioType = signature[3];
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        db.addTextEntry({"program", "relation", relation, "source-locator"}, srcLocator);
        db.addDurationEntry({"program", "relation", relation, ioType}, start, end);
    }
} relationIOTimingProcessor;

/**
 * Program Run Event Processor
 */
const class ProgramTimepointProcessor : public EventProcessor {
public:
    ProgramTimepointProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@time", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        microseconds time = va_arg(args, microseconds);
        auto path = signature;
        path[0] = "program";
        db.addTimeEntry(path, time);
    }
} programTimepointProcessor;

/**
 * Program Run Event Processor
 */
const class ProgramRuntimeProcessor : public EventProcessor {
public:
    ProgramRuntimeProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@runtime", this);
    }
    /** process event input */
    void process(
            ProfileDatabase& db, const std::vector<std::string>& /* signature */, va_list& args) override {
        microseconds start = va_arg(args, microseconds);
        microseconds end = va_arg(args, microseconds);
        db.addDurationEntry({"program", "runtime"}, start, end);
    }
} programRuntimeProcessor;

/**
 * Program Resource Utilisation Event Processor
 */
const class ProgramResourceUtilisationProcessor : public EventProcessor {
public:
    ProgramResourceUtilisationProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@utilisation", this);
    }
    /** process event input */
    void process(
            ProfileDatabase& db, const std::vector<std::string>& /* signature */, va_list& args) override {
        microseconds time = va_arg(args, microseconds);
        uint64_t systemTime = va_arg(args, uint64_t);
        uint64_t userTime = va_arg(args, uint64_t);
        std::size_t maxRSS = va_arg(args, std::size_t);
        std::string timeString = std::to_string(time.count());
        db.addSizeEntry({"program", "usage", "timepoint", timeString, "systemtime"}, systemTime);
        db.addSizeEntry({"program", "usage", "timepoint", timeString, "usertime"}, userTime);
        db.addSizeEntry({"program", "usage", "timepoint", timeString, "maxRSS"}, maxRSS);
    }
} programResourceUtilisationProcessor;

/**
 * Frequency Atom Processor
 */
const class FrequencyAtomProcessor : public EventProcessor {
public:
    FrequencyAtomProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@frequency-atom", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        const std::string& version = signature[2];
        const std::string& rule = signature[3];
        const std::string& atom = signature[4];
        const std::string& originalRule = signature[5];
        std::size_t level = std::stoi(signature[6]);
        std::size_t number = va_arg(args, std::size_t);
        std::size_t iteration = va_arg(args, std::size_t);
        // non-recursive rule
        if (rule == originalRule) {
            db.addSizeEntry({"program", "relation", relation, "non-recursive-rule", rule, "atom-frequency",
                                    rule, atom, "level"},
                    level);
            db.addSizeEntry({"program", "relation", relation, "non-recursive-rule", rule, "atom-frequency",
                                    rule, atom, "num-tuples"},
                    number);
        } else {
            db.addSizeEntry(
                    {"program", "relation", relation, "iteration", std::to_string(iteration),
                            "recursive-rule", originalRule, version, "atom-frequency", rule, atom, "level"},
                    level);
            db.addSizeEntry({"program", "relation", relation, "iteration", std::to_string(iteration),
                                    "recursive-rule", originalRule, version, "atom-frequency", rule, atom,
                                    "num-tuples"},
                    number);
        }
    }
} frequencyAtomProcessor;

/**
 * Reads Processor
 */
const class RelationReadsProcessor : public EventProcessor {
public:
    RelationReadsProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@relation-reads", this);
    }
    /** process event input */
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string& relation = signature[1];
        std::size_t reads = va_arg(args, std::size_t);
        db.addSizeEntry({"program", "relation", relation, "reads"}, reads);
    }

} relationReadsProcessor;

/**
 * Config entry processor
 */
const class ConfigProcessor : public EventProcessor {
public:
    ConfigProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@config", this);
    }
    void process(
            ProfileDatabase& db, const std::vector<std::string>& /* signature */, va_list& args) override {
        const std::string key = va_arg(args, char*);
        const std::string& value = va_arg(args, char*);
        db.addTextEntry({"program", "configuration", key}, value);
    }
} configProcessor;

/**
 * Text entry processor
 */
const class TextProcessor : public EventProcessor {
public:
    TextProcessor() {
        EventProcessorSingleton::instance().registerEventProcessor("@text", this);
    }
    void process(ProfileDatabase& db, const std::vector<std::string>& signature, va_list& args) override {
        const std::string text = va_arg(args, char*);
        auto path = signature;
        path.front() = "program";
        db.addTextEntry(path, text);
    }
} textProcessor;

}  // namespace profile
}  // namespace souffle
