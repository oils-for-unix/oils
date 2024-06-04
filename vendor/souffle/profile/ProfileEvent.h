/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2018, The Souffle Developers. All rights reserved.
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ProfileEvent.h
 *
 * Declares classes for profile events
 *
 ***********************************************************************/

#pragma once

#include "souffle/profile/EventProcessor.h"
#include "souffle/profile/ProfileDatabase.h"
#include "souffle/utility/MiscUtil.h"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#ifdef WIN32
#include <Psapi.h>
#else
#include <sys/resource.h>
#include <sys/time.h>
#endif  // WIN32

namespace souffle {

/**
 * Profile Event Singleton
 */
class ProfileEventSingleton {
    /** profile database */
    profile::ProfileDatabase database{};
    std::string filename{""};

    ProfileEventSingleton(){};

public:
    ~ProfileEventSingleton() {
        stopTimer();
        dump();
    }

    /** get instance */
    static ProfileEventSingleton& instance() {
        static std::unique_ptr<ProfileEventSingleton> singleton(new ProfileEventSingleton);
        return *singleton;
    }

    /** create config record */
    void makeConfigRecord(const std::string& key, const std::string& value) {
        profile::EventProcessorSingleton::instance().process(database, "@config", key.c_str(), value.c_str());
    }

    /** create time event */
    void makeTimeEvent(const std::string& txt) {
        profile::EventProcessorSingleton::instance().process(
                database, txt.c_str(), std::chrono::duration_cast<microseconds>(now().time_since_epoch()));
    }

    /** create an event for recording start and end times */
    void makeTimingEvent(const std::string& txt, time_point start, time_point end, std::size_t startMaxRSS,
            std::size_t endMaxRSS, std::size_t size, std::size_t iteration) {
        microseconds start_ms = std::chrono::duration_cast<microseconds>(start.time_since_epoch());
        microseconds end_ms = std::chrono::duration_cast<microseconds>(end.time_since_epoch());
        profile::EventProcessorSingleton::instance().process(
                database, txt.c_str(), start_ms, end_ms, startMaxRSS, endMaxRSS, size, iteration);
    }

    /** create quantity event */
    void makeQuantityEvent(const std::string& txt, std::size_t number, int iteration) {
        profile::EventProcessorSingleton::instance().process(database, txt.c_str(), number, iteration);
    }

    void makeNonRecursiveCountEvent(const std::string& txt, double joinSize) {
        profile::EventProcessorSingleton::instance().process(database, txt.c_str(), joinSize);
    }

    void makeRecursiveCountEvent(const std::string& txt, double joinSize, std::size_t iteration) {
        profile::EventProcessorSingleton::instance().process(database, txt.c_str(), joinSize, iteration);
    }

    /** create utilisation event */
    void makeUtilisationEvent(const std::string& txt) {
        /* current time */
        microseconds time = std::chrono::duration_cast<microseconds>(now().time_since_epoch());

#ifdef WIN32
        HANDLE hProcess = GetCurrentProcess();
        FILETIME systemFileTime, userFileTime;
        GetProcessTimes(hProcess, nullptr, nullptr, &systemFileTime, &userFileTime);
        /* system CPU time and user CPU time are both expected to be in
           microseconds below, GetProcessTime gives us a value which is a
           counter of 100 nanosecond units. */
        /* system CPU time used */
        uint64_t systemTime = systemFileTime.dwHighDateTime;
        systemTime = (systemTime << 32) | systemFileTime.dwLowDateTime;
        systemTime /= 1000;
        /* user CPU time used */
        uint64_t userTime = userFileTime.dwHighDateTime;
        userTime = (userTime << 32) | userFileTime.dwLowDateTime;
        userTime /= 1000;
        PROCESS_MEMORY_COUNTERS processMemoryCounters;
        GetProcessMemoryInfo(hProcess, &processMemoryCounters, sizeof(processMemoryCounters));
        /* Maximum resident set size (kb) */
        std::size_t maxRSS = processMemoryCounters.PeakWorkingSetSize / 1000;
#else
        /* system CPU time used */
        struct rusage ru {};
        getrusage(RUSAGE_SELF, &ru);
        /* system CPU time used */
        uint64_t systemTime = ru.ru_stime.tv_sec * 1000000 + ru.ru_stime.tv_usec;
        /* user CPU time used */
        uint64_t userTime = ru.ru_utime.tv_sec * 1000000 + ru.ru_utime.tv_usec;
        /* Maximum resident set size (kb) */
        std::size_t maxRSS = ru.ru_maxrss;
#endif  // WIN32

        profile::EventProcessorSingleton::instance().process(
                database, txt.c_str(), time, systemTime, userTime, maxRSS);
    }

    void setOutputFile(std::string outputFilename) {
        filename = outputFilename;
    }
    /** Dump all events */
    void dump() {
        if (!filename.empty()) {
            std::ofstream os(filename);
            if (!os.is_open()) {
                std::cerr << "Cannot open profile log file <" + filename + ">";
            } else {
                database.print(os);
            }
        }
    }

    /** Start timer */
    void startTimer() {
        timer.start();
    }

    /** Stop timer */
    void stopTimer() {
        timer.stop();
    }

    void resetTimerInterval(uint32_t interval = 1) {
        timer.resetTimerInterval(interval);
    }
    const profile::ProfileDatabase& getDB() const {
        return database;
    }

    void setDBFromFile(const std::string& databaseFilename) {
        database = profile::ProfileDatabase(databaseFilename);
    }

private:
    /**  Profile Timer */
    class ProfileTimer {
    private:
        /** time interval between per utilisation read */
        uint32_t t;

        /** timer is running */
        std::atomic<bool> running{false};

        /** thread timer runs on */
        std::thread th;

        std::condition_variable conditionVariable;
        std::mutex timerMutex;

        /** number of utilisation events */
        std::atomic<uint32_t> runCount{0};

        /** run method for thread th */
        void run() {
            ProfileEventSingleton::instance().makeUtilisationEvent("@utilisation");
            ++runCount;
            if (runCount % 128 == 0) {
                increaseInterval();
            }
        }

        uint32_t getInterval() {
            return t;
        }

        /** Increase value of time interval by factor of 2 */
        void increaseInterval() {
            // Don't increase time interval past 60 seconds
            if (t < 60000) {
                t = t * 2;
            }
        }

    public:
        /*
         *  @param interval the size of the timing interval in milliseconds
         */
        ProfileTimer(uint32_t interval = 10) : t(interval) {}

        /** start timer on the thread th */
        void start() {
            if (running) {
                return;
            }
            running = true;

            th = std::thread([this]() {
                while (running) {
                    run();
                    std::unique_lock<std::mutex> lock(timerMutex);
                    conditionVariable.wait_for(lock, std::chrono::milliseconds(getInterval()));
                }
            });
        }

        /** stop timer on the thread th */
        void stop() {
            running = false;
            conditionVariable.notify_all();
            if (th.joinable()) {
                th.join();
            }
        }

        /** Reset timer interval.
         *
         *  The timer interval increases as the program executes. Resetting the interval is useful to
         *  ensure that detailed usage information is gathered even in long running programs, if desired.
         *
         *  @param interval the size of the timing interval in milliseconds
         */
        void resetTimerInterval(uint32_t interval = 10) {
            t = interval;
            runCount = 0;
            conditionVariable.notify_all();
        }
    };

    ProfileTimer timer;
};

}  // namespace souffle
