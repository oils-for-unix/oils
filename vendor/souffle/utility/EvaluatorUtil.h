/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020, The Souffle Developers. All rights reserved.
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file EvaluatorUtils.h
 *
 * Defines utility functions used by synthesised and interpreter code.
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/utility/StringUtil.h"
#include "souffle/utility/tinyformat.h"
#include <csignal>

namespace souffle::evaluator {

template <typename A, typename F /* Tuple<RamDomain,1> -> void */>
void runRange(const A from, const A to, const A step, F&& go) {
#define GO(x) go(Tuple<RamDomain, 1>{ramBitCast(x)})
    if (0 < step) {
        for (auto x = from; x < to; x += step) {
            GO(x);
        }
    } else if (step < 0) {
        for (auto x = from; to < x; x += step) {
            GO(x);
        }
    } else if (from != to) {
        // `step = 0` edge case, only if non-empty range
        GO(from);
    }
#undef GO
}

template <typename A, typename F /* Tuple<RamDomain,1> -> void */>
void runRangeBackward(const A from, const A to, F&& func) {
    assert(from > to);
    if (from > to) {
        for (auto x = from; x > to; --x) {
            func(Tuple<RamDomain, 1>{ramBitCast(x)});
        }
    }
}

template <typename A, typename F /* Tuple<RamDomain,1> -> void */>
void runRange(const A from, const A to, F&& go) {
    if constexpr (std::is_unsigned<A>()) {
        if (from <= to) {
            runRange(from, to, static_cast<A>(1U), std::forward<F>(go));
        } else {
            runRangeBackward(from, to, std::forward<F>(go));
        }
    } else {
        return runRange(from, to, A(from <= to ? 1 : -1), std::forward<F>(go));
    }
}

template <typename A>
A symbol2numeric(const std::string& src) {
    try {
        if constexpr (std::is_same_v<RamFloat, A>) {
            return RamFloatFromString(src);
        } else if constexpr (std::is_same_v<RamSigned, A>) {
            return RamSignedFromString(src, nullptr, 0);
        } else if constexpr (std::is_same_v<RamUnsigned, A>) {
            return RamUnsignedFromString(src, nullptr, 0);
        } else {
            static_assert(sizeof(A) == 0, "Invalid type specified for symbol2Numeric");
        }

    } catch (...) {
        tfm::format(std::cerr, "error: wrong string provided by `to_number(\"%s\")` functor.\n", src);
        raise(SIGFPE);
        abort();  // UNREACHABLE: `raise` lacks a no-return attribute
    }
};

template <typename A>
bool lxor(A x, A y) {
    return (x || y) && (!x != !y);
}

// HACK:  C++ doesn't have an infix logical xor operator.
//        C++ doesn't allow defining new infix operators.
//        C++ isn't a very nice language, but C++ does allow overload-based war crimes.
//        This particular war crime allows a very verbose infix op for `lxor`.
//        It should only be used in macro dispatches.
struct lxor_infix {
    template <typename A>
    struct curry {
        A x;
        bool operator+(A y) const {
            return lxor(x, y);
        }
    };
};

template <typename A>
lxor_infix::curry<A> operator+(A x, lxor_infix) {
    return lxor_infix::curry<A>{x};
}

}  // namespace souffle::evaluator
