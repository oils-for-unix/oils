/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file General.h
 *
 * @brief Lightweight / cheap header for misc utilities.
 *
 * Misc utilities that require non-trivial headers should go in `MiscUtil.h`
 *
 ***********************************************************************/

#if defined(_MSC_VER)
#define SOUFFLE_ALWAYS_INLINE /* TODO: MSVC equiv */
#else
// clang / gcc recognize this attribute
// NB: GCC will only inline when optimisation is on, and will warn about it.
//     Adding `inline` (even though the KW nominally has nothing to do with
//     inlining) will force it to inline in all cases. Lovely.
#define SOUFFLE_ALWAYS_INLINE [[gnu::always_inline]] inline
#endif
