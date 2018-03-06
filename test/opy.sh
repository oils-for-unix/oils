#!/bin/bash
#
# Usage:
#   ./opy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# Can't be readonly because we override it below?  Gah.
#readonly OPYC=${OPYC:-bin/opyc}
OPYC=${OPYC:-bin/opyc}

readonly TMP_DIR=_tmp/opy-test
mkdir -p $TMP_DIR


usage() {
  set +o errexit

  bin/opy_.py
  test $? -eq 2 || fail

  bin/opy_.py --version
  test $? -eq 0 || fail

  #bin/opy
  #test $? -eq 2 || fail

  bin/opyc
  test $? -eq 2 || fail

  bin/opyc invalid
  test $? -eq 2 || fail

  # TODO: --help, --version everywhere.

  #bin/opy_.py --help
  #test $? -eq 0 || fail

  #bin/opy --help
  #test $? -eq 0 || fail

  #bin/opy --version
  #test $? -eq 0 || fail

  bin/opyc --help
  test $? -eq 0 || fail

  #bin/opyc --version
  #test $? -eq 0 || fail
}

parse() {
  cat >$TMP_DIR/hello.py <<EOF
print(1+2)
EOF
  $OPYC parse $TMP_DIR/hello.py
}

compile() {
  cat >$TMP_DIR/loop.py <<EOF
for i in xrange(4):
  print(i*i)
EOF

  $OPYC compile $TMP_DIR/loop.py $TMP_DIR/loop.opyc

  # We can run it with CPython now, but later we won't able to.
  python $TMP_DIR/loop.opyc > out.txt
  diff out.txt - <<EOF || fail
0
1
4
9
EOF
}

readonly -a PASSING=(
  usage
  parse
  compile
)

all-passing() {
  run-all "${PASSING[@]}"
}

# Use the release binary
run-for-release() {
  OPYC=_bin/opyc $0 run-all "${PASSING[@]}"
}

"$@"
