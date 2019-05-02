#!/bin/bash
#
# Manual repro for prompt bug:
#
# bin/osh
# osh$ . demo/cannot-fork.sh
#
# For completion bug:
#
# osh$ . testdata/completion/osh-unit.sh
# osh$ . demo/cannot-fork.sh
# osh$ optdemo <TAB>

PS1='$(echo hi)\$'
prlimit --nproc=1 --pid=$$
