#!/usr/bin/env bash
#
# Tests that explore parsing corner cases.

#### Length of length of ARGS!
func() { echo ${##}; }
func 0 1 2 3 4 5 6 7 8 
## stdout: 1

#### Length of length of ARGS!  2 digit
func() { echo ${##}; }
func 0 1 2 3 4 5 6 7 8 9
## stdout: 2
