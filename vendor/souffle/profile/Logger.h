/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Logger.h
 *
 * A logger is the utility utilized by RAM programs to create logs and
 * traces.
 *
 ***********************************************************************/

#pragma once

#include "souffle/profile/ProfileEvent.h"
#include "souffle/utility/MiscUtil.h"
#include <cstddef>
#include <functional>
#include <string>
#include <utility>

namespace souffle {

/**
 * The class utilized to times for the souffle profiling tool. This class
 * is utilized by both -- the interpreted and compiled version -- to conduct
 * the corresponding measurements.
 *
 * To far, only execution times are logged. More events, e.g. the number of
 * processed tuples may be added in the future.
 */
class Logger {
public:
    Logger(std::string label, std::size_t iteration) : Logger(label, iteration, []() { return 0; }) {}

    Logger(std::string label, std::size_t iteration, std::function<std::size_t()> size)
            : label(std::move(label)), start(now()), iteration(iteration), size(size), preSize(size()) {
#ifdef WIN32
        HANDLE hProcess = GetCurrentProcess();
        PROCESS_MEMORY_COUNTERS processMemoryCounters;
        GetProcessMemoryInfo(hProcess, &processMemoryCounters, sizeof(processMemoryCounters));
        startMaxRSS = processMemoryCounters.PeakWorkingSetSize / 1000;
#else
        struct rusage ru {};
        getrusage(RUSAGE_SELF, &ru);
        startMaxRSS = ru.ru_maxrss;
#endif  // WIN32
        // Assume that if we are logging the progress of an event then we care about usage during that time.
        ProfileEventSingleton::instance().resetTimerInterval();
    }

    ~Logger() {
#ifdef WIN32
        HANDLE hProcess = GetCurrentProcess();
        PROCESS_MEMORY_COUNTERS processMemoryCounters;
        GetProcessMemoryInfo(hProcess, &processMemoryCounters, sizeof(processMemoryCounters));
        std::size_t endMaxRSS = processMemoryCounters.PeakWorkingSetSize / 1000;
#else
        struct rusage ru {};
        getrusage(RUSAGE_SELF, &ru);
        std::size_t endMaxRSS = ru.ru_maxrss;
#endif  // WIN32
        ProfileEventSingleton::instance().makeTimingEvent(
                label, start, now(), startMaxRSS, endMaxRSS, size() - preSize, iteration);
    }

private:
    std::string label;
    time_point start;
    std::size_t startMaxRSS;
    std::size_t iteration;
    std::function<std::size_t()> size;
    std::size_t preSize;
};
}  // end of namespace souffle
