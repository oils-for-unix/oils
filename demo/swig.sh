#!/usr/bin/env bash
#
# Can we use SWIG to wrap pure C++ in Python extension modules?
#
# This might be hard for our garbage collected types.
#
# Usage:
#   demo/swig.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install() {
  sudo apt-get install swig
}

# https://www.swig.org/Doc3.0/Python.html#Python

example() {
  ### Translate, compile, and run

  swig -python -c++ demo/swig/example.i

  # Two Output Files
  wc -l demo/swig/{example.py,example_wrap.*}
  ls -l demo/swig/

  set -x
  python2 demo/swig/setup.py build_ext --inplace

  python2 -c '
import _example
print(dir(_example))
print("fact(5) = %d" % _example.fact(5))
print("add(3, 4) = %d" % _example.add(3, 4))
print(_example.send)

# TODO: convert Str* to Python
# print(_example.send(42, "my payload"))

# Generates TypeError for you
# print("add(x, 4) = %d" % _example.add("3", 4))
'

}

clean-temp() {
  # Don't check in generated files
  rm -v demo/swig/{example.py,example_wrap.cxx}
}

# Hm doesn't work?
qsn() {
  #swig -o _tmp/qsn -python cpp/qsn.i
  swig -python -c++ cpp/qsn.i
  ls -l cpp/qsn*
  #ls -l _tmp/qsn
}

"$@"
