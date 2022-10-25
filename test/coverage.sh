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
  local out_dir=$1
  shift  # other args are suites

  local -a args=()
  local -a to_merge=()

  for suite in "$@"; do
    local prof_dir="_test/clang-coverage/$suite"
    local bin_dir="_bin/clang-coverage/$suite"

    # args for merging
    to_merge+=($prof_dir/*.profraw)

    # args for reporting (weird syntax)
    for b in $bin_dir/*; do
      if ! test -f $b; then  # skip mycpp/examples, which is a dir
        continue
      fi
      args+=(--object $b)
    done

  done

  local merged=$out_dir/ALL.profdata

  $CLANG_DIR/bin/llvm-profdata merge -sparse "${to_merge[@]}" \
    -o $merged

  # https://llvm.org/docs/CommandGuide/llvm-cov.html


  # Text report
  # $CLANG_DIR/bin/llvm-cov show --instr-profile $dir/ALL.profdata "${args[@]}"

  local html_dir=$out_dir/html
  mkdir -p $html_dir

  $CLANG_DIR/bin/llvm-cov show \
    --format html --output-dir $html_dir \
    --project-title "$suite" \
    --ignore-filename-regex '_test.cc$' \
    --ignore-filename-regex 'greatest.h$' \
    --ignore-filename-regex '_gen/' \
    --ignore-filename-regex 'mycpp/demo' \
    --ignore-filename-regex 'mycpp/examples' \
    --ignore-filename-regex 'mycpp/smartptr' \
    --ignore-filename-regex 'mycpp/cheney' \
    --ignore-filename-regex 'mycpp/bump_leak' \
    --ignore-filename-regex 'prebuilt/' \
    --show-instantiation-summary \
    --instr-profile $merged \
    "${args[@]}"

  #echo "Wrote $html"
  #ls -l --si -h $html  # 2.2 MB of HTML

  # Clang quirk: permissions of this tree aren't right.  Without this, the Soil
  # host won't be able to zip and publish them.

  # make sure dirs can be listed
  echo 'fix DIRS'
  find $html_dir -type d | xargs -- chmod --changes o+rx
  echo

  # make sure files are readable
  echo 'fix FILES'
  chmod --changes -R o+r $html_dir
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

unified-report() {
  # Merge 3 suites

  local out_dir=_test/clang-coverage/unified
  mkdir -p $out_dir

  html-report $out_dir \
    mycpp mycpp/examples cpp
}

log-files-index() {
  local dir=${1:-_test/clang-coverage}
  pushd $dir
  # Unit tests logs
  find . -name '*.log' \
    | gawk '{ printf("<a href=\"%s\">%s</a> <br/>\n", $0, $0); }' \
    > log-files.html
  popd
}

run-for-release() {
  ### Similar to cpp-coverage in soil/worker.sh

  mycpp/TEST.sh unit-test-coverage
  mycpp/TEST.sh examples-coverage
  cpp/TEST.sh coverage

  log-files-index _test/clang-coverage

  unified-report
}

"$@"

