/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file BinaryConstraintOps.h
 *
 * Defines binary constraint operators for AST & RAM
 *
 ***********************************************************************/

#pragma once

#include "souffle/TypeAttribute.h"
#include "souffle/utility/MiscUtil.h"
#include <iostream>
#include <string>
#include <vector>

namespace souffle {

/**
 * Binary Constraint Operators
 */

// TODO (darth_tytus): Some of the constraints are repeated because of float and unsigned.
// This is inelegant solution, but Ram execution demands this distinction.
// Investigate a better way.

enum class BinaryConstraintOp {
    EQ,           // equivalence of two values
    FEQ,          // float equiv; b/c NaNs are never equiv
    NE,           // whether two values are different
    FNE,          // float diff; b/c NaNs are always different
    LT,           // signed <
    ULT,          // Unsigned <
    FLT,          // Float <
    SLT,          // Symbol <
    LE,           // signed ≤
    ULE,          // Unsigned ≤
    FLE,          // Float ≤
    SLE,          // Symbol ≤
    GT,           // signed >
    UGT,          // unsigned >
    FGT,          // float >
    SGT,          // Symbol >
    GE,           // signed ≥
    UGE,          // Unsigned ≥
    FGE,          // Float ≥
    SGE,          // Symbol ≥
    MATCH,        // matching string
    CONTAINS,     // whether a sub-string is contained in a string
    NOT_MATCH,    // not matching string
    NOT_CONTAINS  // whether a sub-string is not contained in a string
};

char const* toBinaryConstraintSymbol(const BinaryConstraintOp op);

inline std::ostream& operator<<(std::ostream& os, BinaryConstraintOp x) {
    return os << toBinaryConstraintSymbol(x);
}

inline BinaryConstraintOp getEqConstraint(const std::string& type) {
    switch (type[0]) {
        case 'f': return BinaryConstraintOp::FEQ;
        case 'u': return BinaryConstraintOp::EQ;
        case 'i': return BinaryConstraintOp::EQ;

        default: return BinaryConstraintOp::EQ;
    }
}

inline BinaryConstraintOp getLessEqualConstraint(const std::string& type) {
    switch (type[0]) {
        case 'f': return BinaryConstraintOp::FLE;
        case 'u': return BinaryConstraintOp::ULE;
        case 'i': return BinaryConstraintOp::LE;

        default: return BinaryConstraintOp::LE;
    }
}

inline BinaryConstraintOp getGreaterEqualConstraint(const std::string& type) {
    switch (type[0]) {
        case 'f': return BinaryConstraintOp::FGE;
        case 'u': return BinaryConstraintOp::UGE;
        case 'i': return BinaryConstraintOp::GE;

        default: return BinaryConstraintOp::GE;
    }
}

inline BinaryConstraintOp getLessThanConstraint(const std::string& type) {
    switch (type[0]) {
        case 'f': return BinaryConstraintOp::FLT;
        case 'u': return BinaryConstraintOp::ULT;
        case 'i': return BinaryConstraintOp::LT;

        default: return BinaryConstraintOp::LT;
    }
}

inline BinaryConstraintOp getGreaterThanConstraint(const std::string& type) {
    switch (type[0]) {
        case 'f': return BinaryConstraintOp::FGT;
        case 'u': return BinaryConstraintOp::UGT;
        case 'i': return BinaryConstraintOp::GT;

        default: return BinaryConstraintOp::GT;
    }
}

inline bool isEqConstraint(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::EQ:
        case BinaryConstraintOp::FEQ: return true;
        default: break;
    }
    return false;
}

inline bool isStrictIneqConstraint(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::LT:
        case BinaryConstraintOp::GT:
        case BinaryConstraintOp::ULT:
        case BinaryConstraintOp::UGT:
        case BinaryConstraintOp::FLT:
        case BinaryConstraintOp::FGT: return true;
        default: break;
    }
    return false;
}

inline bool isWeakIneqConstraint(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::LE:
        case BinaryConstraintOp::GE:
        case BinaryConstraintOp::ULE:
        case BinaryConstraintOp::UGE:
        case BinaryConstraintOp::FLE:
        case BinaryConstraintOp::FGE: return true;
        default: break;
    }
    return false;
}

inline bool isIneqConstraint(const BinaryConstraintOp constraintOp) {
    return isStrictIneqConstraint(constraintOp) || isWeakIneqConstraint(constraintOp);
}

inline bool isIndexableConstraint(const BinaryConstraintOp constraintOp) {
    return isIneqConstraint(constraintOp) || isEqConstraint(constraintOp);
}

inline bool isSignedInequalityConstraint(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::LE:
        case BinaryConstraintOp::GE:
        case BinaryConstraintOp::LT:
        case BinaryConstraintOp::GT: return true;
        default: break;
    }
    return false;
}

inline BinaryConstraintOp convertStrictToWeakIneqConstraint(const BinaryConstraintOp constraintOp) {
    assert(isStrictIneqConstraint(constraintOp));
    switch (constraintOp) {
        case BinaryConstraintOp::LT: return BinaryConstraintOp::LE;
        case BinaryConstraintOp::GT: return BinaryConstraintOp::GE;
        case BinaryConstraintOp::ULT: return BinaryConstraintOp::ULE;
        case BinaryConstraintOp::UGT: return BinaryConstraintOp::UGE;
        case BinaryConstraintOp::FLT: return BinaryConstraintOp::FLE;
        case BinaryConstraintOp::FGT: return BinaryConstraintOp::FGE;
        default: break;
    }
    return constraintOp;
}

inline BinaryConstraintOp convertStrictToNotEqualConstraint(const BinaryConstraintOp constraintOp) {
    assert(isStrictIneqConstraint(constraintOp));
    switch (constraintOp) {
        case BinaryConstraintOp::LT: return BinaryConstraintOp::NE;
        case BinaryConstraintOp::GT: return BinaryConstraintOp::NE;
        case BinaryConstraintOp::ULT: return BinaryConstraintOp::NE;
        case BinaryConstraintOp::UGT: return BinaryConstraintOp::NE;
        case BinaryConstraintOp::FLT: return BinaryConstraintOp::FNE;
        case BinaryConstraintOp::FGT: return BinaryConstraintOp::FNE;
        default: break;
    }
    return constraintOp;
}

inline bool isLessThan(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::LT:
        case BinaryConstraintOp::ULT:
        case BinaryConstraintOp::FLT: return true;
        default: break;
    }
    return false;
}

inline bool isGreaterThan(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::GT:
        case BinaryConstraintOp::UGT:
        case BinaryConstraintOp::FGT: return true;
        default: break;
    }
    return false;
}

inline bool isLessEqual(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::LE:
        case BinaryConstraintOp::ULE:
        case BinaryConstraintOp::FLE: return true;
        default: break;
    }
    return false;
}

inline bool isGreaterEqual(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::GE:
        case BinaryConstraintOp::UGE:
        case BinaryConstraintOp::FGE: return true;
        default: break;
    }
    return false;
}

/**
 * Utility function, informing whether constraint is overloaded.
 * Only the signed version's are treated as overloaded (as they are returned by the parser).
 */
inline bool isOverloaded(const BinaryConstraintOp constraintOp) {
    switch (constraintOp) {
        case BinaryConstraintOp::EQ:
        case BinaryConstraintOp::NE:
        case BinaryConstraintOp::LT:
        case BinaryConstraintOp::LE:
        case BinaryConstraintOp::GT:
        case BinaryConstraintOp::GE: return true;
        default: break;
    }
    return false;
}

/**
 * Convert Constraint to work with requested type.
 * Example: constraintOp = LT, toType = Float -> FLT (less-than working on floats).
 */
inline BinaryConstraintOp convertOverloadedConstraint(
        const BinaryConstraintOp constraintOp, const TypeAttribute toType) {
    auto FAIL = [&]() -> BinaryConstraintOp {
        fatal("invalid binary constraint overload: op = %s; type = %s", constraintOp, toType);
    };

    // clang-format off
#define COMPARE_CONSTRAINT_FLOAT_OR_RAW(op)                             \
    case BinaryConstraintOp::op:                                        \
        switch (toType) {                                               \
        default                     : return BinaryConstraintOp::   op; \
        case TypeAttribute::Float   : return BinaryConstraintOp::F##op; \
        }
#define COMPARE_CONSTRAINT(op)                                          \
    case BinaryConstraintOp::op:                                        \
        switch (toType) {                                               \
        case TypeAttribute::Signed  : return BinaryConstraintOp::   op; \
        case TypeAttribute::Unsigned: return BinaryConstraintOp::U##op; \
        case TypeAttribute::Float   : return BinaryConstraintOp::F##op; \
        case TypeAttribute::Symbol  : return BinaryConstraintOp::S##op; \
        case TypeAttribute::ADT     :                                   \
        case TypeAttribute::Record  : return FAIL();                    \
        }                                                               \
        break; /* HACK: GCC-9 is incorrectly reporting a case fallthru */
    // clang-format on

    switch (constraintOp) {
        COMPARE_CONSTRAINT_FLOAT_OR_RAW(EQ)
        COMPARE_CONSTRAINT_FLOAT_OR_RAW(NE)

        COMPARE_CONSTRAINT(LT)
        COMPARE_CONSTRAINT(LE)
        COMPARE_CONSTRAINT(GT)
        COMPARE_CONSTRAINT(GE)

        default: fatal("invalid constraint conversion: constraint = %s", constraintOp);
    }

    UNREACHABLE_BAD_CASE_ANALYSIS

#undef COMPARE_CONSTRAINT_FLOAT_OR_RAW
#undef COMPARE_CONSTRAINT
}

/**
 * Negated Constraint Operator
 * Each operator requires a negated operator which is
 * necessary for the expansion of complex rule bodies with disjunction and negation.
 */
inline BinaryConstraintOp negatedConstraintOp(const BinaryConstraintOp op) {
    switch (op) {
        case BinaryConstraintOp::EQ: return BinaryConstraintOp::NE;
        case BinaryConstraintOp::FEQ: return BinaryConstraintOp::FNE;
        case BinaryConstraintOp::NE: return BinaryConstraintOp::EQ;
        case BinaryConstraintOp::FNE: return BinaryConstraintOp::FEQ;

        case BinaryConstraintOp::LT: return BinaryConstraintOp::GE;
        case BinaryConstraintOp::ULT: return BinaryConstraintOp::UGE;
        case BinaryConstraintOp::FLT: return BinaryConstraintOp::FGE;
        case BinaryConstraintOp::SLT: return BinaryConstraintOp::SGE;

        case BinaryConstraintOp::LE: return BinaryConstraintOp::GT;
        case BinaryConstraintOp::ULE: return BinaryConstraintOp::UGT;
        case BinaryConstraintOp::FLE: return BinaryConstraintOp::FGT;
        case BinaryConstraintOp::SLE: return BinaryConstraintOp::SGT;

        case BinaryConstraintOp::GE: return BinaryConstraintOp::LT;
        case BinaryConstraintOp::UGE: return BinaryConstraintOp::ULT;
        case BinaryConstraintOp::FGE: return BinaryConstraintOp::FLT;
        case BinaryConstraintOp::SGE: return BinaryConstraintOp::SLT;

        case BinaryConstraintOp::GT: return BinaryConstraintOp::LE;
        case BinaryConstraintOp::UGT: return BinaryConstraintOp::ULE;
        case BinaryConstraintOp::FGT: return BinaryConstraintOp::FLE;
        case BinaryConstraintOp::SGT: return BinaryConstraintOp::SLE;

        case BinaryConstraintOp::MATCH: return BinaryConstraintOp::NOT_MATCH;
        case BinaryConstraintOp::NOT_MATCH: return BinaryConstraintOp::MATCH;
        case BinaryConstraintOp::CONTAINS: return BinaryConstraintOp::NOT_CONTAINS;
        case BinaryConstraintOp::NOT_CONTAINS: return BinaryConstraintOp::CONTAINS;
    }

    UNREACHABLE_BAD_CASE_ANALYSIS
}

/**
 * Converts operator to its symbolic representation
 */
inline char const* toBinaryConstraintSymbol(const BinaryConstraintOp op) {
    switch (op) {
        case BinaryConstraintOp::FEQ:
        case BinaryConstraintOp::EQ: return "=";
        case BinaryConstraintOp::FNE:
        case BinaryConstraintOp::NE: return "!=";
        case BinaryConstraintOp::SLT:
        case BinaryConstraintOp::ULT:
        case BinaryConstraintOp::FLT:
        case BinaryConstraintOp::LT: return "<";
        case BinaryConstraintOp::SLE:
        case BinaryConstraintOp::ULE:
        case BinaryConstraintOp::FLE:
        case BinaryConstraintOp::LE: return "<=";
        case BinaryConstraintOp::SGT:
        case BinaryConstraintOp::UGT:
        case BinaryConstraintOp::FGT:
        case BinaryConstraintOp::GT: return ">";
        case BinaryConstraintOp::SGE:
        case BinaryConstraintOp::UGE:
        case BinaryConstraintOp::FGE:
        case BinaryConstraintOp::GE: return ">=";
        case BinaryConstraintOp::MATCH: return "match";
        case BinaryConstraintOp::CONTAINS: return "contains";
        case BinaryConstraintOp::NOT_MATCH: return "not_match";
        case BinaryConstraintOp::NOT_CONTAINS: return "not_contains";
    }

    UNREACHABLE_BAD_CASE_ANALYSIS
}

/**
 * Converts symbolic representation of an operator to the operator.
 * Note that this won't tell you which polymorphic overload is actually used.
 */
inline BinaryConstraintOp toBinaryConstraintOp(const std::string& symbol) {
    if (symbol == "=") return BinaryConstraintOp::EQ;
    if (symbol == "!=") return BinaryConstraintOp::NE;
    if (symbol == "<") return BinaryConstraintOp::LT;
    if (symbol == "<=") return BinaryConstraintOp::LE;
    if (symbol == ">=") return BinaryConstraintOp::GE;
    if (symbol == ">") return BinaryConstraintOp::GT;
    if (symbol == "match") return BinaryConstraintOp::MATCH;
    if (symbol == "contains") return BinaryConstraintOp::CONTAINS;
    if (symbol == "not_match") return BinaryConstraintOp::NOT_MATCH;
    if (symbol == "not_contains") return BinaryConstraintOp::NOT_CONTAINS;

    fatal("unrecognised binary operator: symbol = `%s`", symbol);
}

/**
 * Determines whether arguments of constraint are orderable
 */
inline bool isOrderedBinaryConstraintOp(const BinaryConstraintOp op) {
    switch (op) {
        case BinaryConstraintOp::EQ:
        case BinaryConstraintOp::FEQ:
        case BinaryConstraintOp::NE:
        case BinaryConstraintOp::FNE:
        case BinaryConstraintOp::LT:
        case BinaryConstraintOp::ULT:
        case BinaryConstraintOp::FLT:
        case BinaryConstraintOp::LE:
        case BinaryConstraintOp::ULE:
        case BinaryConstraintOp::FLE:
        case BinaryConstraintOp::GE:
        case BinaryConstraintOp::UGE:
        case BinaryConstraintOp::FGE:
        case BinaryConstraintOp::GT:
        case BinaryConstraintOp::UGT:
        case BinaryConstraintOp::FGT:
        case BinaryConstraintOp::SLT:
        case BinaryConstraintOp::SLE:
        case BinaryConstraintOp::SGE:
        case BinaryConstraintOp::SGT: return true;

        case BinaryConstraintOp::MATCH:
        case BinaryConstraintOp::NOT_MATCH:
        case BinaryConstraintOp::CONTAINS:
        case BinaryConstraintOp::NOT_CONTAINS: return false;
    }

    UNREACHABLE_BAD_CASE_ANALYSIS
}

/**
 * Determines whether a functor should be written using infix notation (e.g. `a + b + c`)
 * or prefix notation (e.g. `+(a,b,c)`)
 */
inline bool isInfixFunctorOp(const BinaryConstraintOp op) {
    switch (op) {
        case BinaryConstraintOp::MATCH:
        case BinaryConstraintOp::NOT_MATCH:
        case BinaryConstraintOp::CONTAINS:
        case BinaryConstraintOp::NOT_CONTAINS: return false;

        default: return true;
    }
}

/**
 * Get type binary constraint operates on.
 **/
inline std::vector<TypeAttribute> getBinaryConstraintTypes(const BinaryConstraintOp op) {
    // clang-format off
#define COMPARE_EQUALS(op)                                                             \
    case BinaryConstraintOp::F##op: return { TypeAttribute::Float };                   \
    case BinaryConstraintOp::   op:                                                    \
        return { TypeAttribute::Signed, TypeAttribute::Unsigned, TypeAttribute::Float, \
                 TypeAttribute::Symbol, TypeAttribute::Record, TypeAttribute::ADT};
#define COMPARE_OP(op)                                                  \
    case BinaryConstraintOp::   op: return { TypeAttribute::Signed   }; \
    case BinaryConstraintOp::U##op: return { TypeAttribute::Unsigned }; \
    case BinaryConstraintOp::F##op: return { TypeAttribute::Float    }; \
    case BinaryConstraintOp::S##op: return { TypeAttribute::Symbol   };
    // clang-format on

    switch (op) {
        COMPARE_EQUALS(EQ)
        COMPARE_EQUALS(NE)
        COMPARE_OP(LT)
        COMPARE_OP(LE)
        COMPARE_OP(GT)
        COMPARE_OP(GE)

        case BinaryConstraintOp::MATCH:
        case BinaryConstraintOp::NOT_MATCH:
        case BinaryConstraintOp::CONTAINS:
        case BinaryConstraintOp::NOT_CONTAINS: return {TypeAttribute::Symbol};
    }

    UNREACHABLE_BAD_CASE_ANALYSIS

#undef COMPARE_EQUALS
#undef COMPARE_OP
}

}  // end of namespace souffle
