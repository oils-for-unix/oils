#!/usr/bin/env bash

# Character classes in globs used by Alpine's abuild.
for d in 'python2-dev>=2.6' python3-dev flex bison bzip2-dev zlib-dev; do
  echo ${d%%[<>=]*}
done
