/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2022, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */
#ifndef GET_OPT_LONG_H
#define GET_OPT_LONG_H

// Points to the argument of the last option found.
extern char* optarg;

// Index of the next element to processed in argv.
extern int optind;

// Enables error message printing if opterr!=0.
extern int opterr;

extern int optopt;

// The long option descriptor, as described by man page for getopt_long.
struct option {
    const char* name;  // name of the long option.
    int has_arg;       // 0=no argument, 1=requires argument, 2=optional argument.
    int* flag;  // if non-null, the variable pointed by `flag` is set to `val` when getopt_long finds this
                // option.
    int val;    // value to return or to load in the variable pointed by `flag` when this option is found.
};

// A limited implementation of POSIX getopt_long.
extern int getopt_long(
        int argc, char* const argv[], const char* optstring, const struct option* longopts, int* longindex);

#endif
