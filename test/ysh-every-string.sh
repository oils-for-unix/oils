#!/usr/bin/env bash
#
# Use every kind of YSH string
#
# Usage:
#   test/ysh-every-string.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

OSH=${OSH:-bin/osh}
YSH=${YSH:-bin/ysh}

# Disable for YSH
#shopt -s parse_sh_arith
source test/common.sh  # run-test-funcs

# OSH and YSH
test-legacy-osh-ysh() {
  for sh in $OSH $YSH; do
    log "     test-legacy with $sh"

    $sh <<'EOF'
  echo 'foo \ "
---'

  echo "foo \\ \" '
---"

  echo $'fo\x6f \\ \" \'
---'
EOF
  done
}

test-legacy-expr() {
  for sh in $YSH; do
    $sh <<'EOF'
  var x = 'foo
---'
  echo $x

  var x = "foo \\ \" '
---"
  echo $x

  # I guess this is useful for refactoring
  var x = $'f\u006f\x6f \\ \" \'
---'
  echo $x

EOF
done
}

test-legacy-multiline() {
  ### double-quoted is allowed to be multi-line in YSH

  for sh in $YSH; do
    $sh <<'EOF'
  echo """
  foo \\ \" '
  ---
  """

  var x = """
  foo \\ \" '
  ---
  """
  echo $x
EOF
done
}

test-raw() {
  ### r prefix for raw is allowed in YSH

  #for sh in $OSH $YSH; do
  for sh in $YSH; do
    $sh <<'EOF'
  # Command mode

  echo 'foo
---'

  echo r'foo
---'

  echo '''
  foo
  ---
  '''

  echo r'''
  foo
  ---
  '''

  # Expression mode

  var x = 'foo
---'
  echo $x

  var x = r'foo
---'
  echo $x

  var x = '''
  foo
  ---
  '''
  echo $x

  var x = r'''
  foo
  ---
  '''
  echo $x

EOF
  done
}

test-j8() {
  ### J8 strings are allowed in YSH

  # TODO: double to single quotes - Add " \' here

  #for sh in $OSH $YSH; do
  for sh in $YSH; do
    $sh <<'EOF'

  # Command mode

  echo u'fo\u{6f} \\ \"
---'

  echo b'f\u{6f}\y6f
---'

  # Leading indent of ---
  echo u'''
  fo\u{6f}
  ---
  '''

  echo b'''
  f\u{6f}\y6f
  ---
  '''

  # Expression mode

  #var x = u'fo\u{6f}
#---'
  #echo $x
EOF
  done
}

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  ninja _bin/cxx-asan/osh
  SH=_bin/cxx-asan/osh run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-every-string run-test-funcs
}

"$@"
