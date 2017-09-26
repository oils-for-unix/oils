#!/bin/bash
#
# Bash implements type -t.
# 
# NOTE: Aliases don't work in batch mode!  Interactive only.

### Basic getopts invocation
set -- -h -c foo x y z
FLAG_h=0
FLAG_c=''
while getopts "hc:" opt; do
  case $opt in
    h) FLAG_h=1 ;;
    c) FLAG_c="$OPTARG" ;;
  esac
done
shift $(( OPTIND - 1 ))
echo h=$FLAG_h c=$FLAG_c optind=$OPTIND argv=$@
# stdout: h=1 c=foo optind=4 argv=x y z
