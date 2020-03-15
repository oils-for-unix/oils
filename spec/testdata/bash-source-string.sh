#!/bin/bash

argv.py $BASH_SOURCE  # SimpleVarSub
argv.py ${BASH_SOURCE}
argv.py $BASH_LINENO # SimpleVarSub
argv.py ${BASH_LINENO}

echo ____

# Test with 2 entries
source spec/testdata/bash-source-string2.sh
