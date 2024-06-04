/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ContainerUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/DynamicCasting.h"
#include "souffle/utility/Iteration.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/Types.h"

#include <algorithm>
#include <functional>
#include <iterator>
#include <map>
#include <set>
#include <type_traits>
#include <utility>
#include <vector>

namespace souffle {

// -------------------------------------------------------------------------------
//                           General Container Utilities
// -------------------------------------------------------------------------------

/**
 * Use to range-for iterate in reverse.
 * Assumes `std::rbegin` and `std::rend` are defined for type `A`.
 */
template <typename A>
struct reverse {
    reverse(A& iterable) : iterable(iterable) {}
    A& iterable;

    auto begin() {
        return std::rbegin(iterable);
    }

    auto end() {
        return std::rend(iterable);
    }
};

/**
 * A utility to check generically whether a given element is contained in a given
 * container.
 */
template <typename C, typename = std::enable_if_t<!is_associative<C>>>
bool contains(const C& container, const typename C::value_type& element) {
    return std::find(container.begin(), container.end(), element) != container.end();
}

/**
 * A utility to check generically whether a given key exists within a given
 * associative container.
 */
template <typename C, typename A, typename = std::enable_if_t<is_associative<C>>>
bool contains(const C& container, A&& element) {
    return container.find(element) != container.end();
}

/**
 * Returns the first element in a container that satisfies a given predicate,
 * nullptr otherwise.
 */
template <typename C, typename F>
auto getIf(C&& container, F&& pred) {
    auto it = std::find_if(container.begin(), container.end(), std::forward<F>(pred));
    return it == container.end() ? nullptr : *it;
}

/**
 * Get value for a given key; if not found, return default value.
 */
template <typename C, typename A, typename = std::enable_if_t<is_associative<C>>>
typename C::mapped_type const& getOr(
        const C& container, A&& key, const typename C::mapped_type& defaultValue) {
    auto it = container.find(key);

    if (it != container.end()) {
        return it->second;
    } else {
        return defaultValue;
    }
}

/**
 * Append elements to a container
 */
template <class C, typename R>
void append(C& container, R&& range) {
    container.insert(container.end(), std::begin(range), std::end(range));
}

/**
 * A utility function enabling the creation of a vector with a fixed set of
 * elements within a single expression. This is the base case covering empty
 * vectors.
 */
template <typename T>
std::vector<T> toVector() {
    return std::vector<T>();
}

/**
 * A utility function enabling the creation of a vector with a fixed set of
 * elements within a single expression. This is the step case covering vectors
 * of arbitrary length.
 */
template <typename T, typename... R>
std::vector<T> toVector(T first, R... rest) {
    // Init-lists are effectively const-arrays. You can't `move` out of them.
    // Combine with `vector`s not having variadic constructors, can't do:
    //   `vector{Own<A>{}, Own<A>{}}`
    // This is inexcusably awful and defeats the purpose of having init-lists.
    std::vector<T> xs;
    T ary[] = {std::move(first), std::move(rest)...};
    for (auto& x : ary) {
        xs.push_back(std::move(x));
    }
    return xs;
}

/**
 * A utility function enabling the creation of a vector of pointers.
 */
template <typename A = void, typename T, typename U = std::conditional_t<std::is_same_v<A, void>, T, A>>
std::vector<U*> toPtrVector(const VecOwn<T>& v) {
    std::vector<U*> res;
    for (auto& e : v) {
        res.push_back(e.get());
    }
    return res;
}

// -------------------------------------------------------------------------------
//                             Equality Utilities
// -------------------------------------------------------------------------------

/**
 * Cast the values, from baseType to toType and compare using ==. (if casting fails -> return false.)
 *
 * @tparam baseType, initial Type of values
 * @tparam toType, type where equality comparison takes place.
 */
template <typename toType, typename baseType>
bool castEq(const baseType* left, const baseType* right) {
    if (auto castedLeft = as<toType>(left)) {
        if (auto castedRight = as<toType>(right)) {
            return castedLeft == castedRight;
        }
    }
    return false;
}

/**
 * A functor class supporting the values pointers are pointing to.
 */
template <typename T>
struct comp_deref {
    bool operator()(const T& a, const T& b) const {
        if (a == nullptr) {
            return false;
        }
        if (b == nullptr) {
            return false;
        }
        return *a == *b;
    }
};

/**
 * A function testing whether two containers are equal with the given Comparator.
 */
template <typename Container, typename Comparator>
bool equal_targets(const Container& a, const Container& b, const Comparator& comp) {
    // check reference
    if (&a == &b) {
        return true;
    }

    // check size
    if (a.size() != b.size()) {
        return false;
    }

    // check content
    return std::equal(a.begin(), a.end(), b.begin(), comp);
}

/**
 * A function testing whether two containers of pointers are referencing equivalent
 * targets.
 */
template <typename T, template <typename...> class Container>
bool equal_targets(const Container<T*>& a, const Container<T*>& b) {
    return equal_targets(a, b, comp_deref<T*>());
}

/**
 * A function testing whether two containers of unique pointers are referencing equivalent
 * targets.
 */
template <typename T, template <typename...> class Container>
bool equal_targets(const Container<Own<T>>& a, const Container<Own<T>>& b) {
    return equal_targets(a, b, comp_deref<Own<T>>());
}

#ifdef _MSC_VER
// issue:
// https://developercommunity.visualstudio.com/t/c-template-template-not-recognized-as-class-templa/558979
template <typename T>
bool equal_targets(const std::vector<Own<T>>& a, const std::vector<Own<T>>& b) {
    return equal_targets(a, b, comp_deref<Own<T>>());
}

template <typename T>
bool equal_targets(const std::vector<T>& a, const std::vector<T>& b) {
    return equal_targets(a, b, comp_deref<T>());
}
#endif

/**
 * A function testing whether two maps of unique pointers are referencing to equivalent
 * targets.
 */
template <typename Key, typename Value, typename Cmp>
bool equal_targets(const std::map<Key, Own<Value>, Cmp>& a, const std::map<Key, Own<Value>, Cmp>& b) {
    auto comp = comp_deref<Own<Value>>();
    return equal_targets(
            a, b, [&comp](auto& a, auto& b) { return a.first == b.first && comp(a.second, b.second); });
}

/**
 * A function testing whether two maps are equivalent using projected values.
 */
template <typename Key, typename Value, typename Cmp, typename F>
bool equal_targets_map(const std::map<Key, Value, Cmp>& a, const std::map<Key, Value, Cmp>& b, F&& comp) {
    return equal_targets(
            a, b, [&](auto& a, auto& b) { return a.first == b.first && comp(a.second, b.second); });
}

// -------------------------------------------------------------------------------
//                             Checking Utilities
// -------------------------------------------------------------------------------
template <typename R>
bool allValidPtrs(R const& range) {
    return std::all_of(range.begin(), range.end(), [](auto&& p) { return (bool)p; });
}

}  // namespace souffle

namespace std {
template <typename Iter, typename F>
struct iterator_traits<souffle::TransformIterator<Iter, F>> {
    using iter_t = std::iterator_traits<Iter>;
    using iter_tag = typename iter_t::iterator_category;
    using difference_type = typename iter_t::difference_type;
    using reference = decltype(std::declval<F&>()(*std::declval<Iter>()));
    using value_type = std::remove_cv_t<std::remove_reference_t<reference>>;
    using iterator_category = std::conditional_t<std::is_base_of_v<std::random_access_iterator_tag, iter_tag>,
            std::random_access_iterator_tag, iter_tag>;
};
}  // namespace std
