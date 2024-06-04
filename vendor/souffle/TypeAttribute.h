/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020 The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file TypeAttribute.h
 *
 * Defines the type attribute enum
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/MiscUtil.h"
#include <iostream>

namespace souffle {

/**
 * @class TypeAttribute
 * @brief Type attribute class
 */
enum class TypeAttribute {
    Symbol,    // Symbol
    Signed,    // Signed number
    Unsigned,  // Unsigned number
    Float,     // Floating point number.
    Record,    // Record
    ADT,       // ADT
};

// Printing of the TypeAttribute Enum.
inline std::ostream& operator<<(std::ostream& os, TypeAttribute T) {
    switch (T) {
        case TypeAttribute::Symbol: return os << "TypeAttribute::Symbol";
        case TypeAttribute::Signed: return os << "TypeAttribute::Signed";
        case TypeAttribute::Float: return os << "TypeAttribute::Float";
        case TypeAttribute::Unsigned: return os << "TypeAttribute::Unsigned";
        case TypeAttribute::Record: return os << "TypeAttribute::Record";
        case TypeAttribute::ADT: return os << "TypeAttribute::ADT";
    }

    fatal("unhandled `TypeAttribute`");
}

}  // end of namespace souffle
