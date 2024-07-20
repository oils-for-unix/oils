/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file FileUtil.h
 *
 * @brief Datalog project utilities
 *
 ***********************************************************************/

#pragma once

#include <algorithm>
#include <array>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <utility>
#include <sys/stat.h>

// -------------------------------------------------------------------------------
//                               File Utils
// -------------------------------------------------------------------------------

#ifndef _WIN32
#include <unistd.h>
#else
#define NOMINMAX
#define NOGDI
#include <fcntl.h>
#include <io.h>
#include <stdlib.h>
#include <windows.h>

// -------------------------------------------------------------------------------
//                               Windows
// -------------------------------------------------------------------------------

#define PATH_MAX 260

inline char* realpath(const char* path, char* resolved_path) {
    return _fullpath(resolved_path, path, PATH_MAX);
}

/**
 * Define an alias for the popen and pclose functions on windows
 */
#define popen _popen
#define pclose _pclose
#endif

// -------------------------------------------------------------------------------
//                               All systems
// -------------------------------------------------------------------------------

namespace souffle {

// The separator in the PATH variable
#ifdef _MSC_VER
const char PATHdelimiter = ';';
const char pathSeparator = '/';
#else
const char PATHdelimiter = ':';
const char pathSeparator = '/';
#endif

inline std::string& makePreferred(std::string& name) {
    std::replace(name.begin(), name.end(), '\\', '/');
    // std::replace(name.begin(), name.end(), '/', pathSeparator);
    return name;
}

inline bool isAbsolute(const std::string& path) {
    std::filesystem::path P(path);
    return P.is_absolute();
}

/**
 *  Check whether a file exists in the file system
 */
inline bool existFile(const std::string& name) {
    static std::map<std::string, bool> existFileCache{};
    auto it = existFileCache.find(name);
    if (it != existFileCache.end()) {
        return it->second;
    }
    std::filesystem::path P(name);
    bool result = std::filesystem::exists(P);
    /*bool result = false;
    struct stat buffer = {};
    if (stat(P.native().c_str(), &buffer) == 0) {
        if ((buffer.st_mode & S_IFMT) != 0) {
            result = true;
        }
    }*/
    existFileCache[name] = result;
    return result;
}

/**
 *  Check whether a directory exists in the file system
 */
inline bool existDir(const std::string& name) {
    struct stat buffer = {};
    if (stat(name.c_str(), &buffer) == 0) {
        if ((buffer.st_mode & S_IFDIR) != 0) {
            return true;
        }
    }
    return false;
}

/**
 * Check whether a given file exists and it is an executable
 */
#ifdef _WIN32
inline bool isExecutable(const std::string& name) {
    return existFile(
            name);  // there is no EXECUTABLE bit on Windows, so theoretically any file may be executable
}
#else
inline bool isExecutable(const std::string& name) {
    return existFile(name) && (access(name.c_str(), X_OK) == 0);
}
#endif

/**
 * Simple implementation of a which tool
 */
inline std::string which(const std::string& name) {
    // Check if name has path components in it and if so return it immediately
    std::filesystem::path P(name);
    if (P.has_parent_path()) {
        return name;
    }
    // Get PATH from environment, if it exists.
    const char* syspath = ::getenv("PATH");
    if (syspath == nullptr) {
        return "";
    }
    char buf[PATH_MAX];
    std::stringstream sstr;
    sstr << syspath;
    std::string sub;

    // Check for existence of a binary called 'name' in PATH
    while (std::getline(sstr, sub, PATHdelimiter)) {
        std::string path = sub + pathSeparator + name;
        if ((::realpath(path.c_str(), buf) != nullptr) && isExecutable(path) && !existDir(path)) {
            return buf;
        }
    }
    return "";
}

/**
 *  C++-style dirname
 */
inline std::string dirName(const std::string& name) {
    if (name.empty()) {
        return ".";
    }

    std::filesystem::path P(name);
    if (P.has_parent_path()) {
        return P.parent_path().string();
    } else {
        return ".";
    }

    std::size_t lastNotSlash = name.find_last_not_of(pathSeparator);
    // All '/'
    if (lastNotSlash == std::string::npos) {
        return "/";
    }
    std::size_t leadingSlash = name.find_last_of(pathSeparator, lastNotSlash);
    // No '/'
    if (leadingSlash == std::string::npos) {
        return ".";
    }
    // dirname is '/'
    if (leadingSlash == 0) {
        return std::string(1, pathSeparator);
    }
    return name.substr(0, leadingSlash);
}

/**
 *  C++-style realpath
 */
inline std::string absPath(const std::string& path) {
    char buf[PATH_MAX];
    char* res = realpath(path.c_str(), buf);
    return (res == nullptr) ? "" : std::string(buf);
}

/**
 *  Join two paths together; note that this does not resolve overlaps or relative paths.
 */
inline std::string pathJoin(const std::string& first, const std::string& second) {
    return (std::filesystem::path(first) / std::filesystem::path(second)).string();

    /*unsigned firstPos = static_cast<unsigned>(first.size()) - 1;
    while (first.at(firstPos) == pathSeparator) {
        firstPos--;
    }
    unsigned secondPos = 0;
    while (second.at(secondPos) == pathSeparator) {
        secondPos++;
    }
    return first.substr(0, firstPos + 1) + pathSeparator + second.substr(secondPos);*/
}

/*
 * Find out if an executable given by @p tool exists in the path given @p path
 * relative to the directory given by @ base. A path here refers a
 * colon-separated list of directories.
 */
inline std::optional<std::string> findTool(
        const std::string& tool, const std::string& base, const std::string& path) {
    std::filesystem::path dir(dirName(base));
    std::stringstream sstr(path);
    std::string sub;

    while (std::getline(sstr, sub, ':')) {
        auto subpath = (dir / sub / tool);
        if (std::filesystem::exists(subpath)) {
            return absPath(subpath.string());
        }
    }
    return {};
}

/*
 * Get the basename of a fully qualified filename
 */
inline std::string baseName(const std::string& filename) {
    if (filename.empty()) {
        return ".";
    }

    std::size_t lastNotSlash = filename.find_last_not_of(pathSeparator);
    if (lastNotSlash == std::string::npos) {
        return std::string(1, pathSeparator);
    }

    std::size_t lastSlashBeforeBasename = filename.find_last_of(pathSeparator, lastNotSlash - 1);
    if (lastSlashBeforeBasename == std::string::npos) {
        lastSlashBeforeBasename = static_cast<std::size_t>(-1);
    }
    return filename.substr(lastSlashBeforeBasename + 1, lastNotSlash - lastSlashBeforeBasename);
}

/**
 * File name, with extension removed.
 */
inline std::string simpleName(const std::string& path) {
    std::string name = baseName(path);
    const std::size_t lastDot = name.find_last_of('.');
    // file has no extension
    if (lastDot == std::string::npos) {
        return name;
    }
    const std::size_t lastSlash = name.find_last_of(pathSeparator);
    // last slash occurs after last dot, so no extension
    if (lastSlash != std::string::npos && lastSlash > lastDot) {
        return name;
    }
    // last dot after last slash, or no slash
    return name.substr(0, lastDot);
}

/**
 * File extension, with all else removed.
 */
inline std::string fileExtension(const std::string& path) {
    std::string name = path;
    const std::size_t lastDot = name.find_last_of('.');
    // file has no extension
    if (lastDot == std::string::npos) {
        return std::string();
    }
    const std::size_t lastSlash = name.find_last_of(pathSeparator);
    // last slash occurs after last dot, so no extension
    if (lastSlash != std::string::npos && lastSlash > lastDot) {
        return std::string();
    }
    // last dot after last slash, or no slash
    return name.substr(lastDot + 1);
}

/**
 * Generate temporary file.
 */
inline std::string tempFile() {
#ifdef _WIN32
    char ctempl[L_tmpnam];
    std::string templ;
    std::FILE* f = nullptr;
    while (f == nullptr) {
        templ = std::tmpnam(ctempl);
        f = fopen(templ.c_str(), "wx");
    }
    fclose(f);
    return templ;
#else
    char templ[40] = "./souffleXXXXXX";
    close(mkstemp(templ));
    return std::string(templ);
#endif
}

inline std::stringstream execStdOut(char const* cmd) {
    std::stringstream data;
    std::shared_ptr<FILE> command_pipe(popen(cmd, "r"), pclose);

    if (command_pipe.get() == nullptr) {
        return data;
    }

    std::array<char, 256> buffer;
    while (!feof(command_pipe.get())) {
        if (fgets(buffer.data(), 256, command_pipe.get()) != nullptr) {
            data << buffer.data();
        }
    }

    return data;
}

inline std::stringstream execStdOut(std::string const& cmd) {
    return execStdOut(cmd.c_str());
}

class TempFileStream : public std::fstream {
    std::string fileName;

public:
    TempFileStream(std::string fileName = tempFile())
            : std::fstream(fileName), fileName(std::move(fileName)) {}
    ~TempFileStream() override {
        close();
        remove(fileName.c_str());
    }

    std::string const& getFileName() const {
        return fileName;
    }
};

}  // namespace souffle
