/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file VisitorFwd.h
 *
 * Defines the bare minimum for declaring a visitable root type.
 * Separate header to avoid dragging in everything used by `Visitor.h`.
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/Types.h"
#include <type_traits>

#define SOUFFLE_DECLARE_VISITABLE_ROOT_TYPE(ty)                                    \
    template <typename A>                                                          \
    struct souffle::detail::VisitRootType_t<A,                                     \
            std::enable_if_t<std::is_base_of_v<ty, ::souffle::remove_cvref_t<A>>>> \
            : souffle::detail::VisitRootType_t<A, ty> {};

namespace souffle::detail {
template <typename A, typename R = void>
struct VisitRootType_t {
    using type = R;
};

template <typename A>
using visit_root_type_or_void = typename VisitRootType_t<remove_cvref_t<A>>::type;

template <typename A>
constexpr bool is_visitable_node = !std::is_same_v<void, visit_root_type_or_void<A>>;

template <typename A>
using visit_root_type = std::enable_if_t<is_visitable_node<A>, visit_root_type_or_void<A>>;
}  // namespace souffle::detail
