/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file WriteStreamCSV.h
 *
 ***********************************************************************/

#pragma once

#include "souffle/RamTypes.h"
#include "souffle/RecordTable.h"
#include "souffle/SymbolTable.h"
#include "souffle/io/WriteStream.h"
#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/MiscUtil.h"
#include "souffle/utility/ParallelUtil.h"
#ifdef USE_LIBZ
#include "souffle/io/gzfstream.h"
#endif

#include <cstddef>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <ostream>
#include <string>
#include <vector>

namespace souffle {

class WriteStreamCSV : public WriteStream {
protected:
    WriteStreamCSV(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStream(rwOperation, symbolTable, recordTable),
              rfc4180(getOr(rwOperation, "rfc4180", "false") == std::string("true")),
              delimiter(getOr(rwOperation, "delimiter", (rfc4180 ? "," : "\t"))) {
        if (rfc4180 && delimiter.find('"') != std::string::npos) {
            std::stringstream errorMessage;
            errorMessage << "CSV delimiter cannot contain '\"' character when rfc4180 is enabled.";
            throw std::invalid_argument(errorMessage.str());
        }
    };

    const bool rfc4180;

    const std::string delimiter;

    void writeNextTupleCSV(std::ostream& destination, const RamDomain* tuple) {
        writeNextTupleElement(destination, typeAttributes.at(0), tuple[0]);

        for (std::size_t col = 1; col < arity; ++col) {
            destination << delimiter;
            writeNextTupleElement(destination, typeAttributes.at(col), tuple[col]);
        }

        destination << "\n";
    }

    virtual void outputSymbol(std::ostream& destination, const std::string& value) {
        outputSymbol(destination, value, false);
    }

    void outputSymbol(std::ostream& destination, const std::string& value, bool fieldValue) {
        if (rfc4180) {
            if (!fieldValue) {
                destination << '"';
            }
            destination << '"';

            const std::size_t end = value.length();
            for (std::size_t pos = 0; pos < end; ++pos) {
                char ch = value[pos];
                if (ch == '"') {
                    destination << '\\';
                    destination << '"';
                }
                destination << ch;
            }

            if (!fieldValue) {
                destination << '"';
            }
            destination << '"';
        } else {
            destination << value;
        }
    }

    void writeNextTupleElement(std::ostream& destination, const std::string& type, RamDomain value) {
        switch (type[0]) {
            case 's': outputSymbol(destination, symbolTable.decode(value), true); break;
            case 'i': destination << value; break;
            case 'u': destination << ramBitCast<RamUnsigned>(value); break;
            case 'f': destination << ramBitCast<RamFloat>(value); break;
            case 'r':
                if (rfc4180) {
                    destination << '"';
                }
                outputRecord(destination, value, type);
                if (rfc4180) {
                    destination << '"';
                }
                break;
            case '+':
                if (rfc4180) {
                    destination << '"';
                }
                outputADT(destination, value, type);
                if (rfc4180) {
                    destination << '"';
                }
                break;
            default: fatal("unsupported type attribute: `%c`", type[0]);
        }
    }
};

class WriteFileCSV : public WriteStreamCSV {
public:
    WriteFileCSV(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStreamCSV(rwOperation, symbolTable, recordTable),
              file(getFileName(rwOperation), std::ios::out | std::ios::binary) {
        if (getOr(rwOperation, "headers", "false") == "true") {
            file << rwOperation.at("attributeNames") << std::endl;
        }
        file << std::setprecision(std::numeric_limits<RamFloat>::max_digits10);
    }

    ~WriteFileCSV() override = default;

protected:
    std::ofstream file;

    void writeNullary() override {
        file << "()\n";
    }

    void writeNextTuple(const RamDomain* tuple) override {
        writeNextTupleCSV(file, tuple);
    }

    /**
     * Return given filename or construct from relation name.
     * Default name is [configured path]/[relation name].csv
     *
     * @param rwOperation map of IO configuration options
     * @return input filename
     */
    static std::string getFileName(const std::map<std::string, std::string>& rwOperation) {
        auto name = getOr(rwOperation, "filename", rwOperation.at("name") + ".csv");
        if (name.front() != '/') {
            name = getOr(rwOperation, "output-dir", ".") + "/" + name;
        }
        return name;
    }
};

#ifdef USE_LIBZ
class WriteGZipFileCSV : public WriteStreamCSV {
public:
    WriteGZipFileCSV(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStreamCSV(rwOperation, symbolTable, recordTable),
              file(getFileName(rwOperation), std::ios::out | std::ios::binary) {
        if (getOr(rwOperation, "headers", "false") == "true") {
            file << rwOperation.at("attributeNames") << std::endl;
        }
        file << std::setprecision(std::numeric_limits<RamFloat>::max_digits10);
    }

    ~WriteGZipFileCSV() override = default;

protected:
    void writeNullary() override {
        file << "()\n";
    }

    void writeNextTuple(const RamDomain* tuple) override {
        writeNextTupleCSV(file, tuple);
    }

    /**
     * Return given filename or construct from relation name.
     * Default name is [configured path]/[relation name].csv
     *
     * @param rwOperation map of IO configuration options
     * @return input filename
     */
    static std::string getFileName(const std::map<std::string, std::string>& rwOperation) {
        auto name = getOr(rwOperation, "filename", rwOperation.at("name") + ".csv.gz");
        if (name.front() != '/') {
            name = getOr(rwOperation, "output-dir", ".") + "/" + name;
        }
        return name;
    }

    gzfstream::ogzfstream file;
};
#endif

class WriteCoutCSV : public WriteStreamCSV {
public:
    WriteCoutCSV(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStreamCSV(rwOperation, symbolTable, recordTable) {
        std::cout << "---------------\n" << rwOperation.at("name");
        if (getOr(rwOperation, "headers", "false") == "true") {
            std::cout << "\n" << rwOperation.at("attributeNames");
        }
        std::cout << "\n===============\n";
        std::cout << std::setprecision(std::numeric_limits<RamFloat>::max_digits10);
    }

    ~WriteCoutCSV() override {
        std::cout << "===============\n";
    }

protected:
    void writeNullary() override {
        std::cout << "()\n";
    }

    void writeNextTuple(const RamDomain* tuple) override {
        writeNextTupleCSV(std::cout, tuple);
    }
};

class WriteCoutPrintSize : public WriteStream {
public:
    WriteCoutPrintSize(const std::map<std::string, std::string>& rwOperation, const SymbolTable& symbolTable,
            const RecordTable& recordTable)
            : WriteStream(rwOperation, symbolTable, recordTable), lease(souffle::getOutputLock().acquire()) {
        std::cout << rwOperation.at("name") << "\t";
    }

    ~WriteCoutPrintSize() override = default;

protected:
    void writeNullary() override {
        fatal("attempting to iterate over a print size operation");
    }

    void writeNextTuple(const RamDomain* /* tuple */) override {
        fatal("attempting to iterate over a print size operation");
    }

    void writeSize(std::size_t size) override {
        std::cout << size << "\n";
    }

    Lock::Lease lease;
};

class WriteFileCSVFactory : public WriteStreamFactory {
public:
    Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) override {
#ifdef USE_LIBZ
        if (contains(rwOperation, "compress")) {
            return mk<WriteGZipFileCSV>(rwOperation, symbolTable, recordTable);
        }
#endif
        return mk<WriteFileCSV>(rwOperation, symbolTable, recordTable);
    }
    const std::string& getName() const override {
        static const std::string name = "file";
        return name;
    }
    ~WriteFileCSVFactory() override = default;
};

class WriteCoutCSVFactory : public WriteStreamFactory {
public:
    Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) override {
        return mk<WriteCoutCSV>(rwOperation, symbolTable, recordTable);
    }

    const std::string& getName() const override {
        static const std::string name = "stdout";
        return name;
    }
    ~WriteCoutCSVFactory() override = default;
};

class WriteCoutPrintSizeFactory : public WriteStreamFactory {
public:
    Own<WriteStream> getWriter(const std::map<std::string, std::string>& rwOperation,
            const SymbolTable& symbolTable, const RecordTable& recordTable) override {
        return mk<WriteCoutPrintSize>(rwOperation, symbolTable, recordTable);
    }
    const std::string& getName() const override {
        static const std::string name = "stdoutprintsize";
        return name;
    }
    ~WriteCoutPrintSizeFactory() override = default;
};

} /* namespace souffle */
