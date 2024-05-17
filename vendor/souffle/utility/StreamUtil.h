/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file StreamUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include <map>
#include <memory>
#include <ostream>
#include <set>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/span.h"

// -------------------------------------------------------------------------------
//                           General Print Utilities
// -------------------------------------------------------------------------------

namespace souffle {

// Usage:       `using namespace stream_write_qualified_char_as_number;`
//              NB: `using` must appear in the same namespace as the `<<` callers.
//                  Putting the `using` in a parent namespace will have no effect.
// Motivation:  Octet sized numeric types are often defined as aliases of a qualified
//              `char`. e.g. `using uint8_t = unsigned char'`
//              `std::ostream` has an overload which converts qualified `char`s to plain `char`.
//              You don't usually want to print a `uint8_t` as an ASCII character.
//
// NOTE:        `char`, `signed char`, and `unsigned char` are distinct types.
namespace stream_write_qualified_char_as_number {
inline std::ostream& operator<<(std::ostream& os, signed char c) {
    return os << int(c);
}

inline std::ostream& operator<<(std::ostream& os, unsigned char c) {
    return os << unsigned(c);
}
}  // namespace stream_write_qualified_char_as_number

template <typename A>
struct IsPtrLike : std::is_pointer<A> {};
template <typename A>
struct IsPtrLike<Own<A>> : std::true_type {};
template <typename A>
struct IsPtrLike<std::shared_ptr<A>> : std::true_type {};
template <typename A>
struct IsPtrLike<std::weak_ptr<A>> : std::true_type {};

namespace detail {

/**
 * A auxiliary class to be returned by the join function aggregating the information
 * required to print a list of elements as well as the implementation of the printing
 * itself.
 */
template <typename Iter, typename Printer>
class joined_sequence {
    /** The begin of the range to be printed */
    Iter begin;

    /** The end of the range to be printed */
    Iter end;

    /** The seperator to be utilized between elements */
    std::string sep;

    /** A functor printing an element */
    Printer p;

public:
    /** A constructor setting up all fields of this class */
    joined_sequence(const Iter& a, const Iter& b, std::string sep, Printer p)
            : begin(a), end(b), sep(std::move(sep)), p(std::move(p)) {}

    /** The actual print method */
    friend std::ostream& operator<<(std::ostream& out, const joined_sequence& s) {
        auto cur = s.begin;
        if (cur == s.end) {
            return out;
        }

        s.p(out, *cur);
        ++cur;
        for (; cur != s.end; ++cur) {
            out << s.sep;
            s.p(out, *cur);
        }
        return out;
    }
};

/**
 * A generic element printer.
 *
 * @tparam Extractor a functor preparing a given value before being printed.
 */
template <typename Extractor>
struct print {
    template <typename T>
    void operator()(std::ostream& out, const T& value) const {
        // extract element to be printed from the given value and print it
        Extractor ext;
        out << ext(value);
    }
};
}  // namespace detail

/**
 * A functor representing the identity function for a generic type T.
 *
 * @tparam T some arbitrary type
 */
template <typename T>
struct id {
    T& operator()(T& t) const {
        return t;
    }
    const T& operator()(const T& t) const {
        return t;
    }
};

/**
 * A functor dereferencing a given type
 *
 * @tparam T some arbitrary type with an overloaded * operator (deref)
 */
template <typename T>
struct deref {
    auto operator()(T& t) const -> decltype(*t) {
        return *t;
    }
    auto operator()(const T& t) const -> decltype(*t) {
        return *t;
    }
};

/**
 * A functor printing elements after dereferencing it. This functor
 * is mainly intended to be utilized when printing sequences of elements
 * of a pointer type when using the join function below.
 */
template <typename T>
struct print_deref : public detail::print<deref<T>> {};

/**
 * Creates an object to be forwarded to some output stream for printing
 * sequences of elements interspersed by a given separator.
 *
 * For use cases see the test case {util_test.cpp}.
 */
template <typename Iter, typename Printer>
detail::joined_sequence<Iter, Printer> join(const Iter& a, const Iter& b, std::string sep, const Printer& p) {
    return souffle::detail::joined_sequence<Iter, Printer>(a, b, std::move(sep), p);
}

/**
 * Creates an object to be forwarded to some output stream for printing
 * sequences of elements interspersed by a given separator.
 *
 * For use cases see the test case {util_test.cpp}.
 */
template <typename Iter, typename T = typename Iter::value_type>
detail::joined_sequence<Iter, detail::print<id<T>>> join(
        const Iter& a, const Iter& b, const std::string& sep = ",") {
    return join(a, b, sep, detail::print<id<T>>());
}

/**
 * Creates an object to be forwarded to some output stream for printing
 * the content of containers interspersed by a given separator.
 *
 * For use cases see the test case {util_test.cpp}.
 */
template <typename Container, typename Printer, typename Iter = typename Container::const_iterator>
detail::joined_sequence<Iter, Printer> join(const Container& c, std::string sep, const Printer& p) {
    return join(c.begin(), c.end(), std::move(sep), p);
}

// Decide if the sane default is to deref-then-print or just print.
// Right now, deref anything deref-able *except* for a `const char*` (which handled as a C-string).
template <typename A>
constexpr bool JoinShouldDeref = IsPtrLike<A>::value && !std::is_same_v<A, char const*>;

/**
 * Creates an object to be forwarded to some output stream for printing
 * the content of containers interspersed by a given separator.
 *
 * For use cases see the test case {util_test.cpp}.
 */
template <typename Container, typename Iter = typename Container::const_iterator,
        typename T = typename std::iterator_traits<Iter>::value_type>
std::enable_if_t<!JoinShouldDeref<T>, detail::joined_sequence<Iter, detail::print<id<T>>>> join(
        const Container& c, std::string sep = ",") {
    return join(c.begin(), c.end(), std::move(sep), detail::print<id<T>>());
}

template <typename Container, typename Iter = typename Container::const_iterator,
        typename T = typename std::iterator_traits<Iter>::value_type>
std::enable_if_t<JoinShouldDeref<T>, detail::joined_sequence<Iter, detail::print<deref<T>>>> join(
        const Container& c, std::string sep = ",") {
    return join(c.begin(), c.end(), std::move(sep), detail::print<deref<T>>());
}

template <typename C, typename F>
auto joinMap(const C& c, F&& map) {
    return join(c.begin(), c.end(), ",", [&](auto&& os, auto&& x) { return os << map(x); });
}

template <typename C, typename F>
auto joinMap(const C& c, std::string sep, F&& map) {
    return join(c.begin(), c.end(), std::move(sep), [&](auto&& os, auto&& x) { return os << map(x); });
}

}  // end namespace souffle

#ifndef __EMBEDDED_SOUFFLE__

namespace std {

/**
 * Enables the generic printing of `array`s assuming their element types
 * are printable.
 */
template <typename T, std::size_t E>
ostream& operator<<(ostream& out, const array<T, E>& v) {
    return out << "[" << souffle::join(v) << "]";
}

/**
 * Introduces support for printing pairs as long as their components can be printed.
 */
template <typename A, typename B>
ostream& operator<<(ostream& out, const pair<A, B>& p) {
    return out << "(" << p.first << "," << p.second << ")";
}

/**
 * Enables the generic printing of vectors assuming their element types
 * are printable.
 */
template <typename T, typename A>
ostream& operator<<(ostream& out, const vector<T, A>& v) {
    return out << "[" << souffle::join(v) << "]";
}

/**
 * Enables the generic printing of `span`s assuming their element types
 * are printable.
 */
template <typename T, std::size_t E>
ostream& operator<<(ostream& out, const souffle::span<T, E>& v) {
    return out << "[" << souffle::join(v) << "]";
}

/**
 * Enables the generic printing of sets assuming their element types
 * are printable.
 */
template <typename K, typename C, typename A>
ostream& operator<<(ostream& out, const set<K, C, A>& s) {
    return out << "{" << souffle::join(s) << "}";
}

/**
 * Enables the generic printing of multisets assuming their element types
 * are printable.
 */
template <typename K, typename C, typename A>
ostream& operator<<(ostream& out, const multiset<K, C, A>& s) {
    return out << "{" << souffle::join(s) << "}";
}

/**
 * Enables the generic printing of maps assuming their element types
 * are printable.
 */
template <typename K, typename T, typename C, typename A>
ostream& operator<<(ostream& out, const map<K, T, C, A>& m) {
    return out << "{" << souffle::join(m, ",", [](ostream& out, const pair<K, T>& cur) {
        out << cur.first << "->" << cur.second;
    }) << "}";
}

template <typename K, typename H, typename A>
ostream& operator<<(ostream& out, const unordered_set<K, H, A>& s) {
    return out << "{" << souffle::join(s) << "}";
}

template <typename K, typename T, typename H, typename E, typename A>
ostream& operator<<(ostream& out, const unordered_map<K, T, H, E, A>& m) {
    return out << "{" << souffle::join(m, ",", [](ostream& out, const pair<K, T>& cur) {
        out << cur.first << "->" << cur.second;
    }) << "}";
}

}  // end namespace std

#endif

namespace souffle {

namespace detail {

/**
 * A utility class required for the implementation of the times function.
 */
template <typename T>
struct multiplying_printer {
    const T& value;
    unsigned times;
    multiplying_printer(const T& value, unsigned times) : value(value), times(times) {}

    friend std::ostream& operator<<(std::ostream& out, const multiplying_printer& printer) {
        for (unsigned i = 0; i < printer.times; i++) {
            out << printer.value;
        }
        return out;
    }
};
}  // namespace detail

/**
 * A utility printing a given value multiple times.
 */
template <typename T>
detail::multiplying_printer<T> times(const T& value, unsigned num) {
    return detail::multiplying_printer<T>(value, num);
}

}  // namespace souffle
