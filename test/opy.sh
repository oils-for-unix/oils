#!/bin/bash
#
# Usage:
#   ./opy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

readonly SMALL_FILE='osh/word_compile_test.py'

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

cfg() {
  bin/opyc cfg $SMALL_FILE
}

run() {
  bin/opyc run $SMALL_FILE
}

eval_() {
  bin/opyc eval 'print(1+2)'
}

readonly -a PASSING=(
  #usage
  parse
  compile
  eval_
  run
  cfg
)

all-passing() {
  run-all "${PASSING[@]}"
}

# Use the release binary
# NOTE: This longer builds because of a hashlib dependency?
#
# $ make _bin/opy.ovm-dbg
# ...
# /Modules/_hashopenssl.c:938: undefined reference to `EVP_get_digestbyname'
# /home/andy/git/oilshell/oil/Python-2.7.13/Modules/_hashopenssl.c:938: undefined reference to `EVP_DigestInit'
# collect2: error: ld returned 1 exit status

run-for-release() {
  OPYC=_bin/opyc $0 run-all "${PASSING[@]}"
}

"$@"
