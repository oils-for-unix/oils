/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2021, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SubProcess.h
 *
 * Wrapper for launching subprocesses.
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/Types.h"
#include "souffle/utility/span.h"
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <optional>
#include <type_traits>

#ifdef _MSC_VER
#define NOMINMAX
#include <windows.h>
#else
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace souffle {

namespace detail {
[[noreturn]] inline void perrorExit(char const* msg) {
    ::perror(msg);
    std::exit(EXIT_FAILURE);
}

// These are used by bash and are a defacto standard on Linux.
// This list is incomplete.
enum LinuxExitCode : int {
    cannot_execute = 126,
    command_not_found = 127,
};

using LinuxWaitStatus = int;
}  // namespace detail

/**
 * Executes a process w/ the given `argv` arguments and `envp` overriden env-vars.
 *
 * @param   argv  The arguments to the process.
 *                Do not include the 'program invoked as' argument 0. This is implicitly done for you.
 * @param   envp  Collection of env vars to override.
 *                Any env not specified in `envp` is inherited from this process' environment.
 * @return  `None` IFF unable to launch `program`, otherwise `program`'s `wait` status.
 *           NB: This is not the exit code, though the exit code can be obtained from it.
 *               However, you can do `execute(...) == 0` if you only care that it succeeded.
 */
template <typename Envp = span<std::pair<char const*, char const*>>,
        typename = std::enable_if_t<is_iterable_of<Envp, std::pair<char const*, char const*> const>>>
std::optional<detail::LinuxWaitStatus> execute(
        std::string const& program, span<char const* const> argv = {}, Envp&& envp = {}) {
#ifndef _MSC_VER
    using EC = detail::LinuxExitCode;

    auto pid = ::fork();
    switch (pid) {
        case -1: return std::nullopt;  // unable to fork. likely hit a resource limit of some kind.

        case 0: {  // child
            // thankfully we're a fork. we can trash this proc's `::environ` w/o reprocussions
            for (auto&& [k, v] : envp) {
                if (::setenv(k, v, 1)) detail::perrorExit("setenv");
            }

            char* argv_temp[argv.size() + 2];
            argv_temp[0] = const_cast<char*>(program.c_str());
            std::copy_n(argv.data(), argv.size(), const_cast<char const**>(argv_temp) + 1);
            argv_temp[argv.size() + 1] = nullptr;

            ::execvp(program.c_str(), argv_temp);
            std::exit(EC::cannot_execute);
        }

        default: {  // parent
            detail::LinuxWaitStatus status;
            if (::waitpid(pid, &status, 0) == -1) {
                // not recoverable / should never happen.
                detail::perrorExit("`waitpid` failed");
            }

            // check it exited or signaled (didn't specify `WNOHANG` or `WUNTRACED`)
            assert(WIFSIGNALED(status) || WIFEXITED(status));

            // check that the fork child successfully `exec`'d
            if (WIFEXITED(status)) {
                switch (WEXITSTATUS(status)) {
                    default: return WEXITSTATUS(status);

                    case EC::cannot_execute:                          // FALL THRU: command_not_found
                    case EC::command_not_found: return std::nullopt;  // fork couldn't execute the program
                }
            }
            // what should be returned on signal? Treat as error
            return EXIT_FAILURE;
        }
    }
#else
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD exit_code = 0;

    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    memset(&pi, 0, sizeof(pi));

    std::size_t l;
    std::wstring program_w(program.length() + 1, L' ');
    ::mbstowcs_s(&l, program_w.data(), program_w.size(), program.data(), program.size());
    program_w.resize(l - 1);

    WCHAR FoundPath[PATH_MAX];
    int64_t Found = (int64_t)FindExecutableW(program_w.c_str(), nullptr, FoundPath);
    if (Found <= 32) {
        std::cerr << "Cannot find executable '" << program << "'.\n";
        return std::nullopt;
    }

    std::wstringstream args_w;
    args_w << program_w;
    for (const auto& arg : argv) {
        std::string arg_s(arg);
        std::wstring arg_w(arg_s.length() + 1, L' ');
        ::mbstowcs_s(&l, arg_w.data(), arg_w.size(), arg_s.data(), arg_s.size());
        arg_w.resize(l - 1);
        args_w << L' ' << arg_w;
    }

    std::string envir;
    for (const auto& couple : envp) {
        envir += couple.first;
        envir += '=';
        envir += couple.second;
        envir += '\0';
    }
    envir += '\0';

    if (!CreateProcessW(FoundPath, args_w.str().data(), NULL, NULL, FALSE, 0, /*envir.data()*/ nullptr, NULL,
                &si, &pi)) {
        return std::nullopt;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);

    if (!GetExitCodeProcess(pi.hProcess, &exit_code)) {
        return std::nullopt;
    }

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return static_cast<int>(exit_code);

#endif
}

/**
 * Executes a process w/ the given `argv` arguments and `envp` overriden env-vars.
 *
 * @param   argv  The arguments to the process.
 *                Do not include the 'program invoked as' argument 0. This is implicitly done for you.
 * @param   envp  Collection of env vars to override.
 *                Any env not specified in `envp` is inherited from this process' environment.
 * @return  `None` IFF unable to launch `program`, otherwise `program`'s `wait` status.
 *           NB: This is not the exit code, though the exit code can be obtained from it.
 *               However, you can do `execute(...) == 0` if you only care that it succeeded.
 */
template <typename Envp = span<std::pair<char const*, std::string>>,
        typename = std::enable_if_t<is_iterable_of<Envp, std::pair<char const*, std::string> const>>>
std::optional<detail::LinuxWaitStatus> execute(
        std::string const& program, span<std::string const> argv, Envp&& envp = {}) {
    auto go = [](auto* dst, auto&& src, auto&& f) {
        size_t i = 0;
        for (auto&& x : src)
            dst[i++] = f(x);
        return span<std::remove_pointer_t<decltype(dst)>>{dst, dst + src.size()};
    };

    std::unique_ptr<char const*[]> argv_temp = std::make_unique<char const*[]>(argv.size());
    std::unique_ptr<std::pair<char const*, char const*>[]> envp_temp =
            std::make_unique<std::pair<char const*, char const*>[]>(envp.size());
    auto argv_ptr = go(argv_temp.get(), argv, [](auto&& x) { return x.c_str(); });
    auto envp_ptr = go(envp_temp.get(), envp, [](auto&& kv) {
        return std::pair{kv.first, kv.second.c_str()};
    });
    return souffle::execute(program, argv_ptr, envp_ptr);
}

}  // namespace souffle
