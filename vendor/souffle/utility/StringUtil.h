/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file StringUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <typeinfo>
#include <vector>

namespace souffle {

// Forward declaration
inline bool isPrefix(const std::string& prefix, const std::string& element);

/**
 * Converts a string to a RamSigned
 *
 * This procedure has similar behaviour to std::stoi/stoll.
 *
 * The procedure accepts prefixes 0b (if base = 2) and 0x (if base = 16)
 * If base = 0, the procedure will try to infer the base from the prefix, if present.
 */
inline RamSigned RamSignedFromString(
        const std::string& str, std::size_t* position = nullptr, const int base = 10) {
    RamSigned val;

    if (base == 0) {
        if (isPrefix("-0b", str) || isPrefix("0b", str)) {
            return RamSignedFromString(str, position, 2);
        } else if (isPrefix("-0x", str) || isPrefix("0x", str)) {
            return RamSignedFromString(str, position, 16);
        } else {
            return RamSignedFromString(str, position);
        }
    }
    std::string binaryNumber;
    bool parsingBinary = base == 2;

    // stoi/stoll can't handle base 2 prefix by default.
    if (parsingBinary) {
        if (isPrefix("-0b", str)) {
            binaryNumber = "-" + str.substr(3);
        } else if (isPrefix("0b", str)) {
            binaryNumber = str.substr(2);
        }
    }
    const std::string& tmp = parsingBinary ? binaryNumber : str;

#if RAM_DOMAIN_SIZE == 64
    val = std::stoll(tmp, position, base);
#else
    val = std::stoi(tmp, position, base);
#endif

    if (parsingBinary && position != nullptr) {
        *position += 2;
    }

    return val;
}

/**
 * Converts a string to a RamFloat
 */
inline RamFloat RamFloatFromString(const std::string& str, std::size_t* position = nullptr) {
    RamFloat val;
#if RAM_DOMAIN_SIZE == 64
    val = std::stod(str, position);
#else
    val = std::stof(str, position);
#endif
    return static_cast<RamFloat>(val);
}
/**
 * Converts a string to a RamUnsigned
 *
 * This procedure has similar behaviour to std::stoul/stoull.
 *
 * The procedure accepts prefixes 0b (if base = 2) and 0x (if base = 16)
 * If base = 0, the procedure will try to infer the base from the prefix, if present.
 */
inline RamUnsigned RamUnsignedFromString(
        const std::string& str, std::size_t* position = nullptr, const int base = 10) {
    // Be default C++ (stoul) allows unsigned numbers starting with "-".
    if (isPrefix("-", str)) {
        throw std::invalid_argument("Unsigned number can't start with minus.");
    }

    if (base == 0) {
        if (isPrefix("0b", str)) {
            return RamUnsignedFromString(str, position, 2);
        } else if (isPrefix("0x", str)) {
            return RamUnsignedFromString(str, position, 16);
        } else {
            return RamUnsignedFromString(str, position);
        }
    }

    // stoul/stoull can't handle binary prefix by default.
    std::string binaryNumber;
    bool parsingBinary = false;
    if (base == 2 && isPrefix("0b", str)) {
        binaryNumber = str.substr(2);
        parsingBinary = true;
    }
    const std::string& tmp = parsingBinary ? binaryNumber : str;

    RamUnsigned val;
#if RAM_DOMAIN_SIZE == 64
    val = std::stoull(tmp, position, base);
#else
    val = std::stoul(tmp, position, base);
#endif

    if (parsingBinary && position != nullptr) {
        *position += 2;
    }

    // check if it's safe to cast (stoul returns unsigned long)
    if (val > std::numeric_limits<RamUnsigned>::max()) {
        throw std::invalid_argument("Unsigned number of of bounds");
    }

    return static_cast<RamUnsigned>(val);
}

/**
 * Can a string be parsed as RamSigned.
 *
 * Souffle (parser, not fact file readers) accepts: hex, binary and base 10.
 * Integer can be negative, in all 3 formats this means that it
 * starts with minus (c++ default semantics).
 */
inline bool canBeParsedAsRamSigned(const std::string& string) {
    std::size_t charactersRead = 0;

    try {
        RamSignedFromString(string, &charactersRead, 0);
    } catch (...) {
        return false;
    }

    return charactersRead == string.size();
}

/**
 * Can a string be parsed as RamUnsigned.
 *
 * Souffle accepts: hex, binary and base 10.
 */
inline bool canBeParsedAsRamUnsigned(const std::string& string) {
    std::size_t charactersRead = 0;
    try {
        RamUnsignedFromString(string, &charactersRead, 0);
    } catch (...) {
        return false;
    }
    return charactersRead == string.size();
}

/**
 * Can a string be parsed as RamFloat.
 */
inline bool canBeParsedAsRamFloat(const std::string& string) {
    std::size_t charactersRead = 0;
    try {
        RamFloatFromString(string, &charactersRead);
    } catch (...) {
        return false;
    }
    return charactersRead == string.size();
}

#if RAM_DOMAIN_SIZE == 64
inline RamDomain stord(const std::string& str, std::size_t* pos = nullptr, int base = 10) {
    return static_cast<RamDomain>(std::stoull(str, pos, base));
}
#elif RAM_DOMAIN_SIZE == 32
inline RamDomain stord(const std::string& str, std::size_t* pos = nullptr, int base = 10) {
    return static_cast<RamDomain>(std::stoul(str, pos, base));
}
#else
#error RAM Domain is neither 32bit nor 64bit
#endif

/**
 * Check whether a string is a sequence of digits
 */
inline bool isNumber(const char* str) {
    if (str == nullptr) {
        return false;
    }

    while (*str != 0) {
        if (isdigit(*str) == 0) {
            return false;
        }
        str++;
    }
    return true;
}

/**
 * A generic function converting strings into strings (trivial case).
 */
inline const std::string& toString(const std::string& str) {
    return str;
}

namespace detail {

/**
 * A type trait to check whether a given type is printable.
 * In this general case, nothing is printable.
 */
template <typename T, typename filter = void>
struct is_printable : public std::false_type {};

/**
 * A type trait to check whether a given type is printable.
 * This specialization makes types with an output operator printable.
 */
template <typename T>
struct is_printable<T, typename std::conditional<false,
                               decltype(std::declval<std::ostream&>() << std::declval<T>()), void>::type>
        : public std::true_type {};

template <typename T, typename filter = void>
struct is_html_printable : public std::false_type {};

template <typename T>
struct is_html_printable<T,
        typename std::conditional<false, decltype(std::declval<T>().printHTML(std::declval<std::ostream&>())),
                void>::type> : public std::true_type {};

}  // namespace detail

/**
 * A generic function converting arbitrary objects to strings by utilizing
 * their print capability.
 *
 * This function is mainly intended for implementing test cases and debugging
 * operations.
 */
template <typename T>
typename std::enable_if<detail::is_printable<T>::value, std::string>::type toString(const T& value) {
    // write value into stream and return result
    std::stringstream ss;
    ss << value;
    return ss.str();
}

/**
 * A fallback for the to-string function in case an unprintable object is supposed
 * to be printed.
 */
template <typename T>
typename std::enable_if<!detail::is_printable<T>::value, std::string>::type toString(const T&) {
    std::stringstream ss;
    ss << "(print for type ";
    ss << typeid(T).name();
    ss << " not supported)";
    return ss.str();
}

template <typename T>
auto toHtml(const T& obj) -> typename std::enable_if<detail::is_html_printable<T>::value, std::string>::type {
    std::stringstream out;
    obj.printHTML(out);
    return out.str();
}

/** Fallback to `toString` */
template <typename T>
auto toHtml(const T& obj) ->
        typename std::enable_if<not detail::is_html_printable<T>::value, std::string>::type {
    return toString(obj);
}

// -------------------------------------------------------------------------------
//                              String Utils
// -------------------------------------------------------------------------------

/**
 * Determine if one string is a prefix of another
 */
inline bool isPrefix(const std::string& prefix, const std::string& element) {
    auto itPrefix = prefix.begin();
    auto itElement = element.begin();

    while (itPrefix != prefix.end() && itElement != element.end()) {
        if (*itPrefix != *itElement) {
            break;
        }
        ++itPrefix;
        ++itElement;
    }

    return itPrefix == prefix.end();
}

/**
 * Determines whether the given value string ends with the given
 * end string.
 */
inline bool endsWith(const std::string& value, const std::string& ending) {
    if (value.size() < ending.size()) {
        return false;
    }
    return std::equal(ending.rbegin(), ending.rend(), value.rbegin());
}

/**
 * Splits a string given a delimiter
 */
inline std::vector<std::string_view> splitView(std::string_view toSplit, std::string_view delimiter) {
    if (toSplit.empty()) return {toSplit};

    auto delimLen = std::max<size_t>(1, delimiter.size());  // ensure we advance even w/ an empty needle

    std::vector<std::string_view> parts;
    for (auto tail = toSplit;;) {
        auto pos = tail.find(delimiter);
        parts.push_back(tail.substr(0, pos));
        if (pos == tail.npos) break;

        tail = tail.substr(pos + delimLen);
    }

    return parts;
}

/**
 * Splits a string given a delimiter
 */
inline std::vector<std::string> splitString(std::string_view str, char delimiter) {
    std::vector<std::string> xs;
    for (auto&& x : splitView(str, std::string_view{&delimiter, 1}))
        xs.push_back(std::string(x));
    return xs;
}

/**
 * Strips the prefix of a given string if it exists. No change otherwise.
 */
inline std::string stripPrefix(const std::string& prefix, const std::string& element) {
    return isPrefix(prefix, element) ? element.substr(prefix.length()) : element;
}

/**
 * Stringify a string using escapes for escape, newline, tab, double-quotes and semicolons
 */
inline std::string stringify(const std::string& input) {
    std::string str(input);

    // replace escapes with double escape sequence
    std::size_t start_pos = 0;
    while ((start_pos = str.find('\\', start_pos)) != std::string::npos) {
        str.replace(start_pos, 1, "\\\\");
        start_pos += 2;
    }
    // replace semicolons with escape sequence
    start_pos = 0;
    while ((start_pos = str.find(';', start_pos)) != std::string::npos) {
        str.replace(start_pos, 1, "\\;");
        start_pos += 2;
    }
    // replace double-quotes with escape sequence
    start_pos = 0;
    while ((start_pos = str.find('"', start_pos)) != std::string::npos) {
        str.replace(start_pos, 1, "\\\"");
        start_pos += 2;
    }
    // replace newline with escape sequence
    start_pos = 0;
    while ((start_pos = str.find('\n', start_pos)) != std::string::npos) {
        str.replace(start_pos, 1, "\\n");
        start_pos += 2;
    }
    // replace tab with escape sequence
    start_pos = 0;
    while ((start_pos = str.find('\t', start_pos)) != std::string::npos) {
        str.replace(start_pos, 1, "\\t");
        start_pos += 2;
    }
    return str;
}

/**
 * Escape JSON string.
 */
inline std::string escapeJSONstring(const std::string& JSONstr) {
    std::ostringstream destination;

    // Iterate over all characters except first and last
    for (char c : JSONstr) {
        if (c == '\"') {
            destination << "\\";
        }
        destination << c;
    }
    return destination.str();
}

/** Valid C++ identifier, note that this does not ensure the uniqueness of identifiers returned. */
inline std::string identifier(std::string id) {
    for (std::size_t i = 0; i < id.length(); i++) {
        if (((isalpha(id[i]) == 0) && i == 0) || ((isalnum(id[i]) == 0) && id[i] != '_')) {
            id[i] = '_';
        }
    }
    return id;
}

// TODO (b-scholz): tidy up unescape/escape functions

inline std::string unescape(
        const std::string& inputString, const std::string& needle, const std::string& replacement) {
    std::string result = inputString;
    std::size_t pos = 0;
    while ((pos = result.find(needle, pos)) != std::string::npos) {
        result = result.replace(pos, needle.length(), replacement);
        pos += replacement.length();
    }
    return result;
}

inline std::string unescape(const std::string& inputString) {
    std::string unescaped = unescape(inputString, "\\\"", "\"");
    unescaped = unescape(unescaped, "\\t", "\t");
    unescaped = unescape(unescaped, "\\r", "\r");
    unescaped = unescape(unescaped, "\\n", "\n");
    return unescaped;
}

inline std::string escape(
        const std::string& inputString, const std::string& needle, const std::string& replacement) {
    std::string result = inputString;
    std::size_t pos = 0;
    while ((pos = result.find(needle, pos)) != std::string::npos) {
        result = result.replace(pos, needle.length(), replacement);
        pos += replacement.length();
    }
    return result;
}

inline std::string escape(const std::string& inputString) {
    std::string escaped = escape(inputString, "\"", "\\\"");
    escaped = escape(escaped, "\t", "\\t");
    escaped = escape(escaped, "\r", "\\r");
    escaped = escape(escaped, "\n", "\\n");
    return escaped;
}

template <typename C>
auto escape(C&& os, std::string_view str, std::set<char> const& needs_escape, std::string_view esc) {
    for (auto&& x : str) {
        if (needs_escape.find(x) != needs_escape.end()) {
            os << esc;
        }
        os << x;
    }

    return std::forward<C>(os);
}

inline std::string escape(std::string_view str, std::set<char> const& needs_escape, std::string_view esc) {
    return escape(std::stringstream{}, str, needs_escape, esc).str();
}

}  // end namespace souffle
