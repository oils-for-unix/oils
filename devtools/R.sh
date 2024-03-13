#!/usr/bin/env bash
#
# Launch R with the libraries we installed for benchmarks and tests.
#
# Trivial wrapper around the R-libs wedge

source build/dev-shell.sh

R "$@"
