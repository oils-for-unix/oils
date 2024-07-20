/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file NodeMapperFwd.h
 *
 * Trivial forward decls for `NodeMapper.h`
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/DynamicCasting.h"
#include "souffle/utility/Types.h"
#include "souffle/utility/VisitorFwd.h"
#include <type_traits>
#include <utility>

namespace souffle {
namespace detail {
/**
 * An abstract class for manipulating AST Nodes by substitution
 */
template <typename Node>
struct NodeMapper {
    static_assert(is_visitable_node<Node>);

    virtual ~NodeMapper() = default;

    /**
     * Abstract replacement method for a node.
     *
     * If the given nodes is to be replaced, the handed in node
     * will be destroyed by the mapper and the returned node
     * will become owned by the caller.
     */
    virtual Own<Node> operator()(Own<Node> node) const = 0;

    /**
     * Wrapper for any subclass of the AST node hierarchy performing type casts.
     */
    template <typename T>
    Own<T> operator()(Own<T> node) const {
        return UNSAFE_cast<T>((*this)(Own<Node>(std::move(node))));
    }
};
}  // namespace detail

template <typename R, typename Node>
void mapAll(R& range, detail::NodeMapper<Node> const& mapper) {
    static_assert(std::is_assignable_v<Own<Node>, decltype(std::move(*std::begin(std::declval<R&>())))>,
            "range/container element isn't a subtype of `Own<Node>`");

    // this one is small / common enough to define in fwd, save people from including the heavier weight stuff
    for (auto& cur : range) {
        cur = mapper(std::move(cur));
    }
}

}  // namespace souffle
