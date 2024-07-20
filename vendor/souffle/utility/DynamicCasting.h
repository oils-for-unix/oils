
/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved.
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file DynamicCasting.h
 *
 * Common utilities for dynamic casting.
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/Types.h"
#include <cassert>
#include <type_traits>

namespace souffle {

/**
 * This class is used to tell as<> that cross-casting is allowed.
 * I use a named type rather than just a bool to make the code stand out.
 */
class AllowCrossCast {};

namespace detail {

/// Tels if A is a valid cross-cast option
template <typename A>
constexpr bool is_valid_cross_cast_option = std::is_same_v<A, void> || std::is_same_v<A, AllowCrossCast>;

/// Tells if there is a function `To::classof(From*)`
template <typename From, typename To, typename = void>
struct has_classof : std::false_type {};

template <typename From, typename To>
struct has_classof<From, To, std::void_t<decltype(remove_cvref_t<To>::classof(std::declval<From*>()))>>
        : std::true_type {};
}  // namespace detail

/// Takes a non-null pointer and return whether it is pointing to a derived class of `To`.
template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<detail::is_valid_cross_cast_option<CastType>>>
inline bool isA(From* p) noexcept {
    if constexpr (detail::has_classof<From, To>::value) {
        // use classof when available
        return remove_cvref_t<To>::classof(p);
    } else {
        // fallback to dynamic_cast
        return dynamic_cast<std::add_pointer_t<copy_const<From, To>>>(p) != nullptr;
    }
}

/// forward isA when From is not a pointer
template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<detail::is_valid_cross_cast_option<CastType>>,
        typename = std::enable_if_t<std::is_same_v<CastType, AllowCrossCast> || std::is_base_of_v<From, To>>,
        typename = std::enable_if_t<std::is_class_v<From> && !is_pointer_like<From>>>
inline bool isA(From& p) noexcept {
    return isA<To>(&p);
}

/// forward isA when From is supposed to be a unique or shared pointer
template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<is_pointer_like<From>>>
inline bool isA(const From& p) noexcept {
    return isA<To, CastType>(p.get());
}

/// Takes a non-null pointer and dynamic-cast to `To`.
///
/// Leverage `To::classof` when available to avoid costly `dynamic_cast`.
template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<detail::is_valid_cross_cast_option<CastType>>>
inline auto as(From* p) noexcept {
    using ToClass = remove_cvref_t<To>;
    using FromClass = remove_cvref_t<From>;
    if constexpr (std::is_base_of_v<ToClass, FromClass>) {
        // trivial conversion from pointer to derived class to pointer to base class
        return static_cast<std::add_pointer_t<copy_const<From, ToClass>>>(p);
    } else if constexpr (std::is_base_of_v<FromClass, ToClass> &&
                         can_static_cast<FromClass*, ToClass*>::value) {
        // cast using isA when converting from pointer to non-virtual base class to pointer to derived class
        using ResultType = remove_cvref_t<To>;
        return isA<ResultType>(p) ? static_cast<std::add_pointer_t<copy_const<From, ToClass>>>(p) : nullptr;
    } else if constexpr (std::is_same_v<CastType, AllowCrossCast> ||
                         !can_static_cast<FromClass*, ToClass*>::value) {
        // dynamic cast when converting across type hierarchies or
        // converting from pointer to virtual base class to pointer to derived class
        return dynamic_cast<std::add_pointer_t<copy_const<From, ToClass>>>(p);
    } else {
        // cross-hierarchy dynamic cast not allowed unless CastType = AllowCrossCast
        static_assert(std::is_base_of_v<FromClass, ToClass>,
                "`as<B, A>` does not allow cross-type dyn casts. "
                "(i.e. `as<B, A>` where `B <: A` is not true.) "
                "Such a cast is likely a mistake or typo.");
    }
}

/// Takes a possibly null pointer and dynamic-cast to `To`.
template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<detail::is_valid_cross_cast_option<CastType>>>
inline auto as_or_null(From* p) noexcept {
    using ToClass = remove_cvref_t<To>;
    if (p == nullptr) {
        return static_cast<std::add_pointer_t<copy_const<From, ToClass>>>(nullptr);
    }
    return as<To, CastType, From>(p);
}

template <typename To, typename CastType = void, typename From,
        typename = std::enable_if_t<detail::is_valid_cross_cast_option<CastType>>,
        typename = std::enable_if_t<std::is_same_v<CastType, AllowCrossCast> || std::is_base_of_v<From, To>>,
        typename = std::enable_if_t<std::is_class_v<From> && !is_pointer_like<From>>>
inline auto as(From& x) {
    return as<To, CastType>(&x);
}

template <typename To, typename CastType = void, typename From>
inline auto as(const std::unique_ptr<From>& x) {
    return as<To, CastType>(x.get());
}

template <typename To, typename CastType = void, typename From>
inline auto as(const std::reference_wrapper<From>& x) {
    return as<To, CastType>(x.get());
}

/**
 * Down-casts and checks the cast has succeeded
 */
template <typename To, typename CastType = void, typename From>
auto& asAssert(From&& a) {
    auto* cast = as<To, CastType>(std::forward<From>(a));
    assert(cast && "Invalid cast");
    return *cast;
}

template <typename B, typename CastType = void, typename A>
Own<B> UNSAFE_cast(Own<A> x) {
    if constexpr (std::is_assignable_v<Own<B>, Own<A>>) {
        return x;
    } else {
        if (!x) return {};

        auto y = Own<B>(as<B, CastType>(x));
        assert(y && "incorrect typed return");
        x.release();  // release after assert so dbgr can report `x` if it fails
        return y;
    }
}

///**
// * Checks if the object of type Source can be casted to type Destination.
// */
// template <typename B, typename CastType = void, typename A>
//// [[deprecated("Use `as` and implicit boolean conversion instead.")]]
// bool isA(A&& src) {
//     return as<B, CastType>(std::forward<A>(src));
// }

}  // namespace souffle
