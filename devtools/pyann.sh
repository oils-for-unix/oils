#!/usr/bin/env bash
#
# Usage:
#   types/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh

readonly PY_PATH='.:vendor/'  # note: could consolidate with other scripts

#
# PyAnnotate
#

# 2025-01: These old versions could go in vendor/ !  They're still useful.

# September 2019
PYANN_URL='https://files.pythonhosted.org/packages/0d/26/2f68c02fae0b88d9cefdbc632edad190d61621b5660c72c920be1e52631e/pyannotate-1.2.0.tar.gz'

# October 2019
MYPY_EXT_URL='https://files.pythonhosted.org/packages/63/60/0582ce2eaced55f65a4406fc97beba256de4b7a95a0034c6576458c6519f/mypy_extensions-0.4.3.tar.gz'

# December 2024
SIX_URL='https://files.pythonhosted.org/packages/94/e7/b2c673351809dca68a0e064b6af791aa332cf192da575fd474ed7d6f16a2/six-1.17.0.tar.gz'

download-tarballs() {
  wget --no-clobber --directory _tmp \
    $PYANN_URL $MYPY_EXT_URL $SIX_URL
}

extract-tarballs() {
  pushd _tmp
  for t in pyannotate-*.gz mypy_extensions-*.gz six-*.gz; do
    echo "=== $t"
    tar -x -z < $t
  done
  popd
}

PY_PATH_2='.:vendor:_tmp/pyannotate-1.2.0:_tmp/mypy_extensions-0.4.3:_tmp/six-1.17.0'

collect-types() {
  # syntax error?
  # Now it requires python3
  # I think we need an old release
  # https://pypi.org/project/mypy-extensions/
  # https://github.com/python/mypy_extensions
  # TypedDict
  # https://github.com/python/mypy_extensions/commit/e0c6670e05a87507d59b7d3a0aa2eec88e9813b0

  #local ext=~/git/oils-for-unix/mypy_extensions
  #export PYTHONPATH=".:$PYANN_REPO:$ext"

  PYTHONPATH=$PY_PATH_2 devtools/pyann_driver.py "$@"

  ls -l type_info.json
  wc -l type_info.json
}

peek-type-info() {
  grep path type_info.json | sort | uniq -c | sort -n
}

apply-types() {
  local json=${1:-type_info.json}
  shift
  #local -a files=(osh/builtin_comp.py core/completion.py)
  local -a files=(doctools/*.py)

  #local -a files=( $(cat _tmp/osh-parse-src.txt | grep -v syntax_asdl.py ) )

  # Use -w to write files
  set -x
  PYTHONPATH=$PY_PATH_2 \
    python2 -m pyannotate_tools.annotations --type-info $json "${files[@]}" "$@"

  #pyann-patched --type-info $json "${files[@]}" "$@"
}

"$@"
