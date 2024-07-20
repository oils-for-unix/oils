/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2020, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ReadStreamJSON.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/ReadStream.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/FileUtil.h"
#include "souffle/utility/StringUtil.h"

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <queue>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace souffle {

template <typename... T>
[[noreturn]] static void throwError(T const&... t) {
    std::ostringstream out;
    (out << ... << t);
    throw std::runtime_error(out.str());
}

class ReadStreamJSON : public ReadStream {
public:
    ReadStreamJSON(std::istream& file, const std::map<std::string, std::string>& rwOperation,
            SymbolTable& symbolTable, RecordTable& recordTable)
            : ReadStream(rwOperation, symbolTable, recordTable), file(file), pos(0), isInitialized(false) {
        std::string err;
        params = Json::parse(rwOperation.at("params"), err);
        if (err.length() > 0) {
            throwError("cannot get internal params: ", err);
        }
    }

protected:
    std::istream& file;
    std::size_t pos;
    Json jsonSource;
    Json params;
    bool isInitialized;
    bool useObjects;
    std::map<const std::string, const std::size_t> paramIndex;

    Own<RamDomain[]> readNextTuple() override {
        // for some reasons we cannot initalized our json objects in constructor
        // otherwise it will segfault, so we initialize in the first call
        if (!isInitialized) {
            isInitialized = true;
            std::string error = "";
            std::string source(std::istreambuf_iterator<char>(file), {});

            jsonSource = Json::parse(source, error);
            // it should be wrapped by an extra array
            if (error.length() > 0 || !jsonSource.is_array()) {
                throwError("cannot deserialize json because ", error, ":\n", source);
            }

            if (jsonSource.array_items().empty()) {
                // No tuples defined
                return nullptr;
            }

            // we only check the first one, since there are extra checks
            // in readNextTupleObject/readNextTupleList
            if (jsonSource[0].is_array()) {
                useObjects = false;
            } else if (jsonSource[0].is_object()) {
                useObjects = true;
                std::size_t index_pos = 0;
                for (auto param : params["relation"]["params"].array_items()) {
                    paramIndex.insert(std::make_pair(param.string_value(), index_pos));
                    index_pos++;
                }
            } else {
                throwError("the input is neither list nor object format");
            }
        }

        if (useObjects) {
            return readNextTupleObject();
        } else {
            return readNextTupleList();
        }
    }

    Own<RamDomain[]> readNextTupleList() {
        if (pos >= jsonSource.array_items().size()) {
            return nullptr;
        }

        Own<RamDomain[]> tuple = mk<RamDomain[]>(typeAttributes.size());
        const Json& jsonObj = jsonSource[pos];
        assert(jsonObj.is_array() && "the input is not json array");
        pos++;
        for (std::size_t i = 0; i < typeAttributes.size(); ++i) {
            try {
                auto&& ty = typeAttributes.at(i);
                switch (ty[0]) {
                    case 's': {
                        tuple[i] = symbolTable.encode(jsonObj[i].string_value());
                        break;
                    }
                    case 'r': {
                        tuple[i] = readNextElementList(jsonObj[i], ty);
                        break;
                    }
                    case 'i': {
                        tuple[i] = jsonObj[i].int_value();
                        break;
                    }
                    case 'u': {
                        tuple[i] = jsonObj[i].int_value();
                        break;
                    }
                    case 'f': {
                        tuple[i] = static_cast<RamDomain>(jsonObj[i].number_value());
                        break;
                    }
                    default: throwError("invalid type attribute: '", ty[0], "'");
                }
            } catch (...) {
                std::stringstream errorMessage;
                if (jsonObj.is_array() && i < jsonObj.array_items().size()) {
                    errorMessage << "Error converting: " << jsonObj[i].dump();
                } else {
                    errorMessage << "Invalid index: " << i;
                }
                throw std::invalid_argument(errorMessage.str());
            }
        }

        return tuple;
    }

    RamDomain readNextElementList(const Json& source, const std::string& recordTypeName) {
        auto&& recordInfo = types["records"][recordTypeName];

        if (recordInfo.is_null()) {
            throw std::invalid_argument("Missing record type information: " + recordTypeName);
        }

        // Handle null case
        if (source.is_null()) {
            return 0;
        }

        assert(source.is_array() && "the input is not json array");
        auto&& recordTypes = recordInfo["types"];
        const std::size_t recordArity = recordInfo["arity"].long_value();
        std::vector<RamDomain> recordValues(recordArity);
        for (std::size_t i = 0; i < recordArity; ++i) {
            const std::string& recordType = recordTypes[i].string_value();
            switch (recordType[0]) {
                case 's': {
                    recordValues[i] = symbolTable.encode(source[i].string_value());
                    break;
                }
                case 'r': {
                    recordValues[i] = readNextElementList(source[i], recordType);
                    break;
                }
                case 'i': {
                    recordValues[i] = source[i].int_value();
                    break;
                }
                case 'u': {
                    recordValues[i] = source[i].int_value();
                    break;
                }
                case 'f': {
                    recordValues[i] = static_cast<RamDomain>(source[i].number_value());
                    break;
                }
                default: throwError("invalid type attribute");
            }
        }

        return recordTable.pack(recordValues.data(), recordValues.size());
    }

    Own<RamDomain[]> readNextTupleObject() {
        if (pos >= jsonSource.array_items().size()) {
            return nullptr;
        }

        Own<RamDomain[]> tuple = mk<RamDomain[]>(typeAttributes.size());
        const Json& jsonObj = jsonSource[pos];
        assert(jsonObj.is_object() && "the input is not json object");
        pos++;
        for (auto p : jsonObj.object_items()) {
            try {
                // get the corresponding position by parameter name
                if (paramIndex.find(p.first) == paramIndex.end()) {
                    throwError("invalid parameter: ", p.first);
                }
                std::size_t i = paramIndex.at(p.first);
                auto&& ty = typeAttributes.at(i);
                switch (ty[0]) {
                    case 's': {
                        tuple[i] = symbolTable.encode(p.second.string_value());
                        break;
                    }
                    case 'r': {
                        tuple[i] = readNextElementObject(p.second, ty);
                        break;
                    }
                    case 'i': {
                        tuple[i] = p.second.int_value();
                        break;
                    }
                    case 'u': {
                        tuple[i] = p.second.int_value();
                        break;
                    }
                    case 'f': {
                        tuple[i] = static_cast<RamDomain>(p.second.number_value());
                        break;
                    }
                    default: throwError("invalid type attribute: '", ty[0], "'");
                }
            } catch (...) {
                std::stringstream errorMessage;
                errorMessage << "Error converting: " << p.second.dump();
                throw std::invalid_argument(errorMessage.str());
            }
        }

        return tuple;
    }

    RamDomain readNextElementObject(const Json& source, const std::string& recordTypeName) {
        auto&& recordInfo = types["records"][recordTypeName];
        const std::string recordName = recordTypeName.substr(2);
        std::map<const std::string, const std::size_t> recordIndex;

        std::size_t index_pos = 0;
        for (auto param : params["records"][recordName]["params"].array_items()) {
            recordIndex.insert(std::make_pair(param.string_value(), index_pos));
            index_pos++;
        }

        if (recordInfo.is_null()) {
            throw std::invalid_argument("Missing record type information: " + recordTypeName);
        }

        // Handle null case
        if (source.is_null()) {
            return 0;
        }

        assert(source.is_object() && "the input is not json object");
        auto&& recordTypes = recordInfo["types"];
        const std::size_t recordArity = recordInfo["arity"].long_value();
        std::vector<RamDomain> recordValues(recordArity);
        recordValues.reserve(recordIndex.size());
        for (auto readParam : source.object_items()) {
            // get the corresponding position by parameter name
            if (recordIndex.find(readParam.first) == recordIndex.end()) {
                throwError("invalid parameter: ", readParam.first);
            }
            std::size_t i = recordIndex.at(readParam.first);
            auto&& type = recordTypes[i].string_value();
            switch (type[0]) {
                case 's': {
                    recordValues[i] = symbolTable.encode(readParam.second.string_value());
                    break;
                }
                case 'r': {
                    recordValues[i] = readNextElementObject(readParam.second, type);
                    break;
                }
                case 'i': {
                    recordValues[i] = readParam.second.int_value();
                    break;
                }
                case 'u': {
                    recordValues[i] = readParam.second.int_value();
                    break;
                }
                case 'f': {
                    recordValues[i] = static_cast<RamDomain>(readParam.second.number_value());
                    break;
                }
                default: throwError("invalid type attribute: '", type[0], "'");
            }
        }

        return recordTable.pack(recordValues.data(), recordValues.size());
    }
};

class ReadFileJSON : public ReadStreamJSON {
public:
    ReadFileJSON(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable)
            // FIXME: This is bordering on UB - we're passing an unconstructed
            // object (fileHandle) to the base class
            : ReadStreamJSON(fileHandle, rwOperation, symbolTable, recordTable),
              baseName(souffle::baseName(getFileName(rwOperation))),
              fileHandle(getFileName(rwOperation), std::ios::in | std::ios::binary) {
        if (!fileHandle.is_open()) {
            throw std::invalid_argument("Cannot open json file " + baseName + "\n");
        }
    }

    ~ReadFileJSON() override = default;

protected:
    /**
     * Return given filename or construct from relation name.
     * Default name is [configured path]/[relation name].json
     *
     * @param rwOperation map of IO configuration options
     * @return input filename
     */
    static std::string getFileName(const std::map<std::string, std::string>& rwOperation) {
        auto name = getOr(rwOperation, "filename", rwOperation.at("name") + ".json");
        if (name.front() != '/') {
            name = getOr(rwOperation, "fact-dir", ".") + "/" + name;
        }
        return name;
    }

    std::string baseName;
    std::ifstream fileHandle;
};

class ReadCinJSONFactory : public ReadStreamFactory {
public:
    Own<ReadStream> getReader(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable) override {
        return mk<ReadStreamJSON>(std::cin, rwOperation, symbolTable, recordTable);
    }

    const std::string& getName() const override {
        static const std::string name = "json";
        return name;
    }
    ~ReadCinJSONFactory() override = default;
};

class ReadFileJSONFactory : public ReadStreamFactory {
public:
    Own<ReadStream> getReader(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable) override {
        return mk<ReadFileJSON>(rwOperation, symbolTable, recordTable);
    }

    const std::string& getName() const override {
        static const std::string name = "jsonfile";
        return name;
    }

    ~ReadFileJSONFactory() override = default;
};
}  // namespace souffle
