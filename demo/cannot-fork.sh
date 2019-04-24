#!/bin/bash
#
# Manual repro for a bug:
#
# bin/osh
# osh$ . demo/cannot-fork.sh

PS1='$(echo hi)\$'
prlimit --nproc=1 --pid=$$
