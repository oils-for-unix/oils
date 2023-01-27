#!/usr/bin/env bash
#
# Run continuous build tasks.
#
# Usage:
#   soil/worker.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source soil/common.sh
source test/tsv-lib.sh

dump-timezone() {

  # On Travis:
  #  /usr/share/zoneinfo/UTC
  # On my machine
  #  /usr/share/zoneinfo/America/Los_Angeles

  read md5 _ <<< $(md5sum /etc/localtime)
  log "md5 = $md5"
  find /usr/share/zoneinfo -type f | xargs md5sum | grep $md5
}

dump-versions() {
  set +o errexit

  set -x
  which python2
  python2 -V

  which python3
  python3 -V
}

dump-locale() {
  set -x
  # show our locale
  locale

  # show all locales
  locale -a
}

dump-hardware() {
  egrep '^(processor|model name)' /proc/cpuinfo
  echo

  egrep '^Mem' /proc/meminfo
  echo

  df -h
  echo
}

dump-distro() {
  local path=/etc/lsb-release
  if test -f $path; then
    cat $path
  else
    echo "$path doesn't exist"
  fi
  echo

  apt-cache policy r-base-core
}

dump-user-host() {
  echo -n 'whoami = '
  whoami
  echo

  echo "PWD = $PWD"
  echo

  echo -n 'hostname = '
  hostname
  echo

  uname -a
  echo

  who
  echo
}

py-all-and-ninja() {
  ### baseline for most tasks

  build/py.sh all
  ./NINJA-config.sh
}

ninja-config() {
  ./NINJA-config.sh
}

dummy-tasks() {
  ### Print tasks that execute quickly

  # (task_name, script, action, result_html)
  cat <<EOF
dump-distro      soil/worker.sh dump-distro     -
dump-user-host   soil/worker.sh dump-user-host  -
dump-env         soil/worker.sh dump-env        -
dump-timezone    soil/worker.sh dump-timezone   -
dump-locale      soil/worker.sh dump-locale     -
dump-hardware    soil/worker.sh dump-hardware   -
EOF
}

pea-tasks() {
  ### Print tasks for the 'pea' build

  # We need a later version of Python 3 / MyPy both to type check and
  # to parse

  # Run py-source so we can type check generated code
  # We need to type check more than we translate

  # (task_name, script, action, result_html)
  cat <<EOF
dump-user-host      soil/worker.sh dump-user-host     -
dump-locale         soil/worker.sh dump-locale        -
py-source           build/py.sh py-source             -
check-types         pea/TEST.sh check-types           -
run-tests           pea/TEST.sh run-tests             -
parse-all           pea/TEST.sh parse-all             -
EOF
}

dev-minimal-tasks() {
  ### Print tasks for the 'dev-minimal' build

  # repo overview is suggested by README.md

  # (task_name, script, action, result_html)
  cat <<EOF
dump-user-host      soil/worker.sh dump-user-host                -
build-minimal       build/py.sh minimal                          -
repo-overview       metrics/source-code.sh overview              -
lint                test/lint.sh soil-run                        -
asdl-types          asdl/TEST.sh check-types                     -
oil-types           devtools/types.sh soil-run                   -
unit                test/unit.sh soil-run                        -
stateful            test/stateful.sh soil-run                    _tmp/spec/stateful/index.html
arena               test/arena.sh soil-run                       -
parse-errors        test/parse-errors.sh soil-run-py             -
runtime-errors      test/runtime-errors.sh run-all-with-osh      -
oil-runtime-errors  test/oil-runtime-errors.sh soil-run          -
oil-spec            test/spec.sh oil-all-serial                  _tmp/spec/oil-language/oil.html
tea-spec            test/spec.sh tea-all-serial                  _tmp/spec/tea-language/tea.html
oil-large           oil_lang/run.sh soil-run                     -
tea-large           tea/run.sh soil-run                          -
link-busybox-ash    test/spec.sh link-busybox-ash                -
osh-minimal         test/spec.sh osh-minimal                     _tmp/spec/survey/osh-minimal.html
EOF
}

# Redefinition for quicker cloud debugging
DISABLED_dev-minimal-tasks() {
  cat <<EOF
build-minimal       build/py.sh minimal           -
interactive         test/interactive.sh soil      -
EOF
}

benchmarks-tasks() {
  # (task_name, script, action, result_html)

  # Note: id-test doesn't run in 'other-tests' because 'gawk' isn't in that image

  cat <<EOF
dump-versions    soil/worker.sh dump-versions          -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
id-test          benchmarks/id-test.sh soil-run        -
osh-parser       benchmarks/osh-parser.sh soil-run     _tmp/osh-parser/index.html
osh-runtime      benchmarks/osh-runtime.sh soil-run    _tmp/osh-runtime/index.html
vm-baseline      benchmarks/vm-baseline.sh soil-run    _tmp/vm-baseline/index.html
compute          benchmarks/compute.sh soil-run        _tmp/compute/index.html
gc               benchmarks/gc.sh soil-run             _tmp/gc/index.html
mycpp-benchmarks benchmarks/mycpp.sh soil-run          _tmp/mycpp-examples/index.html
EOF
}

cpp-spec-tasks() {
  # (task_name, script, action, result_html)

  # BUG: oil-cpp can't run with 'build/py.sh minimal' because 'fastlex' isn't built
  # can't run with 'build/py.sh all' because we don't have cmark

  cat <<EOF
dump-versions    soil/worker.sh dump-versions          -
build-minimal    build/py.sh minimal                   -
HACK-fastlex     build/py.sh fastlex                   -
ninja-config     soil/worker.sh ninja-config           -
oils-cpp-smoke   build/native.sh oils-cpp-smoke        -
spec-cpp         test/spec-cpp.sh soil-run             _tmp/spec/cpp/osh-summary.html
EOF
}

cpp-small-tasks() {
  # Note: mycpp-benchmarks runs benchmarks SERIALLY with ninja -j 1, and makes HTML
  # And then we have correctness for mycpp-translator.  Somewhat redundant but
  # it's OK for now.

  cat <<EOF
dump-versions    soil/worker.sh dump-versions          -
build-minimal    build/py.sh minimal                   -
ninja-config     soil/worker.sh ninja-config           -
cpp-unit         test/cpp-unit.sh soil-run             _test/cpp-unit.html
oils-cpp-smoke   build/native.sh oils-cpp-smoke        -
line-counts      metrics/source-code.sh write-reports  _tmp/metrics/line-counts/index.html
preprocessed     metrics/source-code.sh preprocessed   _tmp/metrics/preprocessed/index.html
native-code      metrics/native-code.sh oils-for-unix     _tmp/metrics/oils-for-unix/index.html
mycpp-examples   mycpp/TEST.sh soil-run                _test/mycpp-examples.html
parse-errors     test/parse-errors.sh soil-run-cpp     -
make-tar         devtools/release-native.sh make-tar   _release/oils-for-unix.tar
test-tar         devtools/release-native.sh test-tar   -
EOF
}

cpp-coverage-tasks() {
  # dep notes: hnode_asdl.h required by expr_asdl.h in mycpp/examples

  cat <<EOF
dump-hardware           soil/worker.sh dump-hardware                    -
build-minimal           build/py.sh minimal                             -
ninja-config            soil/worker.sh ninja-config                     -
extract-clang           deps/from-binary.sh extract-clang-in-container  -
mycpp-unit-coverage     mycpp/TEST.sh unit-test-coverage                _test/clang-coverage/mycpp/html/index.html
mycpp-examples-coverage mycpp/TEST.sh examples-coverage                 _test/clang-coverage/mycpp/examples/html/index.html
cpp-coverage            cpp/TEST.sh coverage                            _test/clang-coverage/cpp/html/index.html
unified-coverage        test/coverage.sh unified-report                 _test/clang-coverage/unified/html/index.html
compare-gcc-clang       metrics/native-code.sh compare-gcc-clang        _tmp/metrics/compare-gcc-clang.txt
EOF
}

ovm-tarball-tasks() {
  ### Print tasks for the 'ovm-tarball' build

  # notes:
  # - dev-all needed to crawl dependencies to make tarball.
  # - The 'tour' also depends on buildings docs.
  # - 'all-markdown' could be published.
  # - build/py.sh all does 'all-help', so we don't need it explicitly

  # (task_name, script, action, result_html)
  cat <<EOF
dump-locale       soil/worker.sh dump-locale             -
py-all            build/py.sh all                        -
yajl              build/py.sh yajl-release               -
tour              build/doc.sh tour                      _release/VERSION/doc/oil-language-tour.html
all-markdown      build/doc.sh all-markdown              -
syscall-by-code   test/syscall.sh by-code                _tmp/syscall/by-code.txt
syscall-by-input  test/syscall.sh by-input               _tmp/syscall/by-input.txt
osh-spec          test/spec.sh soil-run-osh              _tmp/spec/survey/osh.html
gold              test/gold.sh soil-run                  -
osh-usage         test/osh-usage.sh soil-run             -
oshc-deps         test/oshc-deps.sh soil-run             -
make-tarball      devtools/release.sh quick-oil-tarball  _release/oil.tar
test-tarball      devtools/release.sh test-oil-tar       -
EOF
}

# Reuse ovm-tarball container
app-tests-tasks() {
  cat <<EOF
py-all            build/py.sh all                         -
yajl              build/py.sh yajl-release                -
ble-clone         test/ble.sh clone                       -
ble-build         test/ble.sh build                       -
ble-test          test/ble.sh run-tests                   -
EOF
}

# TODO: Most of these should be Ninja tasks.
# Other tests:
# find-test, xargs-test, pgen2-test, web/table/csv2html-test.sh
# Probably should start using a shell test framework too.
other-tests-tasks() {
  cat <<EOF
dump-distro            soil/worker.sh dump-distro                 -
dump-locale            soil/worker.sh dump-locale                 -
build-minimal          build/py.sh minimal                        -
configure-test         ./configure-test.sh soil_run               -
time-test              benchmarks/time-test.sh soil-run           -
tsv-lib-test           test/tsv-lib-test.sh soil-run              -
ysh-prettify           test/ysh-prettify.sh soil-run              -
R-test                 devtools/R-test.sh soil-run                -
xargs-test             test/other.sh xargs-test                   -
csv2html-test          test/other.sh csv2html-test                -
oil-python-symbols     metrics/source-code.sh oil-python-symbols  -
opyc                   test/opyc.sh soil-run                      -
opy-count-lines        opy/soil.sh count-lines                    -
test-gold              opy/soil.sh test-gold                      -
build-oil-repo         opy/soil.sh build-oil-repo                 -
regtest-compile        opy/soil.sh regtest-compile                -
EOF
}

tests-todo() {
  ### More tests to add
  find . -name '_*' -a -prune -o -name '*-test.sh' -a -print

  # pgen2/pgen2-test.sh seems mostly broken
}

# Redefinition for quicker cloud debugging
maybe-merge-tasks() {
  cat <<EOF
dump-env            soil/worker.sh dump-env           -
dump-user-host      soil/worker.sh dump-user-host     -
maybe-merge         soil/maybe-merge.sh soil-run      -
EOF
}

run-tasks() {
  ### Run the tasks on stdin and write _tmp/soil/INDEX.tsv.
  local job_name=$1
  local out_dir=$2  # should already exist

  mkdir -p $out_dir/logs

  # So we can always run benchmarks/time_.py.  TODO: Use Ninja for deps.
  build/py.sh time-helper

  # For the later deploy step to pick up
  date +%s > $out_dir/task-run-start-time.txt

  # This data can go on the dashboard index
  local tsv=$out_dir/INDEX.tsv
  rm -f $tsv

  local status
  local max_status=0

  while read task_name script action result_html; do
    log "--- task: $task_name ---"

    local log_path=$out_dir/logs/$task_name.txt 

    # 15 minutes per task
    # One of the longest tasks is test/spec-cpp, which takes around 420 seconds
    # TODO: should have a configurable timeout
    local timeout_secs=900

    set +o errexit
    time-tsv -o $tsv --append --time-fmt '%.2f' \
      --field $task_name --field $script --field $action \
      --field $result_html -- \
      timeout $timeout_secs $script $action >$log_path 2>&1
    status=$?
    set -o errexit

    if test "$status" -gt "$max_status"; then
      max_status=$status
    fi

    # show the last line
    echo
    tsv-row status elapsed task script action result_html
    tail -n 1 $tsv
    echo
    log "status=$status max_status=$max_status"
  done

  log '--- done ---'
  ls -l $out_dir
  wc -l $out_dir/logs/*

  # This suppressed the deployment of logs, which we don't want.  So all our
  # Travis builds succeed?  But then we can't use their failure notifications
  # (which might be OK).
  if false; then
    # exit with the maximum exit code.
    awk '
    BEGIN { max = 0 }
          { if ($1 > max) { max = $1 } }
    END   { exit(max) }
    ' $tsv
  fi

  # To fail later.  Important: this dir persists across jobs; it's NOT removed
  # by 'host-shim.sh job-reset'.
  mkdir -p _soil-jobs

  # e.g. _soil-jobs/dummy.status.txt
  echo $max_status > _soil-jobs/$job_name.status.txt
}

save-metadata() {
  ### Write metadata files to be saved as JSON

  # NOTE: host-shim.sh also writes image-pull-time.txt

  local job_name=$1
  local meta_dir=$2

  echo "$job_name" > $meta_dir/job-name.txt

  # command to show current branch
  # This does NOT work in detached HEAD!  Travis puts the branch in an env
  # variable, but sr.ht doesn't.
  # git rev-parse --abbrev-ref HEAD > $meta_dir/git-branch.txt

  git log -n 1 --pretty='format:%H' > $meta_dir/commit-hash.txt

  # ISO 8601 format
  # Note: this can get confused with rebases.  Two different commits can have
  # the same date.
  git log -n 1 --pretty='format:%aI' > $meta_dir/commit-date.txt

  git log -n 1 --pretty='format:%s' > $meta_dir/commit-line.txt  # "subject"
}

job-main() {
  local job_name=$1

  local out_dir=_tmp/soil

  log-context 'job-main'
  mkdir -v -p $out_dir
  ls -l -d $out_dir

  save-metadata $job_name $out_dir

  ${job_name}-tasks | run-tasks $job_name $out_dir
}

JOB-dummy() { job-main 'dummy'; }

JOB-dev-minimal() { job-main 'dev-minimal'; }

JOB-other-tests() { job-main 'other-tests'; }

JOB-pea() { job-main 'pea'; }

JOB-cpp-coverage() { job-main 'cpp-coverage'; }

# For now, these share a container image
JOB-ovm-tarball() { job-main 'ovm-tarball'; }
JOB-app-tests() { job-main 'app-tests'; }

# For now, these share a container image
JOB-cpp-small() { job-main 'cpp-small'; }
JOB-cpp-spec() { job-main 'cpp-spec'; }
JOB-benchmarks() { job-main 'benchmarks'; }

JOB-maybe-merge() { job-main 'maybe-merge'; }

list-jobs() {
  compgen -A function | grep -- '^JOB-' | sed 's/^JOB-//g' | egrep -v 'maybe-merge'
}

"$@"
