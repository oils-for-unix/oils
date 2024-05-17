/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Types.h
 *
 * @brief Shared type definitions
 *
 ***********************************************************************/

#pragma once

#include <iterator>
#include <memory>
#include <type_traits>
#include <vector>

namespace souffle {

// TODO: replace with C++20 concepts
template <typename CC, typename A>
constexpr bool is_iterable_of = std::is_constructible_v<A&,
        typename std::iterator_traits<decltype(std::begin(std::declval<CC>()))>::value_type&>;

// basically std::monostate, but doesn't require importing all of `<variant>`
struct Unit {};

constexpr bool operator==(Unit, Unit) noexcept {
    return true;
}
constexpr bool operator<=(Unit, Unit) noexcept {
    return true;
}
constexpr bool operator>=(Unit, Unit) noexcept {
    return true;
}
constexpr bool operator!=(Unit, Unit) noexcept {
    return false;
}
constexpr bool operator<(Unit, Unit) noexcept {
    return false;
}
constexpr bool operator>(Unit, Unit) noexcept {
    return false;
}

template <typename A>
using Own = std::unique_ptr<A>;

template <typename A, typename B = A, typename... Args>
Own<A> mk(Args&&... xs) {
    return std::make_unique<B>(std::forward<Args>(xs)...);
}

template <typename A>
using VecOwn = std::vector<Own<A>>;

/**
 * Copy the const qualifier of type T onto type U
 */
template <typename A, typename B>
using copy_const = std::conditional_t<std::is_const_v<A>, const B, B>;

namespace detail {

template <typename A>
struct is_own_ptr_t : std::false_type {};

template <typename A>
struct is_own_ptr_t<Own<A>> : std::true_type {};

template <typename T, typename U = void>
struct is_range_impl : std::false_type {};

template <typename T>
struct is_range_impl<T, std::void_t<decltype(*std::begin(std::declval<T&>()))>> : std::true_type {};

template <typename A, typename = void>
struct is_associative : std::false_type {};

template <typename A>
struct is_associative<A, std::void_t<typename A::key_type>> : std::true_type {};

template <typename A, typename = void, typename = void>
struct is_set : std::false_type {};

template <typename A>
struct is_set<A, std::void_t<typename A::key_type>, std::void_t<typename A::value_type>>
        : std::is_same<typename A::key_type, typename A::value_type> {};

}  // namespace detail

template <typename A>
constexpr bool is_own_ptr = detail::is_own_ptr_t<std::decay_t<A>>::value;

/**
 * A simple test to check if T is a range (i.e. has std::begin())
 */
template <typename T>
struct is_range : detail::is_range_impl<T> {};

template <typename A>
constexpr bool is_range_v = is_range<A>::value;

template <typename A>
constexpr bool is_remove_ref_const = std::is_const_v<std::remove_reference_t<A>>;

/**
 * Type identity, remove once we have C++20
 */
template <typename T>
struct type_identity {
    using type = T;
};

/**
 * Remove cv ref, remove once we have C++ 20
 */
template <typename T>
using remove_cvref = std::remove_cv<std::remove_reference_t<T>>;

template <class T>
using remove_cvref_t = typename remove_cvref<T>::type;

namespace detail {
template <typename T>
struct is_pointer_like : std::is_pointer<T> {};

template <typename T>
struct is_pointer_like<Own<T>> : std::true_type {};

}  // namespace detail

template <typename T>
constexpr bool is_pointer_like = detail::is_pointer_like<remove_cvref_t<T>>::value;

// TODO: complete these or move to C++20
template <typename A>
constexpr bool is_associative = detail::is_associative<A>::value;

template <typename A>
constexpr bool is_set = detail::is_set<A>::value;

// Useful for `static_assert`ing in unhandled cases with `constexpr` static dispatching
// Gives nicer error messages. (e.g. "failed due to req' unhandled_dispatch_type<...>")
template <typename A>
constexpr bool unhandled_dispatch_type = !std::is_same_v<A, A>;

// Tells if we can static_cast<From,To>
template <typename From, typename To, typename = void>
struct can_static_cast : std::false_type {};

template <typename From, typename To>
struct can_static_cast<From, To, std::void_t<decltype(static_cast<To>(std::declval<From>()))>>
        : std::true_type {};

// A virtual base is first and foremost a base,
// that, however, cannot be static_casted to its derived class.
template <typename Base, typename Derived>
struct is_virtual_base_of
        : std::conjunction<std::is_base_of<Base, Derived>, std::negation<can_static_cast<Base*, Derived*>>> {
};

}  // namespace souffle
