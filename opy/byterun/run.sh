#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

make-pyc() {
  mkdir -p _tmp/
  pushd _tmp/

  cat >prog.py <<EOF
print "hi from prog"
EOF
  python -c 'import prog'
  /bin/ls -al


  popd

}

py() {
  # Doesn't accept pyc file?
  ./__main__.py _tmp/prog.py
}

pyc() {
  ./__main__.py -c _tmp/prog.pyc
}

unit() {
  export PYTHONPATH=.
  for t in ./test_*.py; do
    echo $t
    $t

    # This exposes the dependency on 'six' that we don't want.
    #python -S $t
  done
}

"$@"
