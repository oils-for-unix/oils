#!/usr/bin/env bash
#
# Launch R with the libraries we installed for benchmarks and tests.

source test/common.sh

R_LIBS_USER=$R_PATH R "$@"
