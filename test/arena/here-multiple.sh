#!/bin/bash

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
osh0-oil3() {
  bin/osh --fix "$@" | diff -u /dev/fd/3 - || { echo FAIL; exit 1; }
}

osh0-oil3 << 'OSH' 2>&1 3<< 'OIL'
x=1
OSH
x = 1
OIL
