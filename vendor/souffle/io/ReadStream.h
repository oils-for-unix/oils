/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ReadStream.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/SerialisationStream.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StringUtil.h"
#include "souffle/utility/json11.h"
#include <cctype>
#include <cstddef>
#include <map>
#include <memory>
#include <ostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace souffle {

class ReadStream : public SerialisationStream<false> {
protected:
    ReadStream(
            const std::map<std::string, std::string>& rwOperation, SymbolTable& symTab, RecordTable& recTab)
            : SerialisationStream(symTab, recTab, rwOperation) {}

public:
    template <typename T>
    void readAll(T& relation) {
        while (const auto next = readNextTuple()) {
            const RamDomain* ramDomain = next.get();
            relation.insert(ramDomain);
        }
    }

protected:
    /**
     * Read a record from a string.
     *
     * @param source - string containing a record
     * @param recordTypeName - record type.
     * @parem pos - start parsing from this position.
     * @param consumed - if not nullptr: number of characters read.
     *
     */
    RamDomain readRecord(const std::string& source, const std::string& recordTypeName, std::size_t pos = 0,
            std::size_t* charactersRead = nullptr) {
        const std::size_t initial_position = pos;

        // Check if record type information are present
        auto&& recordInfo = types["records"][recordTypeName];
        if (recordInfo.is_null()) {
            throw std::invalid_argument("Missing record type information: " + recordTypeName);
        }

        // Handle nil case
        consumeWhiteSpace(source, pos);
        if (source.substr(pos, 3) == "nil") {
            if (charactersRead != nullptr) {
                *charactersRead = 3;
            }
            return 0;
        }

        auto&& recordTypes = recordInfo["types"];
        const std::size_t recordArity = recordInfo["arity"].long_value();

        std::vector<RamDomain> recordValues(recordArity);

        consumeChar(source, '[', pos);

        for (std::size_t i = 0; i < recordArity; ++i) {
            const std::string& recordType = recordTypes[i].string_value();
            std::size_t consumed = 0;

            if (i > 0) {
                consumeChar(source, ',', pos);
            }
            consumeWhiteSpace(source, pos);
            switch (recordType[0]) {
                case 's': {
                    recordValues[i] = symbolTable.encode(readSymbol(source, ",]", pos, &consumed));
                    break;
                }
                case 'i': {
                    recordValues[i] = RamSignedFromString(source.substr(pos), &consumed);
                    break;
                }
                case 'u': {
                    recordValues[i] = ramBitCast(RamUnsignedFromString(source.substr(pos), &consumed));
                    break;
                }
                case 'f': {
                    recordValues[i] = ramBitCast(RamFloatFromString(source.substr(pos), &consumed));
                    break;
                }
                case 'r': {
                    recordValues[i] = readRecord(source, recordType, pos, &consumed);
                    break;
                }
                case '+': {
                    recordValues[i] = readADT(source, recordType, pos, &consumed);
                    break;
                }
                default: fatal("Invalid type attribute");
            }
            pos += consumed;
        }
        consumeChar(source, ']', pos);

        if (charactersRead != nullptr) {
            *charactersRead = pos - initial_position;
        }

        return recordTable.pack(recordValues.data(), recordValues.size());
    }

    RamDomain readADT(const std::string& source, const std::string& adtName, std::size_t pos = 0,
            std::size_t* charactersRead = nullptr) {
        const std::size_t initial_position = pos;

        // Branch will are encoded as one of the:
        // [branchIdx, [branchValues...]]
        // [branchIdx, branchValue]
        // branchIdx
        RamDomain branchIdx = -1;

        auto&& adtInfo = types["ADTs"][adtName];
        const auto& branches = adtInfo["branches"];

        if (adtInfo.is_null() || !branches.is_array()) {
            throw std::invalid_argument("Missing ADT information: " + adtName);
        }

        // Consume initial character
        consumeChar(source, '$', pos);
        std::string constructor = readQualifiedName(source, pos);

        json11::Json branchInfo = [&]() -> json11::Json {
            for (auto branch : branches.array_items()) {
                ++branchIdx;

                if (branch["name"].string_value() == constructor) {
                    return branch;
                }
            }

            throw std::invalid_argument("Missing branch information: " + constructor);
        }();

        assert(branchInfo["types"].is_array());
        auto branchTypes = branchInfo["types"].array_items();

        // Handle a branch without arguments.
        if (branchTypes.empty()) {
            if (charactersRead != nullptr) {
                *charactersRead = pos - initial_position;
            }

            if (adtInfo["enum"].bool_value()) {
                return branchIdx;
            }

            RamDomain emptyArgs = recordTable.pack(toVector<RamDomain>().data(), 0);
            const RamDomain record[] = {branchIdx, emptyArgs};
            return recordTable.pack(record, 2);
        }

        consumeChar(source, '(', pos);

        std::vector<RamDomain> branchArgs(branchTypes.size());

        for (std::size_t i = 0; i < branchTypes.size(); ++i) {
            auto argType = branchTypes[i].string_value();
            assert(!argType.empty());

            std::size_t consumed = 0;

            if (i > 0) {
                consumeChar(source, ',', pos);
            }
            consumeWhiteSpace(source, pos);

            switch (argType[0]) {
                case 's': {
                    branchArgs[i] = symbolTable.encode(readSymbol(source, ",)", pos, &consumed));
                    break;
                }
                case 'i': {
                    branchArgs[i] = RamSignedFromString(source.substr(pos), &consumed);
                    break;
                }
                case 'u': {
                    branchArgs[i] = ramBitCast(RamUnsignedFromString(source.substr(pos), &consumed));
                    break;
                }
                case 'f': {
                    branchArgs[i] = ramBitCast(RamFloatFromString(source.substr(pos), &consumed));
                    break;
                }
                case 'r': {
                    branchArgs[i] = readRecord(source, argType, pos, &consumed);
                    break;
                }
                case '+': {
                    branchArgs[i] = readADT(source, argType, pos, &consumed);
                    break;
                }
                default: fatal("Invalid type attribute");
            }
            pos += consumed;
        }

        consumeChar(source, ')', pos);

        if (charactersRead != nullptr) {
            *charactersRead = pos - initial_position;
        }

        // Store branch either as [branch_id, [arguments]] or [branch_id, argument].
        RamDomain branchValue = [&]() -> RamDomain {
            if (branchArgs.size() != 1) {
                return recordTable.pack(branchArgs.data(), branchArgs.size());
            } else {
                return branchArgs[0];
            }
        }();

        RamDomain rec[2] = {branchIdx, branchValue};
        return recordTable.pack(rec, 2);
    }

    /**
     * Read the next alphanumeric + ('_', '?') sequence (corresponding to IDENT).
     * Consume preceding whitespace.
     * TODO (darth_tytus): use std::string_view?
     */
    std::string readQualifiedName(const std::string& source, std::size_t& pos) {
        consumeWhiteSpace(source, pos);
        if (pos >= source.length()) {
            throw std::invalid_argument("Unexpected end of input");
        }

        const std::size_t bgn = pos;
        while (pos < source.length()) {
            unsigned char ch = static_cast<unsigned char>(source[pos]);
            bool valid = std::isalnum(ch) || ch == '_' || ch == '?' || ch == '.';
            if (!valid) break;
            ++pos;
        }

        return source.substr(bgn, pos - bgn);
    }

    std::string readUntil(const std::string& source, const std::string& stopChars, const std::size_t pos,
            std::size_t* charactersRead) {
        std::size_t endOfSymbol = source.find_first_of(stopChars, pos);

        if (endOfSymbol == std::string::npos) {
            throw std::invalid_argument("Unexpected end of input");
        }

        *charactersRead = endOfSymbol - pos;

        return source.substr(pos, *charactersRead);
    }

    std::string readQuotedSymbol(const std::string& source, std::size_t pos, std::size_t* charactersRead) {
        const std::size_t start = pos;
        const std::size_t end = source.length();

        const char quoteMark = source[pos];
        ++pos;

        const std::size_t startOfSymbol = pos;
        std::size_t endOfSymbol = std::string::npos;
        bool hasEscaped = false;

        bool escaped = false;
        while (pos < end) {
            if (escaped) {
                hasEscaped = true;
                escaped = false;
                ++pos;
                continue;
            }

            const char c = source[pos];
            if (c == quoteMark) {
                endOfSymbol = pos;
                ++pos;
                break;
            }
            if (c == '\\') {
                escaped = true;
            }
            ++pos;
        }

        if (endOfSymbol == std::string::npos) {
            throw std::invalid_argument("Unexpected end of input");
        }

        *charactersRead = pos - start;

        std::size_t lengthOfSymbol = endOfSymbol - startOfSymbol;

        // fast handling of symbol without escape sequence
        if (!hasEscaped) {
            return source.substr(startOfSymbol, lengthOfSymbol);
        } else {
            // slow handling of symbol with escape sequence
            std::string symbol;
            symbol.reserve(lengthOfSymbol);
            bool escaped = false;
            for (std::size_t pos = startOfSymbol; pos < endOfSymbol; ++pos) {
                char ch = source[pos];
                if (escaped || ch != '\\') {
                    symbol.push_back(ch);
                    escaped = false;
                } else {
                    escaped = true;
                }
            }
            return symbol;
        }
    }

    /**
     * Read the next symbol.
     * It is either a double-quoted symbol with backslash-escaped chars, or the
     * longuest sequence that do not contains any of the given stopChars.
     * */
    std::string readSymbol(const std::string& source, const std::string& stopChars, const std::size_t pos,
            std::size_t* charactersRead) {
        if (source[pos] == '"') {
            return readQuotedSymbol(source, pos, charactersRead);
        } else {
            return readUntil(source, stopChars, pos, charactersRead);
        }
    }

    /**
     * Read past given character, consuming any preceding whitespace.
     */
    void consumeChar(const std::string& str, char c, std::size_t& pos) {
        consumeWhiteSpace(str, pos);
        if (pos >= str.length()) {
            throw std::invalid_argument("Unexpected end of input");
        }
        if (str[pos] != c) {
            std::stringstream error;
            error << "Expected: \'" << c << "\', got: " << str[pos];
            throw std::invalid_argument(error.str());
        }
        ++pos;
    }

    /**
     * Advance position in the string until first non-whitespace character.
     */
    void consumeWhiteSpace(const std::string& str, std::size_t& pos) {
        while (pos < str.length() && std::isspace(static_cast<unsigned char>(str[pos]))) {
            ++pos;
        }
    }

    virtual Own<RamDomain[]> readNextTuple() = 0;
};

class ReadStreamFactory {
public:
    virtual Own<ReadStream> getReader(
            const std::map<std::string, std::string>&, SymbolTable&, RecordTable&) = 0;
    virtual const std::string& getName() const = 0;
    virtual ~ReadStreamFactory() = default;
};

} /* namespace souffle */
