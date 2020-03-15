#!/bin/bash

argv.py $BASH_SOURCE  # SimpleVarSub
argv.py ${BASH_SOURCE}
argv.py $BASH_LINENO  # SimpleVarSub
argv.py ${BASH_LINENO}
argv.py $FUNCNAME  # SimpleVarSub
argv.py ${FUNCNAME}
