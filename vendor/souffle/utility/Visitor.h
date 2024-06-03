/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Visitor.h
 *
 * Defines a generic visitor pattern for nodes
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/FunctionalUtil.h"
#include "souffle/utility/Types.h"
#include "souffle/utility/VisitorFwd.h"
#include <cassert>
#include <type_traits>
#include <utility>

namespace souffle {

/**
 * Extension point for visitors.
 * Can be orderloaded in the namespace of Node
 */
template <class Node>
auto getChildNodes(Node&& node) -> decltype(node.getChildNodes()) {
    static_assert(
            std::is_const_v<std::remove_reference_t<Node>> ==
            std::is_const_v<
                    std::remove_pointer_t<std::remove_reference_t<decltype(*node.getChildNodes().begin())>>>);
    return node.getChildNodes();
}

namespace detail {

/** A tag type required for the is_visitor type trait to identify Visitors */
struct visitor_tag {};

template <typename T>
constexpr bool is_visitor = std::is_base_of_v<visitor_tag, remove_cvref_t<T>>;

template <typename T, typename U = void>
struct is_visitable_impl : std::false_type {};

template <typename T>
struct is_visitable_impl<T, std::void_t<decltype(getChildNodes(std::declval<T const&>()))>>
        : is_range<decltype(getChildNodes(std::declval<T&>()))> {};

template <typename A, typename = void>
struct is_visitable_pointer_t : std::false_type {};

template <typename A, typename = void>
struct is_visitable_container_t : std::false_type {};

template <typename A>
constexpr bool is_visitable = is_visitable_impl<remove_cvref_t<A>>::value;

template <typename A>
constexpr bool is_visitable_pointer = is_visitable_pointer_t<A>::value;

template <typename A>
constexpr bool is_visitable_element = is_visitable<A> || is_visitable_pointer<A>;

template <typename A>
constexpr bool is_visitable_container = is_visitable_container_t<A>::value;

template <typename A>
struct is_visitable_pointer_t<A, std::enable_if_t<souffle::is_pointer_like<A>>>
        : std::bool_constant<is_visitable<decltype(*std::declval<A>())>> {};

template <typename A>
struct is_visitable_container_t<A, std::void_t<decltype(std::begin(std::declval<A>()))>>
        : std::bool_constant<is_visitable_element<decltype(*std::begin(std::declval<A>()))>> {};

template <typename A>
constexpr bool is_visitable_dispatch_root = is_visitable_element<A> || is_visitable_container<A>;

// Actual guts of `souffle::Visitor`. Intended to be inherited by the partial specialisations
// for a given node type. (e.g. AST, or RAM.)
// This allows us to use partial template specialisation to pick the correct implementation for a node type.
template <typename R, class NodeType, typename... Params>
struct VisitorBase : visitor_tag {
    using Root = NodeType;
    using RootNoConstQual = std::remove_const_t<NodeType>;
    static_assert(std::is_class_v<Root>);
    static_assert(std::is_same_v<RootNoConstQual, visit_root_type_or_void<RootNoConstQual>>,
            "`RootConstQualified_` must refer to a (const-qual) node root type."
            "(Enables selecting correct visitor impl based on partial template specialisation)");

    virtual ~VisitorBase() = default;

    /** The main entry for the user allowing visitors to be utilized as functions */
    R operator()(NodeType& node, Params const&... args) {
        return dispatch(node, args...);
    }

    /**
     * The main entry for a visit process conducting the dispatching of
     * a visit to the various sub-types of Nodes. Sub-classes may override
     * this implementation to conduct pre-visit operations.
     *
     * @param node the node to be visited
     * @param args a list of extra parameters to be forwarded
     */
    virtual R dispatch(NodeType& node, Params const&... args) = 0;

    /** The base case for all visitors -- if no more specific overload was defined */
    virtual R visit_(type_identity<RootNoConstQual>, NodeType& /*node*/, Params const&... /*args*/) {
        if constexpr (std::is_same_v<void, R>) {
            return;
        } else {
            R res{};
            return res;
        }
    }
};

}  // namespace detail

/**
 * The generic base type of all Visitors realizing the dispatching of
 * visitor calls. Each visitor may define a return type R and a list of
 * extra parameters to be passed along with the visited Nodes to the
 * corresponding visitor function.
 *
 * You must define a partial specialisation of this class for your specific Node-type.
 * This specialisation must derive from `detail::VisitorBase`.
 *
 * @tparam R the result type produced by a visit call
 * @tparam Node the type of the node being visited (can be const qualified)
 * @tparam Params extra parameters to be passed to the visit call
 */
template <typename R, class NodeType, typename... Params>
struct Visitor {
    static_assert(unhandled_dispatch_type<NodeType>,
            "No partial specialisation for node type found. Likely causes:\n"
            "\t* `NodeType` isn't a root type\n"
            "\t* `SOUFFLE_VISITOR_DEFINE_PARTIAL_SPECIALISATION` wasn't applied for `NodeType`");
};

#define SOUFFLE_VISITOR_DEFINE_PARTIAL_SPECIALISATION(node, inner_visitor)              \
    template <typename R, typename... Params>                                           \
    struct souffle::Visitor<R, node, Params...> : inner_visitor<R, node, Params...> {}; \
    template <typename R, typename... Params>                                           \
    struct souffle::Visitor<R, node const, Params...> : inner_visitor<R, node const, Params...> {};

#define SOUFFLE_VISITOR_FORWARD(Kind) \
    if (auto* n = as<Kind>(node)) return visit_(type_identity<Kind>(), *n, args...);

#define SOUFFLE_VISITOR_LINK(Kind, Parent)                                                        \
    virtual R visit_(type_identity<Kind>, copy_const<NodeType, Kind>& n, Params const&... args) { \
        return visit_(type_identity<Parent>(), n, args...);                                       \
    }

namespace detail {

template <typename A>
using copy_const_visit_root = copy_const<std::remove_reference_t<A>, visit_root_type<A>>;

template <typename F>
using infer_visit_arg_type = std::remove_reference_t<typename lambda_traits<F>::template arg<0>>;

template <typename F>
using infer_visit_node_type = copy_const_visit_root<infer_visit_arg_type<F>>;

template <typename F, typename A>
using visitor_enable_if_arg0 = std::enable_if_t<std::is_same_v<A, remove_cvref_t<infer_visit_arg_type<F>>>>;

// useful for implicitly-as-casting continuations
template <typename CastType = void, typename F, typename A>
SOUFFLE_ALWAYS_INLINE auto matchApply([[maybe_unused]] F&& f, [[maybe_unused]] A& x) {
    using FInfo = lambda_traits<F>;
    using Arg = std::remove_reference_t<typename FInfo::template arg<0>>;
    using Result = typename FInfo::result_type;
    constexpr bool can_cast = std::is_base_of_v<A, Arg> || std::is_base_of_v<Arg, A> ||
                              std::is_same_v<CastType, AllowCrossCast>;

    if constexpr (std::is_same_v<Result, void>) {
        if constexpr (can_cast) {
            if (auto y = as<Arg, CastType>(&x)) f(*y);
        }
    } else {
        Result result = {};
        if constexpr (can_cast) {
            if (auto y = as<Arg, CastType>(&x)) result = f(*y);
        }
        return result;
    }
}

/**
 * A specialized visitor wrapping a lambda function -- an auxiliary type required
 * for visitor convenience functions.
 */
template <typename F, typename Node, typename CastType>
struct LambdaVisitor : public Visitor<void, Node> {
    F lambda;
    LambdaVisitor(F lam) : lambda(std::move(lam)) {}

    void dispatch(Node& node) override {
        matchApply<CastType>(lambda, node);
    }
};

/**
 * A factory function for creating LambdaVisitor instances.
 */
template <typename CastType = void, typename F, typename Node = infer_visit_node_type<F>>
auto makeLambdaVisitor(F&& f) {
    return LambdaVisitor<std::decay_t<F>, copy_const_visit_root<Node>, CastType>(std::forward<F>(f));
}

}  // namespace detail

/**
 * A utility function visiting all nodes within a given container of root nodes
 * recursively in a depth-first pre-order fashion applying the given function to each
 * encountered node.
 *
 * @param xs the root(s) of the ASTs to be visited
 * @param fun the function to be applied
 * @param args a list of extra parameters to be forwarded to the visitor
 */
template <typename CC, typename Visitor, typename... Args,
        typename = std::enable_if_t<detail::is_visitable_dispatch_root<CC>>,
        typename = std::enable_if_t<detail::is_visitor<Visitor>>>
void visit(CC&& xs, Visitor&& visitor, Args&&... args) {
    if constexpr (detail::is_visitable<CC>) {
        visitor(xs, args...);
        souffle::visit(getChildNodes(xs), std::forward<Visitor>(visitor), std::forward<Args>(args)...);
    } else if constexpr (detail::is_visitable_pointer<CC>) {
        static_assert(std::is_lvalue_reference_v<CC> || std::is_pointer_v<remove_cvref_t<CC>>,
                "root isn't an l-value `Own<Node>` or a raw pointer. this is likely a mistake: an r-value "
                "root means the tree will be destroyed after the call");
        assert(xs);
        souffle::visit(*xs, std::forward<Visitor>(visitor), std::forward<Args>(args)...);
    } else if constexpr (detail::is_visitable_container<CC>) {
        for (auto&& x : xs) {
            // FIXME: Remove this once nodes are converted to references
            if constexpr (is_pointer_like<decltype(x)>) {
                assert(x && "found null node during traversal");
            }

            souffle::visit(x, visitor, args...);
        }
    } else
        static_assert(unhandled_dispatch_type<CC>);
}

/**
 * A utility function visiting all nodes within the given root
 * recursively in a depth-first pre-order fashion, applying the given visitor to each
 * encountered node.
 *
 * @param root the root of the structure to be visited
 * @param visitor the visitor to be applied on each node
 */
template <typename CastType = void, class CC, typename F,
        typename = std::enable_if_t<detail::is_visitable_dispatch_root<CC>>,
        typename = std::enable_if_t<!detail::is_visitor<F>>>
void visit(CC&& root, F&& fun) {
    using Arg = std::remove_reference_t<typename lambda_traits<F>::template arg<0>>;
    using Node = detail::visit_root_type_or_void<Arg>;
    static_assert(!std::is_same_v<Node, void>, "unable to infer node type from function's first argument");

    souffle::visit(std::forward<CC>(root),
            detail::makeLambdaVisitor<CastType,
                    std::conditional_t<std::is_rvalue_reference_v<F>, std::remove_reference_t<F>, F>,
                    copy_const<Arg, Node>>(std::forward<F>(fun)));
}

/**
 * Traverses tree in pre-order, stopping immediately if the predicate matches and returns true.
 * Returns true IFF the predicate matched and returned true at least once.
 *
 * @param xs the root(s) of the ASTs to be visited
 * @param f the predicate to be applied
 */
template <typename CC, typename F /* exists B <: Node. B& -> bool */,
        typename = std::enable_if_t<detail::is_visitable_dispatch_root<CC>>>
bool visitExists(CC&& xs, F&& f) {
    if constexpr (detail::is_visitable_node<CC>) {
        if (detail::matchApply(f, xs)) return true;

        return visitExists(getChildNodes(xs), std::forward<F>(f));
    } else if constexpr (detail::is_visitable_pointer<CC>) {
        static_assert(std::is_lvalue_reference_v<CC> || std::is_pointer_v<remove_cvref_t<CC>>,
                "arg isn't an l-value `Own<Node>` or a raw pointer. this is likely a mistake: an r-value "
                "root means the tree will be destroyed after the call");
        assert(xs);
        return visitExists(*xs, f);
    } else if constexpr (detail::is_visitable_container<CC>) {
        for (auto&& x : xs)
            if (visitExists(x, f)) return true;

        return false;
    } else
        static_assert(unhandled_dispatch_type<CC>);
}

/**
 * Traverses tree in pre-order, stopping immediately if the predicate matches and returns false.
 * Returns true IFF the predicate never matched and returned false.
 *
 * @param xs the root(s) of the ASTs to be visited
 * @param f the predicate to be applied
 */
template <typename CC, typename F /* exists B <: Node. B& -> bool */,
        typename = std::enable_if_t<detail::is_visitable_dispatch_root<CC>>>
bool visitForAll(CC&& xs, F&& pred) {
    using Arg = remove_cvref_t<typename lambda_traits<F>::template arg<0>>;
    return !visitExists(std::forward<CC>(xs), [&](const Arg& x) { return !pred(x); });
}

/**
 * Traverse tree in pre-order. Skips sub-trees when predicate matches and returns true.
 * Returns # of frontiers found. (i.e. # of times predicate returned true.)
 *
 * @param xs the root(s) of the ASTs to be visited
 * @param f the `is-frontier` predicate
 */
template <typename CC, typename F /* exists B <: Node. B& -> bool */,
        typename = std::enable_if_t<detail::is_visitable_dispatch_root<CC>>>
size_t visitFrontier(CC&& xs, F&& f) {
    if constexpr (detail::is_visitable_node<CC>) {
        if (detail::matchApply(f, xs)) return 1;

        return visitFrontier(getChildNodes(xs), f);
    } else if constexpr (detail::is_visitable_pointer<CC>) {
        static_assert(std::is_lvalue_reference_v<CC> || std::is_pointer_v<remove_cvref_t<CC>>,
                "arg isn't an l-value `Own<Node>` or a raw pointer. this is likely a mistake: an r-value "
                "root means the tree will be destroyed after the call");
        assert(xs);
        return visitFrontier(*xs, f);
    } else if constexpr (detail::is_visitable_container<CC>) {
        size_t count = 0;
        for (auto&& x : xs)
            count += visitFrontier(x, f);

        return count;
    } else
        static_assert(unhandled_dispatch_type<CC>);
}

}  // namespace souffle
