/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file gzfstream.h
 * A simple zlib wrapper to provide gzip file streams.
 *
 ***********************************************************************/

#pragma once

#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <zlib.h>

namespace souffle {

namespace gzfstream {

namespace internal {

class gzfstreambuf : public std::streambuf {
public:
    gzfstreambuf() {
        setp(buffer, buffer + (bufferSize - 1));
        setg(buffer + reserveSize, buffer + reserveSize, buffer + reserveSize);
    }

    gzfstreambuf(const gzfstreambuf&) = delete;

    gzfstreambuf(gzfstreambuf&& old) = default;

    gzfstreambuf* open(const std::string& filename, std::ios_base::openmode mode) {
        if (is_open()) {
            return nullptr;
        }
        if ((mode ^ std::ios::in ^ std::ios::out) == 0) {
            return nullptr;
        }

        this->mode = mode;
        std::string gzmode((mode & std::ios::in) != 0 ? "rb" : "wb");
        fileHandle = gzopen(filename.c_str(), gzmode.c_str());

        if (fileHandle == nullptr) {
            return nullptr;
        }
        isOpen = true;

        return this;
    }

    gzfstreambuf* close() {
        if (is_open()) {
            sync();
            isOpen = false;
            if (gzclose(fileHandle) == Z_OK) {
                return this;
            }
        }
        return nullptr;
    }

    bool is_open() const {
        return isOpen;
    }

    ~gzfstreambuf() override {
        try {
            close();
        } catch (...) {
            // Don't throw exceptions.
        }
    }

protected:
    int_type overflow(int c = EOF) override {
        if (((mode & std::ios::out) == 0) || !isOpen) {
            return EOF;
        }

        if (c != EOF) {
            *pptr() = c;
            pbump(1);
        }
        const int toWrite = static_cast<int>(pptr() - pbase());
        if (gzwrite(fileHandle, pbase(), static_cast<unsigned int>(toWrite)) != toWrite) {
            return EOF;
        }
        pbump(-toWrite);

        return c;
    }

    int_type underflow() override {
        if (((mode & std::ios::in) == 0) || !isOpen) {
            return EOF;
        }
        if ((gptr() != nullptr) && (gptr() < egptr())) {
            return traits_type::to_int_type(*gptr());
        }

        std::size_t charsPutBack = gptr() - eback();
        if (charsPutBack > reserveSize) {
            charsPutBack = reserveSize;
        }
        memcpy(buffer + reserveSize - charsPutBack, gptr() - charsPutBack, charsPutBack);

        int charsRead =
                gzread(fileHandle, buffer + reserveSize, static_cast<unsigned int>(bufferSize - reserveSize));
        if (charsRead <= 0) {
            return EOF;
        }

        setg(buffer + reserveSize - charsPutBack, buffer + reserveSize, buffer + reserveSize + charsRead);

        return traits_type::to_int_type(*gptr());
    }

    int sync() override {
        if ((pptr() != nullptr) && pptr() > pbase()) {
            const int toWrite = static_cast<int>(pptr() - pbase());
            if (gzwrite(fileHandle, pbase(), static_cast<unsigned int>(toWrite)) != toWrite) {
                return -1;
            }
            pbump(-toWrite);
        }
        return 0;
    }

private:
    static constexpr std::size_t bufferSize = 65536;
    static constexpr std::size_t reserveSize = 16;

    char buffer[bufferSize] = {};
    gzFile fileHandle = {};
    bool isOpen = false;
    std::ios_base::openmode mode = std::ios_base::in;
};

class gzfstream : virtual public std::ios {
public:
    gzfstream() {
        init(&buf);
    }

    gzfstream(const std::string& filename, std::ios_base::openmode mode) {
        init(&buf);
        open(filename, mode);
    }

    gzfstream(const gzfstream&) = delete;

    gzfstream(gzfstream&&) = delete;

    ~gzfstream() override = default;

    void open(const std::string& filename, std::ios_base::openmode mode) {
        if (buf.open(filename, mode) == nullptr) {
            clear(rdstate() | std::ios::badbit);
        }
    }

    bool is_open() {
        return buf.is_open();
    }

    void close() {
        if (buf.is_open()) {
            if (buf.close() == nullptr) {
                clear(rdstate() | std::ios::badbit);
            }
        }
    }

    gzfstreambuf* rdbuf() const {
        return &buf;
    }

protected:
    mutable gzfstreambuf buf;
};

}  // namespace internal

class igzfstream : public internal::gzfstream, public std::istream {
public:
    igzfstream() : internal::gzfstream(), std::istream(&buf) {}

    explicit igzfstream(const std::string& filename, std::ios_base::openmode mode = std::ios::in)
            : internal::gzfstream(filename, mode), std::istream(&buf) {}

    igzfstream(const igzfstream&) = delete;

    igzfstream(igzfstream&&) = delete;

    internal::gzfstreambuf* rdbuf() const {
        return internal::gzfstream::rdbuf();
    }

    void open(const std::string& filename, std::ios_base::openmode mode = std::ios::in) {
        internal::gzfstream::open(filename, mode);
    }
};

class ogzfstream : public internal::gzfstream, public std::ostream {
public:
    ogzfstream() : std::ostream(&buf) {}

    explicit ogzfstream(const std::string& filename, std::ios_base::openmode mode = std::ios::out)
            : internal::gzfstream(filename, mode), std::ostream(&buf) {}

    ogzfstream(const ogzfstream&) = delete;

    ogzfstream(ogzfstream&&) = delete;

    internal::gzfstreambuf* rdbuf() const {
        return internal::gzfstream::rdbuf();
    }

    void open(const std::string& filename, std::ios_base::openmode mode = std::ios::out) {
        internal::gzfstream::open(filename, mode);
    }
};

} /* namespace gzfstream */

} /* namespace souffle */
