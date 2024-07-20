/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ReadStreamSQLite.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/ReadStream.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/StringUtil.h"
#include <cassert>
#include <cstdint>
#include <fstream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <sqlite3.h>

namespace souffle {

class ReadStreamSQLite : public ReadStream {
public:
    ReadStreamSQLite(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable)
            : ReadStream(rwOperation, symbolTable, recordTable), dbFilename(getFileName(rwOperation)),
              relationName(rwOperation.at("name")) {
        openDB();
        checkTableExists();
        prepareSelectStatement();
    }

    ~ReadStreamSQLite() override {
        sqlite3_finalize(selectStatement);
        sqlite3_close(db);
    }

protected:
    /**
     * Read and return the next tuple.
     *
     * Returns nullptr if no tuple was readable.
     * @return
     */
    Own<RamDomain[]> readNextTuple() override {
        if (sqlite3_step(selectStatement) != SQLITE_ROW) {
            return nullptr;
        }

        Own<RamDomain[]> tuple = mk<RamDomain[]>(arity + auxiliaryArity);

        uint32_t column;
        for (column = 0; column < arity; column++) {
            std::string element;
            if (0 == sqlite3_column_bytes(selectStatement, column)) {
                element = "";
            } else {
                element = reinterpret_cast<const char*>(sqlite3_column_text(selectStatement, column));

                if (element.empty()) {
                    element = "";
                }
            }

            try {
                auto&& ty = typeAttributes.at(column);
                switch (ty[0]) {
                    case 's': tuple[column] = symbolTable.encode(element); break;
                    case 'f': tuple[column] = ramBitCast(RamFloatFromString(element)); break;
                    case 'i':
                    case 'u':
                    case 'r': tuple[column] = RamSignedFromString(element); break;
                    default: fatal("invalid type attribute: `%c`", ty[0]);
                }
            } catch (...) {
                std::stringstream errorMessage;
                errorMessage << "Error converting number in column " << (column) + 1;
                throw std::invalid_argument(errorMessage.str());
            }
        }

        return tuple;
    }

    void executeSQL(const std::string& sql) {
        assert(db && "Database connection is closed");

        char* errorMessage = nullptr;
        /* Execute SQL statement */
        int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, &errorMessage);
        if (rc != SQLITE_OK) {
            std::stringstream error;
            error << "SQLite error in sqlite3_exec: " << sqlite3_errmsg(db) << "\n";
            error << "SQL error: " << errorMessage << "\n";
            error << "SQL: " << sql << "\n";
            sqlite3_free(errorMessage);
            throw std::invalid_argument(error.str());
        }
    }

    void throwError(const std::string& message) {
        std::stringstream error;
        error << message << sqlite3_errmsg(db) << "\n";
        throw std::invalid_argument(error.str());
    }

    void prepareSelectStatement() {
        std::stringstream selectSQL;
        selectSQL << "SELECT * FROM '" << relationName << "'";
        const char* tail = nullptr;
        if (sqlite3_prepare_v2(db, selectSQL.str().c_str(), -1, &selectStatement, &tail) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_prepare_v2: ");
        }
    }

    void openDB() {
        sqlite3_config(SQLITE_CONFIG_URI, 1);
        if (sqlite3_open(dbFilename.c_str(), &db) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_open: ");
        }
        sqlite3_extended_result_codes(db, 1);
        executeSQL("PRAGMA synchronous = OFF");
        executeSQL("PRAGMA journal_mode = MEMORY");
    }

    void checkTableExists() {
        sqlite3_stmt* tableStatement;
        std::stringstream selectSQL;
        selectSQL << "SELECT count(*) FROM sqlite_master WHERE type IN ('table', 'view') AND ";
        selectSQL << " name = '" << relationName << "';";
        const char* tail = nullptr;

        if (sqlite3_prepare_v2(db, selectSQL.str().c_str(), -1, &tableStatement, &tail) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_prepare_v2: ");
        }

        if (sqlite3_step(tableStatement) == SQLITE_ROW) {
            int count = sqlite3_column_int(tableStatement, 0);
            if (count > 0) {
                sqlite3_finalize(tableStatement);
                return;
            }
        }
        sqlite3_finalize(tableStatement);
        throw std::invalid_argument(
                "Required table or view does not exist in " + dbFilename + " for relation " + relationName);
    }

    /**
     * Return given filename or construct from relation name.
     * Default name is [configured path]/[relation name].sqlite
     *
     * @param rwOperation map of IO configuration options
     * @return input filename
     */
    static std::string getFileName(const std::map<std::string, std::string>& rwOperation) {
        // legacy support for SQLite prior to 2020-03-18
        // convert dbname to filename
        auto name = getOr(rwOperation, "dbname", rwOperation.at("name") + ".sqlite");
        name = getOr(rwOperation, "filename", name);

        if (name.rfind("file:", 0) == 0 || name.rfind(":memory:", 0) == 0) {
            return name;
        }

        if (name.front() != '/') {
            name = getOr(rwOperation, "fact-dir", ".") + "/" + name;
        }
        return name;
    }

    const std::string dbFilename;
    const std::string relationName;
    sqlite3_stmt* selectStatement = nullptr;
    sqlite3* db = nullptr;
};

class ReadSQLiteFactory : public ReadStreamFactory {
public:
    Own<ReadStream> getReader(const std::map<std::string, std::string>& rwOperation, SymbolTable& symbolTable,
            RecordTable& recordTable) override {
        return mk<ReadStreamSQLite>(rwOperation, symbolTable, recordTable);
    }

    const std::string& getName() const override {
        static const std::string name = "sqlite";
        return name;
    }
    ~ReadSQLiteFactory() override = default;
};

} /* namespace souffle */
