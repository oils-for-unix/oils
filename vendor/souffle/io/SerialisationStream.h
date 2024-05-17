/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020, The Souffle Developers. All rights reserved.
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SerialisationStream.h
 *
 * Defines a common base class for relation serialisation streams.
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/StringUtil.h"
#include "souffle/utility/json11.h"
#include <cassert>
#include <cstddef>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace souffle {

class RecordTable;
class SymbolTable;

using json11::Json;

template <bool readOnlyTables>
class SerialisationStream {
public:
    virtual ~SerialisationStream() = default;

protected:
    template <typename A>
    using RO = std::conditional_t<readOnlyTables, const A, A>;

    SerialisationStream(RO<SymbolTable>& symTab, RO<RecordTable>& recTab, Json types,
            std::vector<std::string> relTypes, std::size_t auxArity = 0)
            : symbolTable(symTab), recordTable(recTab), types(std::move(types)),
              typeAttributes(std::move(relTypes)), arity(typeAttributes.size() - auxArity),
              auxiliaryArity(auxArity) {}

    SerialisationStream(RO<SymbolTable>& symTab, RO<RecordTable>& recTab, Json types)
            : symbolTable(symTab), recordTable(recTab), types(std::move(types)) {
        setupFromJson();
    }

    SerialisationStream(RO<SymbolTable>& symTab, RO<RecordTable>& recTab,
            const std::map<std::string, std::string>& rwOperation)
            : symbolTable(symTab), recordTable(recTab) {
        std::string parseErrors;
        types = Json::parse(rwOperation.at("types"), parseErrors);
        assert(parseErrors.size() == 0 && "Internal JSON parsing failed.");
        if (rwOperation.count("params") > 0) {
            params = Json::parse(rwOperation.at("params"), parseErrors);
            assert(parseErrors.size() == 0 && "Internal JSON parsing failed.");
        } else {
            params = Json::object();
        }

        auxiliaryArity = RamSignedFromString(getOr(rwOperation, "auxArity", "0"));

        setupFromJson();
    }

    RO<SymbolTable>& symbolTable;
    RO<RecordTable>& recordTable;
    Json types;
    Json params;
    std::vector<std::string> typeAttributes;

    std::size_t arity = 0;
    std::size_t auxiliaryArity = 0;

private:
    void setupFromJson() {
        auto&& relInfo = types["relation"];
        arity = static_cast<std::size_t>(relInfo["arity"].long_value());

        assert(relInfo["types"].is_array());
        auto&& relTypes = relInfo["types"].array_items();
        assert(relTypes.size() == arity);

        for (const auto& jsonType : relTypes) {
            const auto& typeString = jsonType.string_value();
            assert(!typeString.empty() && "malformed types tag");
            typeAttributes.push_back(typeString);
        }

        for (std::size_t i = 0; i < auxiliaryArity; i++) {
            typeAttributes.push_back("i:number");
        }
    }
};

}  // namespace souffle
