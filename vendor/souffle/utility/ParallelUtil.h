/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ParallelUtil.h
 *
 * A set of utilities abstracting from the underlying parallel library.
 * Currently supported APIs: OpenMP and Cilk
 *
 ***********************************************************************/

#pragma once

#include <atomic>
#include <cassert>
#include <cstddef>
#include <memory>
#include <new>

// https://bugs.llvm.org/show_bug.cgi?id=41423
#if defined(__cpp_lib_hardware_interference_size) && (__cpp_lib_hardware_interference_size != 201703L)
using std::hardware_constructive_interference_size;
using std::hardware_destructive_interference_size;
#else
// 64 bytes on x86-64 │ L1_CACHE_BYTES │ L1_CACHE_SHIFT │ __cacheline_aligned │
// ...
constexpr std::size_t hardware_constructive_interference_size = 2 * sizeof(max_align_t);
constexpr std::size_t hardware_destructive_interference_size = 2 * sizeof(max_align_t);
#endif

#ifdef _OPENMP

/**
 * Implementation of parallel control flow constructs utilizing OpenMP
 */

#include <omp.h>

#ifdef __APPLE__
#define pthread_yield pthread_yield_np
#elif !defined(_MSC_VER)
#include <sched.h>
// pthread_yield is deprecated and should be replaced by sched_yield
#define pthread_yield sched_yield
#elif defined _MSC_VER
#include <thread>
#define NOMINMAX
#include <windows.h>
#define pthread_yield std::this_thread::yield
#endif

#ifdef _MSC_VER
// support for a parallel region
#define PARALLEL_START __pragma(omp parallel) {
#define PARALLEL_END }

// support for parallel loops
#define pfor __pragma(omp for schedule(dynamic)) for
#else
// support for a parallel region
#define PARALLEL_START _Pragma("omp parallel") {
#define PARALLEL_END }

// support for parallel loops
#define pfor _Pragma("omp for schedule(dynamic)") for
#endif

// spawn and sync are processed sequentially (overhead to expensive)
#define task_spawn
#define task_sync

// section start / end => corresponding OpenMP pragmas
// NOTE: disabled since it causes performance losses
//#define SECTIONS_START _Pragma("omp parallel sections") {
// NOTE: we stick to flat-level parallelism since it is faster due to thread pooling
#define SECTIONS_START {
#define SECTIONS_END }

// the markers for a single section
//#define SECTION_START _Pragma("omp section") {
#define SECTION_START {
#define SECTION_END }

// a macro to create an operation context
#define CREATE_OP_CONTEXT(NAME, INIT) [[maybe_unused]] auto NAME = INIT;
#define READ_OP_CONTEXT(NAME) NAME

#else

// support for a parallel region => sequential execution
#define PARALLEL_START {
#define PARALLEL_END }

// support for parallel loops => simple sequential loop
#define pfor for

// spawn and sync not supported
#define task_spawn
#define task_sync

// sections are processed sequentially
#define SECTIONS_START {
#define SECTIONS_END }

// sections are inlined
#define SECTION_START {
#define SECTION_END }

// a macro to create an operation context
#define CREATE_OP_CONTEXT(NAME, INIT) [[maybe_unused]] auto NAME = INIT;
#define READ_OP_CONTEXT(NAME) NAME

// mark es sequential
#define IS_SEQUENTIAL

#endif

#ifndef IS_SEQUENTIAL
#define IS_PARALLEL
#endif

#ifdef IS_PARALLEL
#include <mutex>
#include <vector>
#define MAX_THREADS (omp_get_max_threads())
#else
#define MAX_THREADS (1)
#endif

namespace souffle {

struct SeqConcurrentLanes {
    struct TrivialLock {
        ~TrivialLock() {}
    };

    using lane_id = std::size_t;
    using unique_lock_type = TrivialLock;

    explicit SeqConcurrentLanes(std::size_t = 1) {}
    SeqConcurrentLanes(const SeqConcurrentLanes&) = delete;
    SeqConcurrentLanes(SeqConcurrentLanes&&) = delete;

    virtual ~SeqConcurrentLanes() {}

    std::size_t lanes() const {
        return 1;
    }

    void setNumLanes(const std::size_t) {}

    unique_lock_type guard(const lane_id) const {
        return TrivialLock();
    }

    void lock(const lane_id) const {
        return;
    }

    void unlock(const lane_id) const {
        return;
    }

    void beforeLockAllBut(const lane_id) const {
        return;
    }

    void beforeUnlockAllBut(const lane_id) const {
        return;
    }

    void lockAllBut(const lane_id) const {
        return;
    }

    void unlockAllBut(const lane_id) const {
        return;
    }
};

#ifdef IS_PARALLEL

/**
 * A small utility class for implementing simple locks.
 */
class Lock {
    // the underlying mutex
    std::mutex mux;

public:
    struct Lease {
        Lease(std::mutex& mux) : mux(&mux) {
            mux.lock();
        }
        Lease(Lease&& other) : mux(other.mux) {
            other.mux = nullptr;
        }
        Lease(const Lease& other) = delete;
        ~Lease() {
            if (mux != nullptr) {
                mux->unlock();
            }
        }

    protected:
        std::mutex* mux;
    };

    // acquired the lock for the live-cycle of the returned guard
    Lease acquire() {
        return Lease(mux);
    }

    void lock() {
        mux.lock();
    }

    bool try_lock() {
        return mux.try_lock();
    }

    void unlock() {
        mux.unlock();
    }
};

//    /* valuable source: http://locklessinc.com/articles/locks/ */

namespace detail {

/* Pause instruction to prevent excess processor bus usage */
#if defined _MSC_VER
#define cpu_relax() YieldProcessor()
#else
#ifdef __x86_64__
#define cpu_relax() asm volatile("pause\n" : : : "memory")
#else
#define cpu_relax() asm volatile("" : : : "memory")
#endif
#endif

/**
 * A utility class managing waiting operations for spin locks.
 */
class Waiter {
    int i = 0;

public:
    Waiter() = default;

    /**
     * Conducts a wait operation.
     */
    void operator()() {
        ++i;
        if ((i % 1000) == 0) {
            // there was no progress => let others work
            pthread_yield();
        } else {
            // relax this CPU
            cpu_relax();
        }
    }
};
}  // namespace detail

/* compare: http://en.cppreference.com/w/cpp/atomic/atomic_flag */
class SpinLock {
    std::atomic<int> lck{0};

public:
    SpinLock() = default;

    void lock() {
        detail::Waiter wait;
        while (!try_lock()) {
            wait();
        }
    }

    bool try_lock() {
        int should = 0;
        return lck.compare_exchange_weak(should, 1, std::memory_order_acquire);
    }

    void unlock() {
        lck.store(0, std::memory_order_release);
    }
};

/**
 * A read/write lock for increased access performance on a
 * read-heavy use case.
 */
class ReadWriteLock {
    /**
     * Based on paper:
     *         Scalable Reader-Writer Synchronization
     *         for Shared-Memory Multiprocessors
     *
     * Layout of the lock:
     *      31        ...             2                    1                    0
     *      +-------------------------+--------------------+--------------------+
     *      | interested reader count |   waiting writer   | active writer flag |
     *      +-------------------------+--------------------+--------------------+
     */

    std::atomic<int> lck{0};

public:
    ReadWriteLock() = default;

    void start_read() {
        // add reader
        auto r = lck.fetch_add(4, std::memory_order_acquire);

        // wait until there is no writer any more
        detail::Waiter wait;
        while (r & 0x3) {
            // release reader
            end_read();

            // wait a bit
            wait();

            // apply as a reader again
            r = lck.fetch_add(4, std::memory_order_acquire);

        }  // while there is a writer => spin
    }

    void end_read() {
        lck.fetch_sub(4, std::memory_order_release);
    }

    void start_write() {
        detail::Waiter wait;

        // set wait-for-write bit
        auto stat = lck.fetch_or(2, std::memory_order_acquire);
        while (stat & 0x2) {
            wait();
            stat = lck.fetch_or(2, std::memory_order_acquire);
        }

        // the caller may starve here ...
        int should = 2;
        while (!lck.compare_exchange_strong(
                should, 1, std::memory_order_acquire, std::memory_order_relaxed)) {
            wait();
            should = 2;
        }
    }

    bool try_write() {
        int should = 0;
        return lck.compare_exchange_strong(should, 1, std::memory_order_acquire, std::memory_order_relaxed);
    }

    void end_write() {
        lck.fetch_sub(1, std::memory_order_release);
    }

    bool try_upgrade_to_write() {
        int should = 4;
        return lck.compare_exchange_strong(should, 1, std::memory_order_acquire, std::memory_order_relaxed);
    }

    void downgrade_to_read() {
        // delete write bit + set num readers to 1
        lck.fetch_add(3, std::memory_order_release);
    }
};

/**
 * An implementation of an optimistic r/w lock.
 */
class OptimisticReadWriteLock {
    /**
     * The version number utilized for the synchronization.
     *
     * Usage:
     *      - even version numbers are stable versions, not being updated
     *      - odd version numbers are temporary versions, currently being updated
     */
    std::atomic<int> version{0};

public:
    /**
     * The lease utilized to link start and end of read phases.
     */
    class Lease {
        friend class OptimisticReadWriteLock;
        int version;

    public:
        Lease(int version = 0) : version(version) {}
        Lease(const Lease& lease) = default;
        Lease& operator=(const Lease& other) = default;
        Lease& operator=(Lease&& other) = default;
    };

    /**
     * A default constructor initializing the lock.
     */
    OptimisticReadWriteLock() = default;

    /**
     * Starts a read phase, making sure that there is currently no
     * active concurrent modification going on. The resulting lease
     * enables the invoking process to later-on verify that no
     * concurrent modifications took place.
     */
    Lease start_read() {
        detail::Waiter wait;

        // get a snapshot of the lease version
        auto v = version.load(std::memory_order_acquire);

        // spin while there is a write in progress
        while ((v & 0x1) == 1) {
            // wait for a moment
            wait();
            // get an updated version
            v = version.load(std::memory_order_acquire);
        }

        // done
        return Lease(v);
    }

    /**
     * Tests whether there have been concurrent modifications since
     * the given lease has been issued.
     *
     * @return true if no updates have been conducted, false otherwise
     */
    bool validate(const Lease& lease) {
        // check whether version number has changed in the mean-while
        std::atomic_thread_fence(std::memory_order_acquire);
        return lease.version == version.load(std::memory_order_relaxed);
    }

    /**
     * Ends a read phase by validating the given lease.
     *
     * @return true if no updates have been conducted since the
     *         issuing of the lease, false otherwise
     */
    bool end_read(const Lease& lease) {
        // check lease in the end
        return validate(lease);
    }

    /**
     * Starts a write phase on this lock be ensuring exclusive access
     * and invalidating any existing read lease.
     */
    void start_write() {
        detail::Waiter wait;

        // set last bit => make it odd
        auto v = version.fetch_or(0x1, std::memory_order_acquire);

        // check for concurrent writes
        while ((v & 0x1) == 1) {
            // wait for a moment
            wait();
            // get an updated version
            v = version.fetch_or(0x1, std::memory_order_acquire);
        }

        // done
    }

    /**
     * Tries to start a write phase unless there is a currently ongoing
     * write operation. In this case no write permission will be obtained.
     *
     * @return true if write permission has been granted, false otherwise.
     */
    bool try_start_write() {
        auto v = version.fetch_or(0x1, std::memory_order_acquire);
        return !(v & 0x1);
    }

    /**
     * Updates a read-lease to a write permission by a) validating that the
     * given lease is still valid and b) making sure that there is no currently
     * ongoing write operation.
     *
     * @return true if the lease was still valid and write permissions could
     *      be granted, false otherwise.
     */
    bool try_upgrade_to_write(const Lease& lease) {
        auto v = version.fetch_or(0x1, std::memory_order_acquire);

        // check whether write privileges have been gained
        if (v & 0x1) return false;  // there is another writer already

        // check whether there was no write since the gain of the read lock
        if (lease.version == v) return true;

        // if there was, undo write update
        abort_write();

        // operation failed
        return false;
    }

    /**
     * Aborts a write operation by reverting to the version number before
     * starting the ongoing write, thereby re-validating existing leases.
     */
    void abort_write() {
        // reset version number
        version.fetch_sub(1, std::memory_order_release);
    }

    /**
     * Ends a write operation by giving up the associated exclusive access
     * to the protected data and abandoning the provided write permission.
     */
    void end_write() {
        // update version number another time
        version.fetch_add(1, std::memory_order_release);
    }

    /**
     * Tests whether currently write permissions have been granted to any
     * client by this lock.
     *
     * @return true if so, false otherwise
     */
    bool is_write_locked() const {
        return version & 0x1;
    }
};

/** Concurrent lanes locking mechanism. */
struct MutexConcurrentLanes {
    using lane_id = std::size_t;
    using unique_lock_type = std::unique_lock<std::mutex>;

    explicit MutexConcurrentLanes(const std::size_t Sz) : Size(Sz), Attribution(attribution(Sz)) {
        Lanes = std::make_unique<Lane[]>(Sz);
    }
    MutexConcurrentLanes(const MutexConcurrentLanes&) = delete;
    MutexConcurrentLanes(MutexConcurrentLanes&&) = delete;

    virtual ~MutexConcurrentLanes() {}

    // Return the number of lanes.
    std::size_t lanes() const {
        return Size;
    }

    // Select a lane
    lane_id getLane(std::size_t I) const {
        if (Attribution == lane_attribution::mod_power_of_2) {
            return I & (Size - 1);
        } else {
            return I % Size;
        }
    }

    /** Change the number of lanes.
     * DO not use while threads are using this object.
     */
    void setNumLanes(const std::size_t NumLanes) {
        Size = (NumLanes == 0 ? 1 : NumLanes);
        Attribution = attribution(Size);
        Lanes = std::make_unique<Lane[]>(Size);
    }

    unique_lock_type guard(const lane_id Lane) const {
        return unique_lock_type(Lanes[Lane].Access);
    }

    // Lock the given lane.
    // Must eventually be followed by unlock(Lane).
    void lock(const lane_id Lane) const {
        Lanes[Lane].Access.lock();
    }

    // Unlock the given lane.
    // Must already be the owner of the lane's lock.
    void unlock(const lane_id Lane) const {
        Lanes[Lane].Access.unlock();
    }

    // Acquire the capability to lock all other lanes than the given one.
    //
    // Must eventually be followed by beforeUnlockAllBut(Lane).
    void beforeLockAllBut(const lane_id Lane) const {
        if (!BeforeLockAll.try_lock()) {
            // If we cannot get the lock immediately, it means it was acquired
            // concurrently by another lane that will also try to acquire our
            // lane lock.
            // So we release our lane lock to let the concurrent operation
            // progress.
            unlock(Lane);
            BeforeLockAll.lock();
            lock(Lane);
        }
    }

    // Release the capability to lock all other lanes than the given one.
    //
    // Must already be the owner of that capability.
    void beforeUnlockAllBut(const lane_id) const {
        BeforeLockAll.unlock();
    }

    // Lock all lanes but the given one.
    //
    // Must already have acquired the capability to lock all other lanes
    // by calling beforeLockAllBut(Lane).
    //
    // Must eventually be followed by unlockAllBut(Lane).
    void lockAllBut(const lane_id Lane) const {
        for (std::size_t I = 0; I < Size; ++I) {
            if (I != Lane) {
                Lanes[I].Access.lock();
            }
        }
    }

    // Unlock all lanes but the given one.
    // Must already be the owner of all the lanes' locks.
    void unlockAllBut(const lane_id Lane) const {
        for (std::size_t I = 0; I < Size; ++I) {
            if (I != Lane) {
                Lanes[I].Access.unlock();
            }
        }
    }

private:
    enum lane_attribution { mod_power_of_2, mod_other };

    struct Lane {
        alignas(hardware_destructive_interference_size) std::mutex Access;
    };

    static constexpr lane_attribution attribution(const std::size_t Sz) {
        assert(Sz > 0);
        if ((Sz & (Sz - 1)) == 0) {
            // Sz is a power of 2
            return lane_attribution::mod_power_of_2;
        } else {
            return lane_attribution::mod_other;
        }
    }

protected:
    std::size_t Size;
    lane_attribution Attribution;

private:
    mutable std::unique_ptr<Lane[]> Lanes;

    alignas(hardware_destructive_interference_size) mutable std::mutex BeforeLockAll;
};

class ConcurrentLanes : public MutexConcurrentLanes {
    using Base = MutexConcurrentLanes;

public:
    using lane_id = Base::lane_id;
    using Base::beforeLockAllBut;
    using Base::beforeUnlockAllBut;
    using Base::guard;
    using Base::lock;
    using Base::lockAllBut;
    using Base::unlock;
    using Base::unlockAllBut;

    explicit ConcurrentLanes(const std::size_t Sz) : MutexConcurrentLanes(Sz) {}
    ConcurrentLanes(const ConcurrentLanes&) = delete;
    ConcurrentLanes(ConcurrentLanes&&) = delete;

    lane_id threadLane() const {
        return getLane(static_cast<std::size_t>(omp_get_thread_num()));
    }

    void setNumLanes(const std::size_t NumLanes) {
        Base::setNumLanes(NumLanes == 0 ? omp_get_max_threads() : NumLanes);
    }

    unique_lock_type guard() const {
        return Base::guard(threadLane());
    }

    void lock() const {
        return Base::lock(threadLane());
    }

    void unlock() const {
        return Base::unlock(threadLane());
    }

    void beforeLockAllBut() const {
        return Base::beforeLockAllBut(threadLane());
    }

    void beforeUnlockAllBut() const {
        return Base::beforeUnlockAllBut(threadLane());
    }

    void lockAllBut() const {
        return Base::lockAllBut(threadLane());
    }

    void unlockAllBut() const {
        return Base::unlockAllBut(threadLane());
    }
};

#else

/**
 * A small utility class for implementing simple locks.
 */
struct Lock {
    class Lease {};

    // no locking if there is no parallel execution
    Lease acquire() {
        return Lease();
    }

    void lock() {}

    bool try_lock() {
        return true;
    }

    void unlock() {}
};

/**
 * A 'sequential' non-locking implementation for a spin lock.
 */
class SpinLock {
public:
    SpinLock() = default;

    void lock() {}

    bool try_lock() {
        return true;
    }

    void unlock() {}
};

class ReadWriteLock {
public:
    ReadWriteLock() = default;

    void start_read() {}

    void end_read() {}

    void start_write() {}

    bool try_write() {
        return true;
    }

    void end_write() {}

    bool try_upgrade_to_write() {
        return true;
    }

    void downgrade_to_read() {}
};

/**
 * A 'sequential' non-locking implementation for an optimistic r/w lock.
 */
class OptimisticReadWriteLock {
public:
    class Lease {};

    OptimisticReadWriteLock() = default;

    Lease start_read() {
        return Lease();
    }

    bool validate(const Lease& /*lease*/) {
        return true;
    }

    bool end_read(const Lease& /*lease*/) {
        return true;
    }

    void start_write() {}

    bool try_start_write() {
        return true;
    }

    bool try_upgrade_to_write(const Lease& /*lease*/) {
        return true;
    }

    void abort_write() {}

    void end_write() {}

    bool is_write_locked() const {
        return true;
    }
};

struct ConcurrentLanes : protected SeqConcurrentLanes {
    using Base = SeqConcurrentLanes;
    using lane_id = SeqConcurrentLanes::lane_id;
    using unique_lock_type = SeqConcurrentLanes::unique_lock_type;

    using Base::lanes;
    using Base::setNumLanes;

    explicit ConcurrentLanes(std::size_t Sz = MAX_THREADS) : Base(Sz) {}
    ConcurrentLanes(const ConcurrentLanes&) = delete;
    ConcurrentLanes(ConcurrentLanes&&) = delete;

    virtual ~ConcurrentLanes() {}

    lane_id threadLane() const {
        return 0;
    }

    unique_lock_type guard() const {
        return Base::guard(threadLane());
    }

    void lock() const {
        return Base::lock(threadLane());
    }

    void unlock() const {
        return Base::unlock(threadLane());
    }

    void beforeLockAllBut() const {
        return Base::beforeLockAllBut(threadLane());
    }

    void beforeUnlockAllBut() const {
        return Base::beforeUnlockAllBut(threadLane());
    }

    void lockAllBut() const {
        return Base::lockAllBut(threadLane());
    }

    void unlockAllBut() const {
        return Base::unlockAllBut(threadLane());
    }
};

#endif

/**
 * Obtains a reference to the lock synchronizing output operations.
 */
inline Lock& getOutputLock() {
    static Lock outputLock;
    return outputLock;
}

}  // namespace souffle
