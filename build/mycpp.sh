#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

CPPFLAGS='-std=c++11 -O2 -g'

demo() {
  build/dev.sh oil-asdl-to-cpp
  c++ -o _bin/oil_mycpp $CPPFLAGS \
    -I _devbuild/gen-cpp \
    -I _devbuild/gen \
    -I mycpp \
    bin/oil.cc mycpp/mylib.cc -lstdc++

  echo '___'

  _bin/oil_mycpp
}

"$@"
