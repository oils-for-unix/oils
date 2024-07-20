/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file BTreeUtil.h
 *
 * Utilities for a generic B-tree data structure
 *
 ***********************************************************************/

#pragma once

#include <tuple>

namespace souffle {

namespace detail {

// ---------- comparators --------------

/**
 * A generic comparator implementation as it is used by
 * a b-tree based on types that can be less-than and
 * equality comparable.
 */
template <typename T>
struct comparator {
    /**
     * Compares the values of a and b and returns
     * -1 if a<b, 1 if a>b and 0 otherwise
     */
    int operator()(const T& a, const T& b) const {
        return (a > b) - (a < b);
    }
    bool less(const T& a, const T& b) const {
        return a < b;
    }
    bool equal(const T& a, const T& b) const {
        return a == b;
    }
};

// ---------- search strategies --------------

/**
 * A common base class for search strategies in b-trees.
 */
struct search_strategy {};

/**
 * A linear search strategy for looking up keys in b-tree nodes.
 */
struct linear_search : public search_strategy {
    /**
     * Required user-defined default constructor.
     */
    linear_search() = default;

    /**
     * Obtains an iterator referencing an element equivalent to the
     * given key in the given range. If no such element is present,
     * a reference to the first element not less than the given key
     * is returned.
     */
    template <typename Key, typename Iter, typename Comp>
    inline Iter operator()(const Key& k, Iter a, Iter b, Comp& comp) const {
        return lower_bound(k, a, b, comp);
    }

    /**
     * Obtains a reference to the first element in the given range that
     * is not less than the given key.
     */
    template <typename Key, typename Iter, typename Comp>
    inline Iter lower_bound(const Key& k, Iter a, Iter b, Comp& comp) const {
        auto c = a;
        while (c < b) {
            auto r = comp(*c, k);
            if (r >= 0) {
                return c;
            }
            ++c;
        }
        return b;
    }

    /**
     * Obtains a reference to the first element in the given range that
     * such that the given key is less than the referenced element.
     */
    template <typename Key, typename Iter, typename Comp>
    inline Iter upper_bound(const Key& k, Iter a, Iter b, Comp& comp) const {
        auto c = a;
        while (c < b) {
            if (comp(*c, k) > 0) {
                return c;
            }
            ++c;
        }
        return b;
    }
};

/**
 * A binary search strategy for looking up keys in b-tree nodes.
 */
struct binary_search : public search_strategy {
    /**
     * Required user-defined default constructor.
     */
    binary_search() = default;

    /**
     * Obtains an iterator pointing to some element within the given
     * range that is equal to the given key, if available. If multiple
     * elements are equal to the given key, an undefined instance will
     * be obtained (no guaranteed lower or upper boundary).  If no such
     * element is present, a reference to the first element not less than
     * the given key will be returned.
     */
    template <typename Key, typename Iter, typename Comp>
    Iter operator()(const Key& k, Iter a, Iter b, Comp& comp) const {
        Iter c;
        auto count = b - a;
        while (count > 0) {
            auto step = count >> 1;
            c = a + step;
            auto r = comp(*c, k);
            if (r == 0) {
                return c;
            }
            if (r < 0) {
                a = ++c;
                count -= step + 1;
            } else {
                count = step;
            }
        }
        return a;
    }

    /**
     * Obtains a reference to the first element in the given range that
     * is not less than the given key.
     */
    template <typename Key, typename Iter, typename Comp>
    Iter lower_bound(const Key& k, Iter a, Iter b, Comp& comp) const {
        Iter c;
        auto count = b - a;
        while (count > 0) {
            auto step = count >> 1;
            c = a + step;
            if (comp(*c, k) < 0) {
                a = ++c;
                count -= step + 1;
            } else {
                count = step;
            }
        }
        return a;
    }

    /**
     * Obtains a reference to the first element in the given range that
     * such that the given key is less than the referenced element.
     */
    template <typename Key, typename Iter, typename Comp>
    Iter upper_bound(const Key& k, Iter a, Iter b, Comp& comp) const {
        Iter c;
        auto count = b - a;
        while (count > 0) {
            auto step = count >> 1;
            c = a + step;
            if (comp(k, *c) >= 0) {
                a = ++c;
                count -= step + 1;
            } else {
                count = step;
            }
        }
        return a;
    }
};

// ---------- search strategies selection --------------

/**
 * A template-meta class to select search strategies for b-trees
 * depending on the key type.
 */
template <typename S>
struct strategy_selection {
    using type = S;
};

struct linear : public strategy_selection<linear_search> {};
struct binary : public strategy_selection<binary_search> {};

// by default every key utilizes binary search
template <typename Key>
struct default_strategy : public binary {};

template <>
struct default_strategy<int> : public linear {};

template <typename... Ts>
struct default_strategy<std::tuple<Ts...>> : public linear {};

/**
 * The default non-updater
 */
template <typename T>
struct updater {
    bool update(T& /* old_t */, const T& /* new_t */) {
        return false;
    }
};

}  // end of namespace detail
}  // end of namespace souffle
