/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file IOSystem.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/ReadStream.h"
#include "souffle/io/ReadStreamCSV.h"
#include "souffle/io/ReadStreamJSON.h"
#include "souffle/io/WriteStream.h"
#include "souffle/io/WriteStreamCSV.h"
#include "souffle/io/WriteStreamJSON.h"

#ifdef USE_SQLITE
#include "souffle/io/ReadStreamSQLite.h"
#include "souffle/io/WriteStreamSQLite.h"
#endif

#include <map>
#include <memory>
#include <stdexcept>
#include <string>

namespace souffle {

class IOSystem {
public:
    static IOSystem& getInstance() {
        static IOSystem singleton;
        return singleton;
    }

    void registerWriteStreamFactory(const std::shared_ptr<WriteStreamFactory>& factory) {
        outputFactories[factory->getName()] = factory;
    }

    void registerReadStreamFactory(const std::shared_ptr<ReadStreamFactory>& factory) {
        inputFactories[factory->getName()] = factory;
    }

    /**
     * Return a new WriteStream
     */
    Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) const {
        std::string ioType = rwOperation.at("IO");
        if (outputFactories.count(ioType) == 0) {
            throw std::invalid_argument("Requested output type <" + ioType + "> is not supported.");
        }
        return outputFactories.at(ioType)->getWriter(rwOperation, symbolTable, recordTable);
    }
    /**
     * Return a new ReadStream
     */
    Own<ReadStream> getReader(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable) const {
        std::string ioType = rwOperation.at("IO");
        if (inputFactories.count(ioType) == 0) {
            throw std::invalid_argument("Requested input type <" + ioType + "> is not supported.");
        }
        return inputFactories.at(ioType)->getReader(rwOperation, symbolTable, recordTable);
    }
    ~IOSystem() = default;

private:
    IOSystem() {
        registerReadStreamFactory(std::make_shared<ReadFileCSVFactory>());
        registerReadStreamFactory(std::make_shared<ReadCinCSVFactory>());
        registerReadStreamFactory(std::make_shared<ReadFileJSONFactory>());
        registerReadStreamFactory(std::make_shared<ReadCinJSONFactory>());
        registerWriteStreamFactory(std::make_shared<WriteFileCSVFactory>());
        registerWriteStreamFactory(std::make_shared<WriteCoutCSVFactory>());
        registerWriteStreamFactory(std::make_shared<WriteCoutPrintSizeFactory>());
        registerWriteStreamFactory(std::make_shared<WriteFileJSONFactory>());
        registerWriteStreamFactory(std::make_shared<WriteCoutJSONFactory>());
#ifdef USE_SQLITE
        registerReadStreamFactory(std::make_shared<ReadSQLiteFactory>());
        registerWriteStreamFactory(std::make_shared<WriteSQLiteFactory>());
#endif
    };
    std::map<std::string, std::shared_ptr<WriteStreamFactory>> outputFactories;
    std::map<std::string, std::shared_ptr<ReadStreamFactory>> inputFactories;
};

} /* namespace souffle */
