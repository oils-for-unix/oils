/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file WriteStream.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/SerialisationStream.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/json11.h"
#include <cassert>
#include <cstddef>
#include <iomanip>
#include <map>
#include <memory>
#include <ostream>
#include <string>

namespace souffle {

using json11::Json;

class WriteStream : public SerialisationStream<true> {
public:
    WriteStream(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : SerialisationStream(symbolTable, recordTable, rwOperation),
              summary(rwOperation.at("IO") == "stdoutprintsize") {}

    template <typename T>
    void writeAll(const T& relation) {
        if (summary) {
            return writeSize(relation.size());
        }
        if (arity == 0) {
            if (relation.begin() != relation.end()) {
                writeNullary();
            }
            return;
        }
        for (const auto& current : relation) {
            writeNext(current);
        }
    }

    template <typename T>
    void writeSize(const T& relation) {
        writeSize(relation.size());
    }

protected:
    const bool summary;

    virtual void writeNullary() = 0;
    virtual void writeNextTuple(const RamDomain* tuple) = 0;
    virtual void writeSize(std::size_t) {
        fatal("attempting to print size of a write operation");
    }

    template <typename Tuple>
    void writeNext(const Tuple tuple) {
        using tcb::make_span;
        writeNextTuple(make_span(tuple).data());
    }

    virtual void outputSymbol(std::ostream& destination, const std::string& value) {
        destination << value;
    }

    void outputRecord(std::ostream& destination, const RamDomain value, const std::string& name) {
        auto&& recordInfo = types["records"][name];

        // Check if record type information are present
        assert(!recordInfo.is_null() && "Missing record type information");

        // Check for nil
        if (value == 0) {
            destination << "nil";
            return;
        }

        auto&& recordTypes = recordInfo["types"];
        const std::size_t recordArity = recordInfo["arity"].long_value();

        const RamDomain* tuplePtr = recordTable.unpack(value, recordArity);

        destination << "[";

        // print record's elements
        for (std::size_t i = 0; i < recordArity; ++i) {
            if (i > 0) {
                destination << ", ";
            }

            const std::string& recordType = recordTypes[i].string_value();
            const RamDomain recordValue = tuplePtr[i];

            switch (recordType[0]) {
                case 'i': destination << recordValue; break;
                case 'f': destination << ramBitCast<RamFloat>(recordValue); break;
                case 'u': destination << ramBitCast<RamUnsigned>(recordValue); break;
                case 's': outputSymbol(destination, symbolTable.decode(recordValue)); break;
                case 'r': outputRecord(destination, recordValue, recordType); break;
                case '+': outputADT(destination, recordValue, recordType); break;
                default: fatal("Unsupported type attribute: `%c`", recordType[0]);
            }
        }
        destination << "]";
    }

    void outputADT(std::ostream& destination, const RamDomain value, const std::string& name) {
        auto&& adtInfo = types["ADTs"][name];

        assert(!adtInfo.is_null() && "Missing adt type information");
        assert(adtInfo["arity"].long_value() > 0);

        // adt is encoded in one of three possible ways:
        // [branchID, [branch_args]] when |branch_args| != 1
        // [branchID, arg] when a branch takes a single argument.
        // branchID when ADT is an enumeration.
        bool isEnum = adtInfo["enum"].bool_value();

        RamDomain branchId = value;
        const RamDomain* branchArgs = nullptr;
        json11::Json branchInfo;
        json11::Json::array branchTypes;

        if (!isEnum) {
            const RamDomain* tuplePtr = recordTable.unpack(value, 2);

            branchId = tuplePtr[0];
            branchInfo = adtInfo["branches"][branchId];
            branchTypes = branchInfo["types"].array_items();

            // Prepare branch's arguments for output.
            branchArgs = [&]() -> const RamDomain* {
                if (branchTypes.size() > 1) {
                    return recordTable.unpack(tuplePtr[1], branchTypes.size());
                } else {
                    return &tuplePtr[1];
                }
            }();
        } else {
            branchInfo = adtInfo["branches"][branchId];
            branchTypes = branchInfo["types"].array_items();
        }

        destination << "$" << branchInfo["name"].string_value();

        if (branchTypes.size() > 0) {
            destination << "(";
        }

        // Print arguments
        for (std::size_t i = 0; i < branchTypes.size(); ++i) {
            if (i > 0) {
                destination << ", ";
            }

            auto argType = branchTypes[i].string_value();
            switch (argType[0]) {
                case 'i': destination << branchArgs[i]; break;
                case 'f': destination << ramBitCast<RamFloat>(branchArgs[i]); break;
                case 'u': destination << ramBitCast<RamUnsigned>(branchArgs[i]); break;
                case 's': outputSymbol(destination, symbolTable.decode(branchArgs[i])); break;
                case 'r': outputRecord(destination, branchArgs[i], argType); break;
                case '+': outputADT(destination, branchArgs[i], argType); break;
                default: fatal("Unsupported type attribute: `%c`", argType[0]);
            }
        }

        if (branchTypes.size() > 0) {
            destination << ")";
        }
    }
};

class WriteStreamFactory {
public:
    virtual Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) = 0;

    virtual const std::string& getName() const = 0;
    virtual ~WriteStreamFactory() = default;
};

template <>
inline void WriteStream::writeNext(const RamDomain* tuple) {
    writeNextTuple(tuple);
}

} /* namespace souffle */
