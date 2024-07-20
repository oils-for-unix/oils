/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

// Implementation of getopt_long for Windows.
#pragma once
#ifdef USE_CUSTOM_GETOPTLONG

#include "GetOptLong.h"
#include <stdio.h>
#include <string.h>

char* optarg = nullptr;

// the index of the next element to be processed in argv
int optind = 0;
int opterr = 1;
int optopt = 0;

enum { no_argument = 0, required_argument = 1, optional_argument = 2 };

namespace {

// nextchar points to the next option character in an element of argv
char* nextchar = nullptr;

// value of optind at the previous call of getopt_long
int previous_optind = -1;

// the number of non-options elements of argv skipped last time getopt was called
int nonopt_count = 0;

int parse_long_option(const int argc, char* const argv[], const struct option* longopts, int* longindex,
        const int print_error_message, const int missing_argument) {
    char* const current = nextchar;
    ++optind;

    char* const hasequal = strchr(current, '=');
    size_t namelength = (hasequal ? (hasequal - current) : strlen(current));

    int i;
    int match = -1;
    for (i = 0; longopts[i].name != nullptr; ++i) {
        if (strncmp(longopts[i].name, current, namelength)) {
            continue;
        }
        if (strlen(longopts[i].name) != namelength) {
            continue;
        }

        match = i;
        break;
    }

    if (match == -1) {
        // cannot find long option
        if (print_error_message) {
            fprintf(stderr, "unknown option -- %.*s\n", static_cast<int>(namelength), current);
        }
        optopt = 0;
        return (int)'?';
    }

    if (longopts[match].has_arg == no_argument) {
        // no argument expected
        if (hasequal) {
            if (print_error_message) {
                fprintf(stderr, "unexpected argument -- %.*s\n", static_cast<int>(namelength), current);
            }
            if (longopts[match].flag == nullptr) {
                optopt = longopts[match].val;
            } else {
                optopt = 0;
            }
            return (int)'?';
        }
    }

    if (longopts[match].has_arg == required_argument || longopts[match].has_arg == optional_argument) {
        if (hasequal) {
            // argument is in the same argv after '=' sign
            optarg = hasequal + 1;
        } else if (optind < argc) {
            // Argument may be in next argv
            // If argument is optional, leave optarg to null, user is in charge
            // of verifying the value of argv[optind] and increment optind
            // if the argument is valid.
            if (longopts[match].has_arg == required_argument) {
                // mandatory argument
                optarg = argv[optind++];
            }
        } else {
            // no argument found
            if (longopts[match].has_arg == required_argument) {
                if (print_error_message) {
                    fprintf(stderr, "missing mandatory argument -- %.*s\n", static_cast<int>(namelength),
                            current);
                }
                optopt = 0;
                return missing_argument;
            }
        }
    }  // unexpected value of has_arg is not verified

    if (longindex) *longindex = match;
    if (longopts[match].flag) {
        *longopts[match].flag = longopts[match].val;
        return 0;
    } else {
        return longopts[match].val;
    }
}

// permute argv[last] and argv[last-1] and recurse
void permute(char* argv[], int first, int last) {
    if (first >= last) return;
    char* tmp = argv[last];
    argv[last] = argv[last - 1];
    argv[last - 1] = tmp;
    permute(argv, first, last - 1);
}

void shift(char* argv[]) {
    // done with reading options from argv[previous_optind]..argv[optind-1]

    int start = previous_optind;
    for (int mv = previous_optind + nonopt_count; mv < optind; ++mv) {
        permute(argv, start, mv);
        ++start;
    }

    optind -= nonopt_count;
    previous_optind = optind;
    nonopt_count = 0;
}

}  // anonymous namespace

int getopt_long(
        int argc, char* const argv[], const char* optstring, const struct option* longopts, int* longindex) {
    if (optind == 0) {  // full reset
        nextchar = nullptr;
        nonopt_count = 0;
        optarg = nullptr;
        optind = 1;
        previous_optind = optind;
    }

    int missing_argument = (int)'?';
    int print_error_message = opterr;

    optarg = nullptr;

    if (*optstring == '+' || *optstring == '-') {
        throw "Mode +/- of optstring is not supported.";
        ++optstring;
    }

    if (*optstring == ':') {
        missing_argument = (int)':';
        print_error_message = 0;
        ++optstring;
    }

    if (nextchar == nullptr) {   // scan starting at argv[optind]
        if (nonopt_count > 0) {  // previous scan skipped over some non-option arguments
            shift((char**)argv);
        } else {
            previous_optind = optind;
        }
    }

    if (optind >= argc) {
        // all command-line arguments have been scanned
        return -1;
    }

    if (nextchar == nullptr) {  // scan starting at argv[optind], skip over any non-option elements
        while ((optind + nonopt_count < argc) &&
                (argv[optind + nonopt_count][0] != '-' || argv[optind + nonopt_count][1] == 0)) {
            ++nonopt_count;
        }

        if (optind + nonopt_count == argc) {
            // no more options
            nonopt_count = 0;
            return -1;
        }

        optind += nonopt_count;
    }

    if (nextchar == nullptr && optind < argc) {  // scan starting at argv[optind]
        nextchar = argv[optind];
    }

    if (nextchar == argv[optind] && *nextchar == '-') {
        ++nextchar;
        if (*nextchar == '-' && nextchar[1] == 0) {
            // double-dash marks the end of the option scan
            nextchar = nullptr;
            shift((char**)argv);
            return -1;
        } else if (*nextchar == '-' && *(++nextchar)) {
            // search long option
            optopt =
                    parse_long_option(argc, argv, longopts, longindex, print_error_message, missing_argument);
            nextchar = nullptr;
            return optopt;
        } else if (*nextchar == 0) {
            // missing option character
            optind += 1;
            nextchar = nullptr;
            return -1;
        }
    }

    // search short option
    const char* option;
    optopt = *nextchar++;
    if ((option = strchr(optstring, optopt)) == nullptr) {
        // cannot find option
        if (print_error_message) {
            fprintf(stderr, "unknown option -- %c\n", optopt);
        }
        return (int)'?';
    }
    ++option;

    if (*option++ != ':') {
        // no argument required
        if (!*nextchar) {
            ++optind;
            nextchar = nullptr;
        }
    } else {
        if (*nextchar) {
            // if argument is in the same argv, always set optarg
            optarg = nextchar;
            ++optind;
            nextchar = nullptr;
        } else if (argc <= ++optind) {
            // no argument found
            nextchar = nullptr;
            optarg = nullptr;

            if (*option != ':') {
                // mandatory argument is missing
                if (print_error_message) {
                    fprintf(stderr, "missing mandatory argument -- %c\n", optopt);
                }
                return missing_argument;
            }
        } else {
            // argument is in next argv
            nextchar = nullptr;

            if (*option != ':' &&
                    ((argv[optind][0] == '-' && (argv[optind][1] != 0 && argv[optind][1] != '-')) ||
                            (argv[optind][0] == '-' && argv[optind][1] == '-' && argv[optind][2] != 0))) {
                // argument is mandatory, but must not start with a dash or a double-dash
                // or must be exactly dash or double-dash.
                if (print_error_message) {
                    fprintf(stderr, "missing mandatory argument -- %c\n", optopt);
                }
                optarg = nullptr;
                return missing_argument;
            }

            if (*option != ':') {
                // argument is mandatory
                optarg = argv[optind++];
            } else {
                // Argument is optional but not in the same argv, set optarg to null.
                // User is in charge of interpreting argv[optind] and increment it
                // if it considers its a valid argument.
                optarg = nullptr;
            }
        }
    }

    return optopt;
}

#endif
