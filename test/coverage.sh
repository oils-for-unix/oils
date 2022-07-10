#!/usr/bin/env bash
#
# Usage:
#   test/coverage.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/common.sh  # $CLANG_DIR

html-report() {
  local suite=${1:-mycpp-unit}

  local prof_dir="_test/clang-coverage/$suite"
  local bin_dir="_bin/clang-coverage/$suite"

  local merged=$prof_dir/ALL.profdata
  $CLANG_DIR/bin/llvm-profdata merge -sparse $prof_dir/*.profraw \
    -o $merged

  # https://llvm.org/docs/CommandGuide/llvm-cov.html

  local -a args=()
  for b in $bin_dir/*; do
    args+=(--object $b)
  done

  # Text report
  # $CLANG_DIR/bin/llvm-cov show --instr-profile $dir/ALL.profdata "${args[@]}"

  local html_dir=$prof_dir/html
  mkdir -p $html_dir

  $CLANG_DIR/bin/llvm-cov show \
    --format html --output-dir $html_dir \
    --project-title "$suite" \
    --ignore-filename-regex '_test.cc$' \
    --ignore-filename-regex 'greatest.h$' \
    --ignore-filename-regex 'mycpp/demo' \
    --ignore-filename-regex '_test/' \
    --ignore-filename-regex '_build/' \
    --show-instantiation-summary \
    --instr-profile $merged \
    "${args[@]}"

  #echo "Wrote $html"
  #ls -l --si -h $html  # 2.2 MB of HTML

  # Clang quirk: permissions of this tree aren't right.  Without this, the Soil
  # host won't be able to zip and publish them.

  # make sure files are readable
  echo 'fix FILES'
  chmod --changes -R o+r $html_dir
  echo

  # make sure dirs can be listed
  echo 'fix DIRS'
  find $html_dir -type d | xargs -- chmod --changes o+x
  echo

  # 2.4 MB of HTML
  du --si -s $html_dir
  echo

  $CLANG_DIR/bin/llvm-cov report --instr-profile $merged "${args[@]}"

  # Also TODO: leaky_bindings_test, etc.
}

llvm-cov-help() {
  # many options for filtering
  # --name-allowlist

  $CLANG_DIR/bin/llvm-cov show --help
}

"$@"

