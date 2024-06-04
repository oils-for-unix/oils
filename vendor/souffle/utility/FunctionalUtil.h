/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file FunctionalUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/DynamicCasting.h"
#include "souffle/utility/Iteration.h"
#include "souffle/utility/MiscUtil.h"
#include <algorithm>
#include <cassert>
#include <functional>
#include <map>
#include <set>
#include <type_traits>
#include <utility>
#include <vector>

namespace souffle {

// -------------------------------------------------------------------------------
//                              Functional Utils
// -------------------------------------------------------------------------------

/**
 * A functor comparing the dereferenced value of a pointer type utilizing a
 * given comparator. Its main use case are sets of non-null pointers which should
 * be ordered according to the value addressed by the pointer.
 */
template <typename T, typename C = std::less<T>>
struct deref_less {
    bool operator()(const T* a, const T* b) const {
        return C()(*a, *b);
    }
};

// -------------------------------------------------------------------------------
//                               Lambda Utils
// -------------------------------------------------------------------------------

/**
 * A type trait enabling the deduction of type properties of lambdas.
 *
 * source:
 * https://stackoverflow.com/questions/7943525/is-it-possible-to-figure-out-the-parameter-type-and-return-type-of-a-lambda
 */
template <typename A, typename = void>
struct lambda_traits;

template <typename A>
struct lambda_traits<A, std::enable_if_t<std::is_class_v<std::decay_t<A>>>>
        : lambda_traits<decltype(&std::decay_t<A>::operator())> {};

#define LAMBDA_TYPE_INFO_REM_CTOR(...) __VA_ARGS__
#define LAMBDA_TYPE_INFO_SPEC(kind, cv, var, is_var)                                 \
    struct lambda_traits<R(kind)(Args... LAMBDA_TYPE_INFO_REM_CTOR var) cv, void> {  \
        using arity = std::integral_constant<std::size_t, sizeof...(Args)>;          \
        using is_variadic = std::integral_constant<bool, is_var>;                    \
        using is_const = std::is_const<int cv>;                                      \
                                                                                     \
        using result_type = R;                                                       \
                                                                                     \
        template <std::size_t i>                                                     \
        using arg = typename std::tuple_element<i, std::tuple<Args..., void>>::type; \
    };

#define LAMBDA_TYPE_INFO_MEMBER(cv, var, is_var)        \
    template <typename C, typename R, typename... Args> \
    LAMBDA_TYPE_INFO_SPEC(C::*, cv, var, is_var)

#define LAMBDA_TYPE_INFO_FUNC(var, is_var)  \
    template <typename R, typename... Args> \
    LAMBDA_TYPE_INFO_SPEC(*, , var, is_var) \
    template <typename R, typename... Args> \
    LAMBDA_TYPE_INFO_SPEC(&, , var, is_var)

LAMBDA_TYPE_INFO_MEMBER(const, (, ...), 1)
LAMBDA_TYPE_INFO_MEMBER(const, (), 0)
LAMBDA_TYPE_INFO_MEMBER(, (, ...), 1)
LAMBDA_TYPE_INFO_MEMBER(, (), 0)
LAMBDA_TYPE_INFO_FUNC((, ...), 1)
LAMBDA_TYPE_INFO_FUNC((), 0)
#undef LAMBDA_TYPE_INFO_REM_CTOR
#undef LAMBDA_TYPE_INFO_SPEC
#undef LAMBDA_TYPE_INFO_MEMBER
#undef LAMBDA_TYPE_INFO_FUNC

namespace detail {

template <typename F>
struct LambdaFix {
    F f;
    template <typename... Args>
    auto operator()(Args&&... args) -> decltype(f(*this, std::forward<Args>(args)...)) {
        return f(*this, std::forward<Args>(args)...);
    }
};

}  // namespace detail

template <typename F /* f -> ... */>
detail::LambdaFix<F> fix(F f) {
    return {std::move(f)};
}

// -------------------------------------------------------------------------------
//                              General Algorithms
// -------------------------------------------------------------------------------

namespace detail {
constexpr auto coerceToBool = [](auto&& x) { return (bool)x; };

template <typename C, typename F /* : A -> B */>
auto mapVector(C& xs, F&& f) {
    std::vector<decltype(f(xs[0]))> ys;
    ys.reserve(xs.size());
    for (auto&& x : xs) {
        ys.push_back(f(x));
    }
    return ys;
}
}  // namespace detail

/**
 * A generic test checking whether all elements within a container satisfy a
 * certain predicate.
 *
 * @param c the container
 * @param p the predicate
 * @return true if for all elements x in c the predicate p(x) is true, false
 *          otherwise; for empty containers the result is always true
 */
template <typename Container, typename UnaryPredicate>
bool all_of(const Container& c, UnaryPredicate p) {
    return std::all_of(c.begin(), c.end(), p);
}

/**
 * A generic test checking whether any elements within a container satisfy a
 * certain predicate.
 *
 * @param c the container
 * @param p the predicate
 * @return true if there is an element x in c such that predicate p(x) is true, false
 *          otherwise; for empty containers the result is always false
 */
template <typename Container, typename UnaryPredicate>
bool any_of(const Container& c, UnaryPredicate p) {
    return std::any_of(c.begin(), c.end(), p);
}

/**
 * A generic test checking whether all elements within a container satisfy a
 * certain predicate.
 *
 * @param c the container
 * @param p the predicate
 * @return true if for all elements x in c the predicate p(x) is true, false
 *          otherwise; for empty containers the result is always true
 */
template <typename Container, typename UnaryPredicate>
bool none_of(const Container& c, UnaryPredicate p) {
    return std::none_of(c.begin(), c.end(), p);
}

/**
 * Filter a vector to exclude certain elements.
 */
template <typename A, typename F>
std::vector<A> filterNot(std::vector<A> xs, F&& f) {
    xs.erase(std::remove_if(xs.begin(), xs.end(), std::forward<F>(f)), xs.end());
    return xs;
}

/**
 * Filter a vector to include certain elements.
 */
template <typename A, typename F>
std::vector<A> filter(std::vector<A> xs, F&& f) {
    return filterNot(std::move(xs), [&](auto&& x) { return !f(x); });
}

template <typename B, typename CrossCast = void, typename C>
auto filterAs(C&& xs) {
    return filterMap(std::forward<C>(xs), [](auto&& x) { return as<B, CrossCast>(x); });
}

/**
 * Fold left a sequence
 */
template <typename A, typename B, typename F /* : B -> A -> B */>
B foldl(std::vector<A> xs, B zero, F&& f) {
    B accum = std::move(zero);
    for (auto&& x : xs)
        accum = f(std::move(accum), std::move(x));
    return accum;
}

/**
 * Fold left a non-empty sequence
 */
template <typename A, typename F /* : A -> A -> A */>
auto foldl(std::vector<A> xs, F&& f) {
    assert(!xs.empty() && "cannot foldl an empty sequence");
    auto it = xs.begin();
    A y = std::move(*it++);
    for (; it != xs.end(); it++) {
        y = f(std::move(y), std::move(*it));
    }
    return y;
}

template <typename A, typename B, typename F /* : A -> B -> B */>
B foldr(std::vector<A> xs, B zero, F&& f) {
    B accum = std::move(zero);
    for (auto&& x : reverse(xs))
        accum = f(std::move(x), std::move(accum));
    return accum;
}

template <typename A, typename F /* : A -> A -> A */>
auto foldr(std::vector<A> xs, F&& f) {
    assert(!xs.empty() && "cannot foldr an empty sequence");
    auto it = xs.rbegin();
    A y = std::move(*it++);
    for (; it != xs.rend(); it++) {
        y = f(std::move(*it), std::move(y));
    }
    return y;
}

/**
 * Applies a function to each element of a vector and returns the results.
 *
 * Unlike `makeTransformRange`, this creates a transformed collection instead of a transformed view.
 */
template <typename A, typename F /* : A -> B */>
auto map(std::vector<A>& xs, F&& f) {
    return detail::mapVector(xs, std::forward<F>(f));
}

template <typename A, typename F /* : A -> B */>
auto map(const std::vector<A>& xs, F&& f) {
    return detail::mapVector(xs, std::forward<F>(f));
}

template <typename A, typename F /* : A -> B */>
auto map(std::vector<A>&& xs, F&& f) {
    return detail::mapVector(xs, std::forward<F>(f));
}

template <typename A, typename F /* : A -> pointer_like<B> */>
auto filterMap(const std::vector<A>& xs, F&& f) {
    using R = decltype(f(xs[0]));
    // not a pointer -> assume it's `std::optional`
    using B = std::conditional_t<std::is_pointer_v<R>, R, std::decay_t<decltype(*std::declval<R>())>>;
    std::vector<B> ys;
    ys.reserve(xs.size());
    for (auto&& x : xs) {
        auto y = f(std::move(x));
        if (y) {
            if constexpr (std::is_pointer_v<R>)
                ys.push_back(std::move(y));
            else  // assume it's `std::optional`
                ys.push_back(std::move(*y));
        }
    }
    return ys;
}

namespace detail {

template <typename It>
constexpr bool IsLegacyIteratorOutput_v = std::is_reference_v<decltype(*std::declval<It>())>&&
        std::is_move_assignable_v<std::remove_reference_t<decltype(*std::declval<It>())>>;

// HACK: Workaround r-ref collapsing w/ template parameters.
template <typename C>
struct filter {
    static_assert(!std::is_reference_v<C>);
    static constexpr bool has_output_iter = IsLegacyIteratorOutput_v<typename C::iterator>;

    template <typename F>
    C operator()(C&& xs, F&& f) {
        // TODO: replace w/ C++20 `std::erase_if`
        if constexpr (has_output_iter) {
            xs.erase(std::remove_if(xs.begin(), xs.end(), [&](auto&& x) { return !f(x); }), xs.end());
        } else {
            auto end = xs.end();
            for (auto it = xs.begin(); it != end;)
                it = f(*it) ? ++it : xs.erase(it);
        }
        return std::move(xs);
    }

    template <typename F, bool enable = std::is_copy_constructible_v<typename C::value_type>>
    std::enable_if_t<enable, C> operator()(const C& xs, F&& f) {
        C ys;
        for (auto&& x : xs)
            if (f(x)) {
                if constexpr (has_output_iter)
                    ys.insert(ys.end(), x);
                else
                    ys.insert(x);
            }
        return ys;
    }
};
}  // namespace detail

template <typename C, typename F /* : C::element_type -> bool */>
auto filter(C&& xs, F&& f) {
    return detail::filter<std::decay_t<C>>{}(std::forward<C>(xs), std::forward<F>(f));
}

template <typename C, typename F /* : C::element_type -> bool */>
auto filterNot(C&& xs, F&& f) {
    return filter(std::forward<C>(xs), [&](auto&& x) { return !f(x); });
}

template <typename A, typename F /* : A -> B */>
auto groupBy(std::vector<A> xs, F&& key) {
    std::map<decltype(key(xs.front())), std::vector<A>> m;
    for (auto&& x : xs)
        m[key(x)].push_back(std::move(x));
    return m;
}

template <typename A, typename B, typename F /* : const A& -> const B& -> () */>
void zipForEach(const std::vector<A>& xs, const std::vector<B>& ys, F&& f) {
    for (size_t i = 0; i < std::min(xs.size(), ys.size()); i++)
        f(xs[i], ys[i]);
}

template <typename A, typename B, typename F /* : const A& -> const B& -> () */>
auto zipMap(const std::vector<A>& xs, const std::vector<B>& ys, F&& f) {
    size_t n = std::min(xs.size(), ys.size());
    std::vector<decltype(f(xs.front(), ys.front()))> zs;
    zs.reserve(n);
    for (size_t i = 0; i < n; i++)
        zs.push_back(f(xs[i], ys[i]));
    return zs;
}

template <typename A, typename B>
std::vector<A> concat(std::vector<A> xs, std::vector<B> ys) {
    for (auto&& y : ys)
        xs.push_back(std::move(y));

    return xs;
}

template <typename A, typename B>
std::vector<A> concat(std::vector<A> xs, const range<B>& ys) {
    for (A y : ys)
        xs.push_back(std::move(y));

    return xs;
}

template <typename A, typename B>
std::vector<A> concat(std::vector<A> xs, B x) {
    xs.push_back(std::move(x));
    return xs;
}

template <typename A, typename B>
void append(std::vector<A>& xs, B&& y) {
    xs = concat(std::move(xs), std::forward<B>(y));
}

// -------------------------------------------------------------------------------
//                               Set Utilities
// -------------------------------------------------------------------------------

template <typename A>
std::set<A> operator&(const std::set<A, std::less<A>>& lhs, const std::set<A, std::less<A>>& rhs) {
    std::set<A> result;
    std::set_intersection(
            lhs.begin(), lhs.end(), rhs.begin(), rhs.end(), std::inserter(result, result.begin()));
    return result;
}

template <typename A>
std::set<A> operator|(const std::set<A, std::less<A>>& lhs, const std::set<A, std::less<A>>& rhs) {
    std::set<A> result;
    std::set_union(lhs.begin(), lhs.end(), rhs.begin(), rhs.end(), std::inserter(result, result.begin()));
    return result;
}

template <typename A>
std::set<A> operator-(const std::set<A, std::less<A>>& lhs, const std::set<A, std::less<A>>& rhs) {
    std::set<A> result;
    std::set_difference(
            lhs.begin(), lhs.end(), rhs.begin(), rhs.end(), std::inserter(result, result.begin()));
    return result;
}

}  // namespace souffle
