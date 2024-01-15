#!/usr/bin/env bash
#
# Run continuous build tasks.
#
# Usage:
#   soil/worker.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source soil/common.sh
source test/tsv-lib.sh

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
os-info          soil/diagnose.sh os-info    -
dump-env         soil/diagnose.sh dump-env   -
EOF
}

raw-vm-tasks() {
  # The perf tool depends on a specific version of a kernel, so run it outside
  # a container.

  # (task_name, script, action, result_html)
  cat <<EOF
os-info          soil/diagnose.sh os-info         -
dump-env         soil/diagnose.sh dump-env        -
perf-install     benchmarks/perf.sh soil-install  -
wait-for-tarball soil/wait.sh for-cpp-tarball         -
test-tar         devtools/release-native.sh test-tar  -
perf-profiles    benchmarks/perf.sh soil-run      _tmp/perf/index.html
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
os-info          soil/diagnose.sh os-info    -
dump-env         soil/diagnose.sh dump-env   -
py-source        build/py.sh py-source       -
check-types      pea/TEST.sh check-types     -
run-tests        pea/TEST.sh run-tests       -
parse-all        pea/TEST.sh parse-all       -
yaks             yaks/TEST.sh soil-run       -
EOF
}

dev-minimal-tasks() {
  ### Print tasks for the 'dev-minimal' build

  # repo overview is suggested by README.md

  # (task_name, script, action, result_html)
  cat <<EOF
os-info             soil/diagnose.sh os-info                     -
dump-env            soil/diagnose.sh dump-env                    -
build-minimal       build/py.sh minimal                          -
repo-overview       metrics/source-code.sh overview              -
lint                test/lint.sh soil-run                        -
asdl-types          asdl/TEST.sh check-types                     -
oil-types           devtools/types.sh soil-run                   -
unit                test/unit.sh soil-run                        -
arena               test/arena.sh soil-run                       -
parse-errors        test/parse-errors.sh soil-run-py             -
runtime-errors      test/runtime-errors.sh run-all-with-osh      -
ysh-runtime-errors  test/ysh-runtime-errors.sh soil-run          -
ysh-parse-errors    test/ysh-parse-errors.sh soil-run-py         -
ysh-every-string    test/ysh-every-string.sh soil-run-py         -
ysh-large           ysh/run.sh soil-run                          -
json-errors         data_lang/json-errors.sh soil-run-py         -
link-busybox-ash    test/spec-bin.sh link-busybox-ash            -
osh-minimal         test/spec-py.sh osh-minimal                  _tmp/spec/osh-minimal/index.html
headless            client/run.sh soil-run-py                    -
EOF
}

interactive-tasks() {
  ### Print tasks for the 'interactive' build

  # TODO: also run interactive suite with osh-cpp

# TODO: Why does the needs-terminal suite hang in Docker?  It doesn't hang in an interactive Docker session.
#
# needs-terminal   test/spec-py.sh needs-terminal-all  _tmp/spec/needs-terminal-py/index.html
#
# https://oilshell.zulipchat.com/#narrow/stream/121539-oil-dev/topic/Spec.20Tests.20for.20Interactive.20Parsing

  cat <<EOF
os-info          soil/diagnose.sh os-info            -
dump-env         soil/diagnose.sh dump-env           -
py-all-and-ninja soil/worker.sh py-all-and-ninja     -
interactive-osh  test/spec-py.sh interactive-osh     _tmp/spec/interactive-osh/index.html
nohup            test/nohup.sh soil-run              -
process-table    test/process-table.sh soil-run      _tmp/process-table/index.html
stateful         test/stateful.sh soil-run           _tmp/spec/stateful/index.html
EOF

}

wild-tasks() {
  ### Print tasks for the 'wild' build

  # (task_name, script, action, result_html)
  cat <<EOF
os-info          soil/diagnose.sh os-info              -
dump-env         soil/diagnose.sh dump-env             -
wait-for-tarball soil/wait.sh for-cpp-tarball          -
test-tar         devtools/release-native.sh test-tar   -
linecount        metrics/tarball.sh linecount-oils-cpp -
wild             test/wild.sh soil-run                 _tmp/wild-www/index.html
EOF
}

benchmarks-tasks() {
  # (task_name, script, action, result_html)

  cat <<EOF
os-info          soil/diagnose.sh os-info              -
dump-env         soil/diagnose.sh dump-env             -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
id-test          benchmarks/id-test.sh soil-run        -
native-code      metrics/native-code.sh oils-for-unix  _tmp/metrics/oils-for-unix/index.html
osh-parser       benchmarks/osh-parser.sh soil-run     _tmp/osh-parser/index.html
osh-runtime      benchmarks/osh-runtime.sh soil-run    _tmp/osh-runtime/index.html
vm-baseline      benchmarks/vm-baseline.sh soil-run    _tmp/vm-baseline/index.html
compute          benchmarks/compute.sh soil-run        _tmp/compute/index.html
gc               benchmarks/gc.sh soil-run             _tmp/gc/index.html
mycpp-benchmarks benchmarks/mycpp.sh soil-run          _tmp/mycpp-examples/index.html
EOF
}

benchmarks2-tasks() {
  # Note: id-test doesn't run in 'other-tests' because 'gawk' isn't in that image
  cat <<EOF
os-info          soil/diagnose.sh os-info              -
dump-env         soil/diagnose.sh dump-env             -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
dev-shell-test   build/dev-shell-test.sh soil-run      -
gc-cachegrind    benchmarks/gc-cachegrind.sh soil-run  _tmp/gc-cachegrind/index.html
uftrace          benchmarks/uftrace.sh soil-run        _tmp/uftrace/index.html
EOF
}

cpp-spec-tasks() {
  # (task_name, script, action, result_html)

  cat <<EOF
os-info          soil/diagnose.sh os-info              -
dump-env         soil/diagnose.sh dump-env             -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
oils-cpp-smoke   build/native.sh soil-run              -
osh-all          test/spec-cpp.sh osh-all              _tmp/spec/osh-cpp/compare.html
ysh-all          test/spec-cpp.sh ysh-all              _tmp/spec/ysh-cpp/compare.html
ysh-py           test/spec-py.sh ysh-all-serial        _tmp/spec/ysh-py/index.html
EOF
}

cpp-tarball-tasks() {

  # Note: build-times task requires _build/oils.sh
  # It's a bit redundant with test-tar

  cat <<EOF
os-info          soil/diagnose.sh os-info    -
dump-env         soil/diagnose.sh dump-env   -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
oils-cpp-smoke   build/native.sh soil-run              -
make-tar         devtools/release-native.sh make-tar   _release/oils-for-unix.tar
build-times      build/native.sh measure-build-times   -
EOF

# build-times is a good enough test
# test-tar         devtools/release-native.sh test-tar   -
#
# Note: tarball is deployed outside the container

}

cpp-small-tasks() {

  # TODO: remove tarball

  # Build the tarball toward the beginning
  cat <<EOF
os-info          soil/diagnose.sh os-info    -
dump-env         soil/diagnose.sh dump-env   -
py-all-and-ninja soil/worker.sh py-all-and-ninja       -
oils-cpp-smoke   build/native.sh soil-run              -
cpp-unit         test/cpp-unit.sh soil-run             _test/cpp-unit.html
headless         client/run.sh soil-run-cpp            -
asan             test/asan.sh soil-run                 -
ltrace           test/ltrace.sh soil-run               -
micro-syntax     doctools/micro-syntax.sh soil-run     -
src-tree         doctools/src-tree.sh soil-run         _tmp/src-tree-www/index.html
line-counts      metrics/source-code.sh write-reports  _tmp/metrics/line-counts/index.html
preprocessed     metrics/source-code.sh preprocessed   _tmp/metrics/preprocessed/index.html
mycpp-examples   mycpp/TEST.sh soil-run                _test/mycpp-examples.html
parse-errors     test/parse-errors.sh soil-run-cpp     -
ysh-parse-errors test/ysh-parse-errors.sh soil-run-cpp -
ysh-every-string test/ysh-every-string.sh soil-run-cpp -
ysh-large        ysh/run.sh soil-run-cpp               -
json-errors      data_lang/json-errors.sh soil-run-cpp -
EOF
}

cpp-coverage-tasks() {
  # dep notes: hnode_asdl.h required by expr_asdl.h in mycpp/examples

  cat <<EOF
os-info                 soil/diagnose.sh os-info    -
dump-env                soil/diagnose.sh dump-env   -
py-all-and-ninja        soil/worker.sh py-all-and-ninja                 -
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
  # - py-all needed to crawl dependencies to make tarball.
  # - quick-oil-tarball deletes _release, so we have to put docs afterward

  # (task_name, script, action, result_html)
  cat <<EOF
os-info           soil/diagnose.sh os-info    -
dump-env          soil/diagnose.sh dump-env   -
py-all            build/py.sh all                        -
syscall-by-code   test/syscall.sh by-code                _tmp/syscall/by-code.txt
syscall-by-input  test/syscall.sh by-input               _tmp/syscall/by-input.txt
osh-spec          test/spec-py.sh osh-all-serial         _tmp/spec/osh-py/index.html
gold              test/gold.sh soil-run                  -
osh-usage         test/osh-usage.sh soil-run             -
tools-deps        test/tools-deps.sh soil-run            -
make-tarball      devtools/release.sh quick-oil-tarball  _release/oil.tar
test-tarball      devtools/release.sh test-oil-tar       -
ysh-ovm-tarball   test/spec-py.sh ysh-ovm-tarball        _tmp/spec/ysh-py/index.html
docs              build/doc.sh soil-run                  _release/VERSION/index.html
ref-check         build/doc.sh ref-check                 -
EOF
}

# Reuse ovm-tarball container
app-tests-tasks() {

  cat <<EOF
os-info           soil/diagnose.sh os-info             -
dump-env          soil/diagnose.sh dump-env            -
py-all            build/py.sh all                      -
ble-clone         test/ble.sh clone                    -
ble-build         test/ble.sh build                    -
ble-bash-suite    test/ble.sh bash-suite               -
ble-test-osh-py   test/ble.sh run-tests-osh-py         -
wait-for-tarball  soil/wait.sh for-cpp-tarball         -
test-tar          devtools/release-native.sh test-tar  -
ble-test-osh-cpp  test/ble.sh run-tests-osh-cpp        -
EOF

# This doesn't work
# ble-test-osh-bash test/ble.sh run-tests-osh-bash       -
}

# TODO: Most of these should be Ninja tasks.
# Other tests:
# find-test, xargs-test, pgen2-test, web/table/csv2html-test.sh
# Probably should start using a shell test framework too.
other-tests-tasks() {
  cat <<EOF
os-info                soil/diagnose.sh os-info    -
dump-env               soil/diagnose.sh dump-env   -
build-minimal          build/py.sh minimal                        -
configure-test         ./configure-test.sh soil_run               -
time-test              benchmarks/time-test.sh soil-run           -
tsv-lib-test           test/tsv-lib-test.sh soil-run              -
ysh-ify                test/ysh-ify.sh soil-run                   -
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
os-info          soil/diagnose.sh os-info    -
dump-env         soil/diagnose.sh dump-env   -
maybe-merge      soil/maybe-merge.sh soil-run     -
EOF
}

run-tasks() {
  ### Run the tasks on stdin and write _tmp/soil/INDEX.tsv.
  local job_name=$1
  local out_dir=$2  # should already exist
  local tty=$3

  mkdir -p $out_dir/logs

  # So we can run benchmarks/time_.py.  
  # 2023-02-28: Images like soil-wild based off the new soil-common no longer
  # have 'cc'.  Instead they use a wedge.
  if command -v cc > /dev/null; then
    build/py.sh time-helper
  else
    echo 'test time-tsv'
    time-tsv -o /tmp/echo.tsv --append -- echo hi

    echo '/tmp/echo.tsv:'
    cat /tmp/echo.tsv
  fi

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
    local -a timeout=(timeout 900)
    local stdin_tty=''

    case $script in
      test/process-table.sh)
        # Workaround for weird interaction, see
        # $ test/process-table.sh timeout-issue
        timeout=()
        ;;
      test/nohup.sh)
        # Only run test/nohup.sh with TTY.  For some reason build/py.sh all hangs
        # with $tty?
        stdin_tty=$tty
        ;;
    esac

    local -a argv=(
      time-tsv -o $tsv --append
        --field $task_name --field $script --field $action
        --field $result_html -- 
        "${timeout[@]}" "$script" "$action"
    )

    # Run task and save status
    set +o errexit
    if test -n "$stdin_tty"; then
      # explicitly connect TTY, e.g. for soil/interactive
      "${argv[@]}" > $log_path 2>&1 < $stdin_tty
    else
      "${argv[@]}" > $log_path 2>&1
    fi
    status=$?
    set -o errexit

    if test "$status" -gt "$max_status"; then
      max_status=$status
    fi

    # Show the last line
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

  # Hack: Assign job_id and write it to the status file.  Other jobs can poll
  # for completion of this job and access its resources.

  local job_id
  job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  # e.g. _soil-jobs/dummy.status.txt
  echo "$max_status $job_id" > _soil-jobs/$job_name.status.txt
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

disable-git-errors() {

  # 2023-02: The build started failing because of the permissions we set in
  # soil/host-shim.sh mount-perms.
  #
  # The issue is that the guest needs to be able to write to the Docker mount
  # of the repo.  I think it may have been related to podman vs. Docker.
  # Should check if mount-perms is necessary in both places.
  #
  # git fails unless we have this workaround.

  # https://stackoverflow.com/questions/72978485/git-submodule-update-failed-with-fatal-detected-dubious-ownership-in-repositor

  # https://github.blog/2022-04-12-git-security-vulnerability-announced/

  #git config --global --add safe.directory '*'

  git config --global --add safe.directory /home/uke/oil
}

job-main() {
  local job_name=$1

  local out_dir=_tmp/soil

  # Report for debugging
  export EXTRA_MYCPP_ARGS='--stack-roots-warn 16'

  log-context 'job-main'
  mkdir -v -p $out_dir
  ls -l -d $out_dir

  disable-git-errors

  save-metadata $job_name $out_dir

  local captured

  set +o errexit
  captured=$(tty)
  status=$?
  set -o errexit

  if test $status -eq 0; then
    echo "TTY = $captured"
    local tty=$captured
  else
    echo "captured = $captured"
    local tty=''  # clear the output
  fi
  echo

  ${job_name}-tasks | run-tasks $job_name $out_dir "$tty"
}

JOB-dummy() { job-main 'dummy'; }
JOB-raw-vm() { job-main 'raw-vm'; }

JOB-dev-minimal() { job-main 'dev-minimal'; }
JOB-interactive() { job-main 'interactive'; }

JOB-other-tests() { job-main 'other-tests'; }

JOB-pea() { job-main 'pea'; }

JOB-ovm-tarball() { job-main 'ovm-tarball'; }
JOB-app-tests() { job-main 'app-tests'; }

JOB-cpp-coverage() { job-main 'cpp-coverage'; }
JOB-cpp-small() { job-main 'cpp-small'; }
JOB-cpp-tarball() { job-main 'cpp-tarball'; }
JOB-cpp-spec() { job-main 'cpp-spec'; }

JOB-benchmarks() { job-main 'benchmarks'; }
JOB-benchmarks2() { job-main 'benchmarks2'; }

JOB-wild() { job-main 'wild'; }

JOB-maybe-merge() { job-main 'maybe-merge'; }

list-jobs() {
  compgen -A function | grep -- '^JOB-' | sed 's/^JOB-//g' | egrep -v 'maybe-merge'
}

"$@"
