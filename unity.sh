#!/usr/bin/env bash


echo "DOING FULL CLEAN"

build/clean.sh > /dev/null 2>&1
build/py.sh all > /dev/null 2>&1
./NINJA-config.sh > /dev/null 2>&1

echo "SETTING UP FOR FULL OSH_EVAL REBUILD"

build/dev.sh all > /dev/null 2>&1

echo "TIMING FULL REBUILD"

time build/dev.sh oil-cpp > /dev/null 2>&1

echo ""
echo "TIMING UNITY BUILD"
time clang++                \
      -I .                  \
      -Wno-invalid-offsetof \
      all.cc > /dev/null 2>&1
