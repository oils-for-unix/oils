/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file WriteStreamSQLite.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/WriteStream.h"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <sqlite3.h>

namespace souffle {

class WriteStreamSQLite : public WriteStream {
public:
    WriteStreamSQLite(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStream(rwOperation, symbolTable, recordTable), dbFilename(getFileName(rwOperation)),
              relationName(rwOperation.at("name")) {
        openDB();
        createTables();
        prepareStatements();
        executeSQL("BEGIN TRANSACTION", db);
    }

    ~WriteStreamSQLite() override {
        executeSQL("COMMIT", db);
        sqlite3_finalize(insertStatement);
        sqlite3_finalize(symbolInsertStatement);
        sqlite3_finalize(symbolSelectStatement);
        sqlite3_close(db);
    }

protected:
    void writeNullary() override {}

    void writeNextTuple(const RamDomain* tuple) override {
        for (std::size_t i = 0; i < arity; i++) {
            RamDomain value = 0;  // Silence warning

            switch (typeAttributes.at(i)[0]) {
                case 's': value = getSymbolTableID(tuple[i]); break;
                default: value = tuple[i]; break;
            }

#if RAM_DOMAIN_SIZE == 64
            if (sqlite3_bind_int64(insertStatement, static_cast<int>(i + 1),
                        static_cast<sqlite3_int64>(value)) != SQLITE_OK) {
#else
            if (sqlite3_bind_int(insertStatement, static_cast<int>(i + 1), static_cast<int>(value)) !=
                    SQLITE_OK) {
#endif
                throwError("SQLite error in sqlite3_bind_text: ");
            }
        }
        if (sqlite3_step(insertStatement) != SQLITE_DONE) {
            throwError("SQLite error in sqlite3_step: ");
        }
        sqlite3_clear_bindings(insertStatement);
        sqlite3_reset(insertStatement);
    }

private:
    void executeSQL(const std::string& sql, sqlite3* db) {
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

    uint64_t getSymbolTableIDFromDB(std::size_t index) {
        if (sqlite3_bind_text(symbolSelectStatement, 1, symbolTable.decode(index).c_str(), -1,
                    SQLITE_TRANSIENT) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_bind_text: ");
        }
        if (sqlite3_step(symbolSelectStatement) != SQLITE_ROW) {
            throwError("SQLite error in sqlite3_step: ");
        }
        uint64_t rowid = sqlite3_column_int64(symbolSelectStatement, 0);
        sqlite3_clear_bindings(symbolSelectStatement);
        sqlite3_reset(symbolSelectStatement);
        return rowid;
    }
    uint64_t getSymbolTableID(std::size_t index) {
        if (dbSymbolTable.count(index) != 0) {
            return dbSymbolTable[index];
        }

        if (sqlite3_bind_text(symbolInsertStatement, 1, symbolTable.decode(index).c_str(), -1,
                    SQLITE_TRANSIENT) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_bind_text: ");
        }
        // Either the insert succeeds and we have a new row id or it already exists and a select is needed.
        uint64_t rowid;
        if (sqlite3_step(symbolInsertStatement) != SQLITE_DONE) {
            // The symbol already exists so select it.
            rowid = getSymbolTableIDFromDB(index);
        } else {
            rowid = sqlite3_last_insert_rowid(db);
        }
        sqlite3_clear_bindings(symbolInsertStatement);
        sqlite3_reset(symbolInsertStatement);

        dbSymbolTable[index] = rowid;
        return rowid;
    }

    void openDB() {
        sqlite3_config(SQLITE_CONFIG_URI, 1);
        if (sqlite3_open(dbFilename.c_str(), &db) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_open: ");
        }
        sqlite3_extended_result_codes(db, 1);
        executeSQL("PRAGMA synchronous = OFF", db);
        executeSQL("PRAGMA journal_mode = MEMORY", db);
    }

    void prepareStatements() {
        prepareInsertStatement();
        prepareSymbolInsertStatement();
        prepareSymbolSelectStatement();
    }
    void prepareSymbolInsertStatement() {
        std::stringstream insertSQL;
        insertSQL << "INSERT INTO " << symbolTableName;
        insertSQL << " VALUES(null,@V0);";
        const char* tail = nullptr;
        if (sqlite3_prepare_v2(db, insertSQL.str().c_str(), -1, &symbolInsertStatement, &tail) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_prepare_v2: ");
        }
    }

    void prepareSymbolSelectStatement() {
        std::stringstream selectSQL;
        selectSQL << "SELECT id FROM " << symbolTableName;
        selectSQL << " WHERE symbol = @V0;";
        const char* tail = nullptr;
        if (sqlite3_prepare_v2(db, selectSQL.str().c_str(), -1, &symbolSelectStatement, &tail) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_prepare_v2: ");
        }
    }

    void prepareInsertStatement() {
        std::stringstream insertSQL;
        insertSQL << "INSERT INTO '_" << relationName << "' VALUES ";
        insertSQL << "(@V0";
        for (unsigned int i = 1; i < arity; i++) {
            insertSQL << ",@V" << i;
        }
        insertSQL << ");";
        const char* tail = nullptr;
        if (sqlite3_prepare_v2(db, insertSQL.str().c_str(), -1, &insertStatement, &tail) != SQLITE_OK) {
            throwError("SQLite error in sqlite3_prepare_v2: ");
        }
    }

    void createTables() {
        createRelationTable();
        createRelationView();
        createSymbolTable();
    }

    void createRelationTable() {
        std::stringstream createTableText;
        createTableText << "CREATE TABLE IF NOT EXISTS '_" << relationName << "' (";
        if (arity > 0) {
            createTableText << "'0' INTEGER";
            for (unsigned int i = 1; i < arity; i++) {
                createTableText << ",'" << std::to_string(i) << "' ";
                createTableText << "INTEGER";
            }
        }
        createTableText << ");";
        executeSQL(createTableText.str(), db);
        executeSQL("DELETE FROM '_" + relationName + "';", db);
    }

    void createRelationView() {
        // Create view with symbol strings resolved

        const auto columnNames = params["relation"]["params"].array_items();

        std::stringstream createViewText;
        createViewText << "CREATE VIEW IF NOT EXISTS '" << relationName << "' AS ";
        std::stringstream projectionClause;
        std::stringstream fromClause;
        fromClause << "'_" << relationName << "'";
        std::stringstream whereClause;
        bool firstWhere = true;
        for (unsigned int i = 0; i < arity; i++) {
            const std::string tableColumnName = std::to_string(i);
            const auto& viewColumnName =
                    (columnNames[i].is_string() ? columnNames[i].string_value() : tableColumnName);
            if (i != 0) {
                projectionClause << ",";
            }
            if (typeAttributes.at(i)[0] == 's') {
                projectionClause << "'_symtab_" << tableColumnName << "'.symbol AS '" << viewColumnName
                                 << "'";
                fromClause << ",'" << symbolTableName << "' AS '_symtab_" << tableColumnName << "'";
                if (!firstWhere) {
                    whereClause << " AND ";
                } else {
                    firstWhere = false;
                }
                whereClause << "'_" << relationName << "'.'" << tableColumnName << "' = "
                            << "'_symtab_" << tableColumnName << "'.id";
            } else {
                projectionClause << "'_" << relationName << "'.'" << tableColumnName << "' AS '"
                                 << viewColumnName << "'";
            }
        }
        createViewText << "SELECT " << projectionClause.str() << " FROM " << fromClause.str();
        if (!firstWhere) {
            createViewText << " WHERE " << whereClause.str();
        }
        createViewText << ";";
        executeSQL(createViewText.str(), db);
    }
    void createSymbolTable() {
        std::stringstream createTableText;
        createTableText << "CREATE TABLE IF NOT EXISTS '" << symbolTableName << "' ";
        createTableText << "(id INTEGER PRIMARY KEY, symbol TEXT UNIQUE);";
        executeSQL(createTableText.str(), db);
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
            name = getOr(rwOperation, "output-dir", ".") + "/" + name;
        }
        return name;
    }

    const std::string dbFilename;
    const std::string relationName;
    const std::string symbolTableName = "__SymbolTable";

    std::unordered_map<uint64_t, uint64_t> dbSymbolTable;
    sqlite3_stmt* insertStatement = nullptr;
    sqlite3_stmt* symbolInsertStatement = nullptr;
    sqlite3_stmt* symbolSelectStatement = nullptr;
    sqlite3* db = nullptr;
};

class WriteSQLiteFactory : public WriteStreamFactory {
public:
    Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) override {
        return mk<WriteStreamSQLite>(rwOperation, symbolTable, recordTable);
    }

    const std::string& getName() const override {
        static const std::string name = "sqlite";
        return name;
    }
    ~WriteSQLiteFactory() override = default;
};

} /* namespace souffle */
