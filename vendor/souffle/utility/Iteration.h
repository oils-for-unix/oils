/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Iteration.h
 *
 * @brief Utilities for iterators and ranges
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/Types.h"

#include <iterator>
#include <type_traits>
#include <utility>
#include <vector>

namespace souffle {

namespace detail {
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4172)
#elif defined(__GNUC__) && (__GNUC__ >= 7)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-local-addr"
#elif defined(__has_warning)
#pragma clang diagnostic push
#if __has_warning("-Wreturn-stack-address")
#pragma clang diagnostic ignored "-Wreturn-stack-address"
#endif
#endif
// This is a helper in the cases when the lambda is stateless
template <typename F>
F makeFun() {
    static_assert(std::is_empty_v<F>);
    // Even thought the lambda is stateless, it has no default ctor
    // Is this gross?  Yes, yes it is.
    // FIXME: Remove after C++20
    typename std::aligned_storage<sizeof(F)>::type fakeLam{};
    return reinterpret_cast<F const&>(fakeLam);
}
#ifdef _MSC_VER
#pragma warning(pop)
#elif defined(__GNUC__) && (__GNUC__ >= 7)
#pragma GCC diagnostic pop
#elif defined(__has_warning)
#pragma clang diagnostic pop
#endif
}  // namespace detail

// -------------------------------------------------------------
//                            Iterators
// -------------------------------------------------------------
/**
 * A wrapper for an iterator that transforms values returned by
 * the underlying iter.
 *
 * @tparam Iter ... the type of wrapped iterator
 * @tparam F    ... the function to apply
 *
 */
template <typename Iter, typename F>
class TransformIterator {
    using iter_t = std::iterator_traits<Iter>;

public:
    using difference_type = typename iter_t::difference_type;
    // TODO: The iterator concept doesn't map correctly to ephemeral views.
    //       e.g. there is no l-value store for a deref.
    //       Figure out what these should be set to.
    using value_type = decltype(std::declval<F>()(*std::declval<Iter>()));
    using pointer = std::remove_reference_t<value_type>*;
    using reference = value_type;
    static_assert(std::is_empty_v<F>, "Function object must be stateless");

    // some constructors
    template <typename = std::enable_if_t<std::is_empty_v<F>>>
    TransformIterator(Iter iter) : TransformIterator(std::move(iter), detail::makeFun<F>()) {}
    TransformIterator(Iter iter, F f) : iter(std::move(iter)), fun(std::move(f)) {}

    /* The equality operator as required by the iterator concept. */
    bool operator==(const TransformIterator& other) const {
        return iter == other.iter;
    }

    /* The not-equality operator as required by the iterator concept. */
    bool operator!=(const TransformIterator& other) const {
        return iter != other.iter;
    }

    bool operator<(TransformIterator const& other) const {
        return iter < other.iter;
    }

    bool operator<=(TransformIterator const& other) const {
        return iter <= other.iter;
    }

    bool operator>(TransformIterator const& other) const {
        return iter > other.iter;
    }

    bool operator>=(TransformIterator const& other) const {
        return iter >= other.iter;
    }

    /* The deref operator as required by the iterator concept. */
    auto operator*() const -> reference {
        return fun(*iter);
    }

    /* Support for the pointer operator. */
    auto operator->() const {
        return &**this;
    }

    /* The increment operator as required by the iterator concept. */
    TransformIterator& operator++() {
        ++iter;
        return *this;
    }

    TransformIterator operator++(int) {
        auto res = *this;
        ++iter;
        return res;
    }

    TransformIterator& operator--() {
        --iter;
        return *this;
    }

    TransformIterator operator--(int) {
        auto res = *this;
        --iter;
        return res;
    }

    TransformIterator& operator+=(difference_type n) {
        iter += n;
        return *this;
    }

    TransformIterator operator+(difference_type n) {
        auto res = *this;
        res += n;
        return res;
    }

    TransformIterator& operator-=(difference_type n) {
        iter -= n;
        return *this;
    }

    TransformIterator operator-(difference_type n) {
        auto res = *this;
        res -= n;
        return res;
    }

    difference_type operator-(TransformIterator const& other) {
        return iter - other.iter;
    }

    auto operator[](difference_type ii) const -> reference {
        return f(iter[ii]);
    }

private:
    /* The nested iterator. */
    Iter iter;
    F fun;
};

template <typename Iter, typename F>
auto operator+(
        typename TransformIterator<Iter, F>::difference_type n, TransformIterator<Iter, F> const& iter) {
    return iter + n;
}

template <typename Iter, typename F>
auto transformIter(Iter&& iter, F&& f) {
    return TransformIterator<remove_cvref_t<Iter>, std::remove_reference_t<F>>(
            std::forward<Iter>(iter), std::forward<F>(f));
}

/**
 * A wrapper for an iterator obtaining pointers of a certain type,
 * dereferencing values before forwarding them to the consumer.
 */
namespace detail {
// HACK: Use explicit structure w/ `operator()` b/c pre-C++20 lambdas do not have copy-assign operators
struct IterTransformDeref {
    template <typename A>
    auto operator()(A&& x) const -> decltype(*x) {
        return *x;
    }
};

// HACK: Use explicit structure w/ `operator()` b/c pre-C++20 lambdas do not have copy-assign operators
struct IterTransformToPtr {
    template <typename A>
    A* operator()(Own<A> const& x) const {
        return x.get();
    }
};

}  // namespace detail

template <typename Iter>
using IterDerefWrapper = TransformIterator<Iter, detail::IterTransformDeref>;

/**
 * A factory function enabling the construction of a dereferencing
 * iterator utilizing the automated deduction of template parameters.
 */
template <typename Iter>
auto derefIter(Iter&& iter) {
    return transformIter(std::forward<Iter>(iter), detail::IterTransformDeref{});
}

/**
 * A factory function that transforms an smart-ptr iter to dumb-ptr iter.
 */
template <typename Iter>
auto ptrIter(Iter&& iter) {
    return transformIter(std::forward<Iter>(iter), detail::IterTransformToPtr{});
}

// -------------------------------------------------------------
//                             Ranges
// -------------------------------------------------------------

/**
 * A utility class enabling representation of ranges by pairing
 * two iterator instances marking lower and upper boundaries.
 */
template <typename Iter>
struct range {
    using iterator = Iter;
    using const_iterator = Iter;

    // the lower and upper boundary
    Iter a, b;

    // a constructor accepting a lower and upper boundary
    range(Iter a, Iter b) : a(std::move(a)), b(std::move(b)) {}

    // default copy / move and assignment support
    range(const range&) = default;
    range(range&&) = default;
    range& operator=(const range&) = default;

    // get the lower boundary (for for-all loop)
    Iter& begin() {
        return a;
    }
    const Iter& begin() const {
        return a;
    }

    // get the upper boundary (for for-all loop)
    Iter& end() {
        return b;
    }
    const Iter& end() const {
        return b;
    }

    // emptiness check
    bool empty() const {
        return a == b;
    }

    // splits up this range into the given number of partitions
    std::vector<range> partition(std::size_t np = 100) {
        // obtain the size
        std::size_t n = 0;
        for (auto i = a; i != b; ++i) {
            n++;
        }

        // split it up
        auto s = n / np;
        auto r = n % np;
        std::vector<range> res;
        res.reserve(np);
        auto cur = a;
        auto last = cur;
        std::size_t i = 0;
        std::size_t p = 0;
        while (cur != b) {
            ++cur;
            i++;
            if (i >= (s + (p < r ? 1 : 0))) {
                res.push_back({last, cur});
                last = cur;
                p++;
                i = 0;
            }
        }
        if (cur != last) {
            res.push_back({last, cur});
        }
        return res;
    }
};

/**
 * A utility function enabling the construction of ranges
 * without explicitly specifying the iterator type.
 *
 * @tparam Iter .. the iterator type
 * @param a .. the lower boundary
 * @param b .. the upper boundary
 */
template <typename Iter>
range<Iter> make_range(const Iter& a, const Iter& b) {
    return range<Iter>(a, b);
}

template <typename Iter, typename F>
auto makeTransformRange(Iter&& begin, Iter&& end, F const& f) {
    return make_range(transformIter(std::forward<Iter>(begin), f), transformIter(std::forward<Iter>(end), f));
}

template <typename R, typename F>
auto makeTransformRange(R&& range, F const& f) {
    return makeTransformRange(range.begin(), range.end(), f);
}

template <typename Iter>
auto makeDerefRange(Iter&& begin, Iter&& end) {
    return make_range(derefIter(std::forward<Iter>(begin)), derefIter(std::forward<Iter>(end)));
}

template <typename R>
auto makePtrRange(R const& xs) {
    return make_range(ptrIter(std::begin(xs)), ptrIter(std::end(xs)));
}

/**
 * This wraps the Range container, and const_casts in place.
 */
template <typename Range, typename F>
class OwningTransformRange {
public:
    using iterator = decltype(transformIter(std::begin(std::declval<Range>()), std::declval<F>()));
    using const_iterator =
            decltype(transformIter(std::begin(std::declval<const Range>()), std::declval<const F>()));

    OwningTransformRange(Range&& range, F f) : range(std::move(range)), f(std::move(f)) {}

    auto begin() {
        return transformIter(std::begin(range), f);
    }

    auto begin() const {
        return transformIter(std::begin(range), f);
    }

    auto cbegin() const {
        return transformIter(std::cbegin(range), f);
    }

    auto end() {
        return transformIter(std::end(range), f);
    }

    auto end() const {
        return transformIter(std::end(range), f);
    }

    auto cend() const {
        return transformIter(std::cend(range), f);
    }

    auto size() const {
        return range.size();
    }

    auto& operator[](std::size_t ii) {
        return begin()[ii];
    }

    auto& operator[](std::size_t ii) const {
        return cbegin()[ii];
    }

private:
    Range range;
    F f;
};

}  // namespace souffle
