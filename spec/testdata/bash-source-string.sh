#!/bin/bash

argv.py $BASH_SOURCE  # SimpleVarSub
argv.py ${BASH_SOURCE}

# Test with 2 entries
source spec/testdata/bash-source-string2.sh
