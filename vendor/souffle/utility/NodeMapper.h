/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Mapper.h
 *
 * Defines generic transformation helpers for nodes
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/FunctionalUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/NodeMapperFwd.h"
#include "souffle/utility/Types.h"
#include "souffle/utility/Visitor.h"
#include <type_traits>
#include <utility>

namespace souffle {

namespace detail {

template <typename F>
using infer_mapper_arg_type = visit_root_type<
        typename lambda_traits<F>::template arg<lambda_traits<F>::arity::value - 1>::element_type>;

template <typename F, typename N, typename = void>
struct infer_mapper_arg_type_or_given {
    using type = N;
};

template <typename F, typename N>
struct infer_mapper_arg_type_or_given<F, N, std::enable_if_t<std::is_same_v<N, void>>> {
    using type = detail::infer_mapper_arg_type<F>;
};

template <typename F /* B <: A. Own<A> -> Own<B> */, typename A>
SOUFFLE_ALWAYS_INLINE void matchMutateInPlace([[maybe_unused]] F&& f, [[maybe_unused]] Own<A>& x) {
    using FInfo = lambda_traits<std::decay_t<F>>;
    using Arg = typename std::decay_t<typename FInfo::template arg<0>>::element_type;
    if constexpr (std::is_base_of_v<A, Arg> || std::is_base_of_v<Arg, A>) {
        if (auto y = as<Arg>(x)) {
            x.release();
            x = UNSAFE_cast<A>(f(Own<Arg>(y)));
        }
    }
}

/**
 * @class LambdaNodeMapper
 * @brief A special NodeMapper wrapping a lambda conducting node transformations.
 */
template <typename Node, typename F>
class LambdaNodeMapper : public NodeMapper<Node> {
    F lambda;

    template <typename A, typename = decltype(lambda(A{}))>
    SOUFFLE_ALWAYS_INLINE auto go(A node) const {
        return lambda(std::move(node));
    }

    template <typename A, typename R = decltype(lambda(std::declval<NodeMapper<Node> const&>(), A{}))>
    SOUFFLE_ALWAYS_INLINE R go(A node) const {
        return lambda(*this, std::move(node));
    }

public:
    /**
     * @brief Constructor for LambdaNodeMapper
     */
    LambdaNodeMapper(F lambda) : lambda(std::move(lambda)) {}

    /**
     * @brief Applies lambda
     */
    Own<Node> operator()(Own<Node> node) const override {
        Own<Node> result = go(std::move(node));
        assert(result != nullptr && "null-pointer in lambda ram-node mapper");
        return result;
    }
};

}  // namespace detail

template <typename N = void, typename F,
        typename Node = typename detail::infer_mapper_arg_type_or_given<F, N>::type>
auto nodeMapper(F f) {
    return detail::LambdaNodeMapper<Node, F>{std::move(f)};
}

template <typename A, typename F, typename Node = detail::visit_root_type<A>>
void mapChildPre(A& root, F&& f) {
    root.apply(nodeMapper<Node>([&](auto&& go, Own<Node> node) {
        detail::matchMutateInPlace(f, node);
        node->apply(go);
        return node;
    }));
}

template <typename A, typename F, typename = std::enable_if_t<detail::is_visitable_node<A>>>
void mapPre(Own<A>& xs, F&& f) {
    assert(xs);
    detail::matchMutateInPlace(f, xs);
    mapChildPre(*xs, f);
}

template <typename A, typename F, typename = std::enable_if_t<detail::is_visitable_node<A>>>
Own<A> mapPre(Own<A>&& x, F&& f) {
    mapPre(x, std::forward<F>(f));
    return std::move(x);
}

template <typename CC, typename F, typename = std::enable_if_t<detail::is_visitable_container<CC>>>
void mapPre(CC& xs, F&& f) {
    for (auto& x : xs)
        mapPre(x, f);
}

template <typename A, typename F, typename Node = detail::visit_root_type<A>>
void mapChildPost(A& root, F&& f) {
    root.apply(nodeMapper<Node>([&](auto&& go, Own<Node> node) {
        node->apply(go);
        detail::matchMutateInPlace(f, node);
        return node;
    }));
}

template <typename A, typename F, typename = std::enable_if_t<detail::is_visitable_node<A>>>
void mapPost(Own<A>& xs, F&& f) {
    assert(xs);
    mapChildPost(*xs, f);
    detail::matchMutateInPlace(f, xs);
}

template <typename A, typename F, typename = std::enable_if_t<detail::is_visitable_node<A>>>
Own<A> mapPost(Own<A>&& x, F&& f) {
    mapPost(x, std::forward<F>(f));
    return std::move(x);
}

template <typename CC, typename F, typename = std::enable_if_t<detail::is_visitable_container<CC>>>
void mapPost(CC& xs, F&& f) {
    for (auto& x : reverse{xs})
        mapPost(x, f);
}

template <typename A, typename F /* Own<A> -> std::pair<Own<A>, bool> */,
        typename Root = detail::visit_root_type<A>>
size_t mapChildFrontier(A& root, F&& frontier);

template <typename A, typename F /* Own<A> -> std::pair<Own<A>, bool> */,
        typename Root = detail::visit_root_type<A>>
size_t mapFrontier(Own<A>& root, F&& frontier) {
    assert(root);
    using Arg = typename std::decay_t<typename lambda_traits<F>::template arg<0>>::element_type;
    if (auto arg = as<Arg>(root)) {
        root.release();
        auto&& [tmp, seen_frontier] = frontier(Own<Arg>(arg));
        root = std::move(tmp);
        if (seen_frontier) return 1;
    }

    return mapChildFrontier(*root, std::forward<F>(frontier));
}

template <typename A, typename F /* Own<A> -> std::pair<Own<A>, bool> */,
        typename Root = detail::visit_root_type<A>>
std::pair<Own<A>, size_t> mapFrontier(Own<A>&& root, F&& frontier) {
    auto n = mapFrontier(root, std::forward<F>(frontier));
    return {std::move(root), n};
}

template <typename A, typename F /* Own<A> -> std::pair<Own<A>, bool> */, typename Root>
size_t mapChildFrontier(A& root, F&& frontier) {
    size_t frontiers = 0;
    root.apply(nodeMapper<Root>([&](Own<Root> node) {
        frontiers += mapFrontier(node, frontier);
        return node;
    }));
    return frontiers;
}

}  // namespace souffle
