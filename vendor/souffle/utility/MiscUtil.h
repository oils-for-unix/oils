/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file MiscUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/General.h"
#include "souffle/utility/Iteration.h"
#include "souffle/utility/Types.h"
#include "tinyformat.h"
#include <cassert>
#include <chrono>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <type_traits>
#include <unordered_map>
#include <utility>

#ifdef _WIN32
#define NOMINMAX
#define NOGDI
#include <fcntl.h>
#include <io.h>
#include <stdlib.h>
#include <windows.h>

/**
 * On windows, the following gcc builtins are missing.
 *
 * In the case of popcountll, __popcnt64 is the windows equivalent.
 *
 * For ctz and ctzll, BitScanForward and BitScanForward64 are the respective
 * windows equivalents.  However ctz is used in a constexpr context, and we can't
 * use BitScanForward, so we implement it ourselves.
 */
#if _WIN64
#define __builtin_popcountll __popcnt64
#else
#define __builtin_popcountll __popcnt
#endif

#if defined(_MSC_VER)
// return the number of trailing zeroes in value, or 32 if value is zero.
inline constexpr unsigned long __builtin_ctz(unsigned long value) {
    unsigned long trailing_zeroes = 0;
    if (value == 0) return 32;
    while ((value = value >> 1) ^ 1) {
        ++trailing_zeroes;
    }
    return trailing_zeroes;
}

// return the number of trailing zeroes in value, or 64 if value is zero.
inline constexpr int __builtin_ctzll_constexpr(unsigned long long value) {
    int trailing_zeroes = 0;

    if (value == 0) return 64;
    while ((value = value >> 1) ^ 1) {
        ++trailing_zeroes;
    }
    return trailing_zeroes;
}

inline int __builtin_ctzll(unsigned long long value) {
    unsigned long trailing_zeroes = 0;

#if _WIN64
    if (_BitScanForward64(&trailing_zeroes, value)) {
#else
    if (_BitScanForward(&trailing_zeroes, value)) {
#endif
        return static_cast<int>(trailing_zeroes);
    } else {
        return 64;  // return 64 like GCC would when value == 0
    }
}
#endif  // _MSC_VER
#endif  // _WIN32

// -------------------------------------------------------------------------------
//                               Timing Utils
// -------------------------------------------------------------------------------

namespace souffle {

/// select the most precise and steady clock to measure durations
using steady_clock = std::conditional<std::chrono::high_resolution_clock::is_steady,
        std::chrono::high_resolution_clock, std::chrono::steady_clock>::type;

static_assert(steady_clock::is_steady, "clock is not monotonically-increasing");

// a type def for a time point
using time_point = steady_clock::time_point;
using microseconds = std::chrono::microseconds;

// a shortcut for taking the current time
inline time_point now() {
    return steady_clock::now();
}

// a shortcut for obtaining the time difference in milliseconds
inline int64_t duration_in_ms(const time_point& start, const time_point& end) {
    return static_cast<int64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count());
}

// a shortcut for obtaining the time difference in microseconds
inline int64_t duration_in_us(const time_point& start, const time_point& end) {
    return static_cast<int64_t>(std::chrono::duration_cast<std::chrono::microseconds>(end - start).count());
}

// a shortcut for obtaining the time difference in nanoseconds
inline int64_t duration_in_ns(const time_point& start, const time_point& end) {
    return static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count());
}

// -------------------------------------------------------------------------------
//                             Cloning Utilities
// -------------------------------------------------------------------------------

namespace detail {
// TODO: This function is still used by ram::Node::clone() because it hasn't been
// converted to return Own<>.  Once converted, remove this.
template <typename D, typename B>
Own<D> downCast(B* ptr) {
    // ensure the clone operation casts to appropriate pointer
    static_assert(std::is_base_of_v<std::remove_const_t<B>, std::remove_const_t<D>>,
            "Needs to be able to downcast");
    return Own<D>(ptr);
}

template <typename D, typename B>
Own<D> downCast(Own<B> ptr) {
    // ensure the clone operation casts to appropriate pointer
    static_assert(std::is_base_of_v<std::remove_const_t<B>, std::remove_const_t<D>>,
            "Needs to be able to downcast");
    return Own<D>(static_cast<D*>(ptr.release()));
}

}  // namespace detail

template <typename A>
std::enable_if_t<!std::is_pointer_v<A> && !is_range_v<A>, Own<A>> clone(const A& node) {
    return detail::downCast<A>(node.cloneImpl());
}

template <typename A>
Own<A> clone(const A* node) {
    return node ? clone(*node) : nullptr;
}

template <typename A>
Own<A> clone(const Own<A>& node) {
    return clone(node.get());
}

template <typename K, typename V, typename C>
auto clone(const std::map<K, V, C>& xs) {
    std::map<K, decltype(clone(std::declval<const V&>())), C> ys;
    for (auto&& [k, v] : xs)
        ys.insert({k, clone(v)});
    return ys;
}

template <typename K, typename V, typename H>
auto clone(const std::unordered_map<K, V, H>& xs) {
    std::unordered_map<K, decltype(clone(std::declval<const V&>())), H> ys;
    for (auto&& [k, v] : xs)
        ys.insert({k, clone(v)});
    return ys;
}

/**
 * Clone a range
 */
template <typename R>
auto cloneRange(R const& range) {
    return makeTransformRange(std::begin(range), std::end(range), [](auto const& x) { return clone(x); });
}

/**
 * Clone a range, optionally allowing up-casting the result to D
 */
template <typename D = void, typename R, std::enable_if_t<is_range_v<R>, void*> = nullptr>
auto clone(R const& range) {
    auto rn = cloneRange(range);
    using ValueType = remove_cvref_t<decltype(**std::begin(range))>;
    using ResType = std::conditional_t<std::is_same_v<D, void>, ValueType, D>;
    return VecOwn<ResType>(rn.begin(), rn.end());
}

template <typename A, typename B>
auto clone(const std::pair<A, B>& p) {
    return std::make_pair(clone(p.first), clone(p.second));
}

// -------------------------------------------------------------------------------
//                             Comparison Utilities
// -------------------------------------------------------------------------------
/**
 * Compares two values referenced by a pointer where the case where both
 * pointers are null is also considered equivalent.
 */
template <typename T>
bool equal_ptr(const T* a, const T* b) {
    if (a == nullptr && b == nullptr) {
        return true;
    }
    if (a != nullptr && b != nullptr) {
        return *a == *b;
    }
    return false;
}

/**
 * Compares two values referenced by a pointer where the case where both
 * pointers are null is also considered equivalent.
 */
template <typename T>
bool equal_ptr(const Own<T>& a, const Own<T>& b) {
    return equal_ptr(a.get(), b.get());
}

// -------------------------------------------------------------------------------
//                               Error Utilities
// -------------------------------------------------------------------------------

template <typename... Args>
[[noreturn]] void fatal(const char* format, const Args&... args) {
    tfm::format(std::cerr, format, args...);
    std::cerr << "\n";
    assert(false && "fatal error; see std err");
    abort();
}

// HACK:  Workaround to suppress spurious reachability warnings.
#define UNREACHABLE_BAD_CASE_ANALYSIS fatal("unhandled switch branch");

// -------------------------------------------------------------------------------
//                               Other Utilities
// -------------------------------------------------------------------------------

template <typename F>
auto lazy(F f) {
    using A = decltype(f());
    return [cache = std::optional<A>{}, f = std::move(f)]() mutable -> A& {
        if (!cache) cache = f();
        return *cache;
    };
}

}  // namespace souffle
