#!/usr/bin/env bash
#
# Test scripts found in the wild for both correctness and performance.
#
# Usage:
#   benchmarks/osh-runtime.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/common.sh  # tsv-concat
source benchmarks/id.sh  # print-job-id
source test/common.sh
source test/tsv-lib.sh  # tsv-row

readonly BASE_DIR=_tmp/osh-runtime

# TODO: Move to ../oil_DEPS
readonly TAR_DIR=$PWD/_deps/osh-runtime  # Make it absolute

#
# Dependencies
#

readonly PY27_DIR=$PWD/Python-2.7.13

# NOTE: Same list in oilshell.org/blob/run.sh.
tarballs() {
  cat <<EOF
tcc-0.9.26.tar.bz2
yash-2.46.tar.xz
ocaml-4.06.0.tar.xz
util-linux-2.40.tar.xz
EOF
}

download() {
  mkdir -p $TAR_DIR
  tarballs | xargs -n 1 -I {} --verbose -- \
    wget --no-clobber --directory $TAR_DIR 'https://www.oilshell.org/blob/testdata/{}'
}

extract() {
  set -x
  time for f in $TAR_DIR/*.{bz2,xz}; do
    tar -x --directory $TAR_DIR --file $f 
  done
  set +x

  ls -l $TAR_DIR
}

#
# Computation
#

run-tasks() {
  local raw_out_dir=$1
  raw_out_dir="$PWD/$raw_out_dir"  # because we change dirs

  # Bug fix for dynamic scoping!
  local host_name sh_path workload

  local task_id=0
  while read -r host_name sh_path workload; do

    log "*** $host_name $sh_path $workload $task_id"

    local sh_run_path
    case $sh_path in
      /*)  # Already absolute
        sh_run_path=$sh_path
        ;;
      */*)  # It's relative, so make it absolute
        sh_run_path=$PWD/$sh_path
        ;;
      *)  # 'dash' should remain 'dash'
        sh_run_path=$sh_path
        ;;
    esac

    local working_dir=''
    local files_out_dir="$raw_out_dir/files-$task_id"
    mkdir -v -p $files_out_dir

    local save_new_files=''

    local -a argv
    case $workload in
      hello-world)
        argv=( testdata/osh-runtime/hello_world.sh )
        ;;

      bin-true)
        argv=( testdata/osh-runtime/bin_true.sh )
        ;;

      abuild-print-help)
        argv=( testdata/osh-runtime/abuild -h )
        ;;

      configure.cpython)
        argv=( $PY27_DIR/configure )
        working_dir=$files_out_dir
        ;;

      configure.util-linux)
        # flag needed to avoid sqlite3 dep error message
        argv=( $TAR_DIR/util-linux-2.40/configure --disable-liblastlog2 )
        working_dir=$files_out_dir
        ;;

      configure.*)
        argv=( ./configure )

        local conf_dir
        case $workload in
          *.ocaml)
            conf_dir='ocaml-4.06.0'
            ;;
          *.tcc)
            conf_dir='tcc-0.9.26'
            ;;
          *.yash)
            conf_dir='yash-2.46'
            ;;
          *)
            die "Invalid workload $workload"
        esac

        # These are run in-tree?
        working_dir=$TAR_DIR/$conf_dir
        ;;

      *)
        die "Invalid workload $workload"
        ;;
    esac

    local -a time_argv=(
      time-tsv 
        --output "$raw_out_dir/times.tsv" --append 
        --rusage
        --rusage-2
        --field "$task_id"
        --field "$host_name" --field "$sh_path"
        --field "$workload"
        -- "$sh_run_path" "${argv[@]}"
    )

    local stdout_file="$files_out_dir/STDOUT.txt"
    local gc_stats_file="$raw_out_dir/gc-$task_id.txt"

    # Maybe change dirs
    if test -n "$working_dir"; then
      pushd "$working_dir"
    fi

    if test -n "$save_new_files"; then
      touch __TIMESTAMP
    fi

    # Run it, possibly with GC stats
    case $sh_path in
      *_bin/*/osh)
        OILS_GC_STATS_FD=99 "${time_argv[@]}" > $stdout_file 99> $gc_stats_file
        ;;
      *)
        "${time_argv[@]}" > $stdout_file
        ;;
    esac

    if test -n "$save_new_files"; then
      echo "COPYING to $files_out_dir"
      find . -type f -newer __TIMESTAMP \
        | xargs -I {} -- cp --verbose {} $files_out_dir
    fi

    # Restore dir
    if test -n "$working_dir"; then
      popd
    fi

    task_id=$((task_id + 1))
  done
}

# Sorted by priority for test-oils.sh osh-runtime --num-shells 3

readonly -a ALL_WORKLOADS=(
  hello-world
  bin-true

  configure.cpython
  configure.util-linux
  configure.ocaml
  configure.tcc
  configure.yash

  abuild-print-help
)

print-workloads() {
  ### for help

  for w in "${ALL_WORKLOADS[@]}"; do
    echo "    $w"
  done
}

print-tasks() {
  local host_name=$1  
  local osh_native=$2

  if test -n "${QUICKLY:-}"; then
    workloads=(
      hello-world
      bin-true
      #configure.util-linux
      #abuild-print-help
    )
  else
    workloads=( "${ALL_WORKLOADS[@]}" )
  fi

  for sh_path in bash dash bin/osh $osh_native; do
    for workload in "${workloads[@]}"; do
      tsv-row $host_name $sh_path $workload
    done
  done
}

print-tasks-xshar() {
  local host_name=$1  
  local osh_native=$2

  local num_iters=${3:-1}
  local num_shells=${4:-1}
  local num_workloads=${5:-1}

  for i in $(seq $num_iters); do

    local s=0
    for sh_path in $osh_native bash dash; do

      local w=0
      for workload in "${ALL_WORKLOADS[@]}"; do
        tsv-row $host_name $sh_path $workload

        w=$(( w + 1 ))  # cut off at specified workloads
        if test $w -eq $num_workloads; then
          break
        fi
      done

      s=$(( s + 1 ))  # cut off as specified shells
      if test $s -eq $num_shells; then
        break
      fi

    done
  done
}

run-tasks-wrapper() {
  ### reads tasks from stdin

  local host_name=$1  # 'no-host' or 'lenny'
  local raw_out_dir=$2

  mkdir -v -p $raw_out_dir

  local tsv_out="$raw_out_dir/times.tsv"

  # Write header of the TSV file that is appended to.
  time-tsv -o $tsv_out --print-header \
    --rusage \
    --rusage-2 \
    --field task_id \
    --field host_name --field sh_path \
    --field workload

  # reads tasks from stdin
  # run-tasks outputs 3 things: raw times.tsv, per-task STDOUT and files, and
  # per-task GC stats
  run-tasks $raw_out_dir

  # Turn individual files into a TSV, adding host
  benchmarks/gc_stats_to_tsv.py $raw_out_dir/gc-*.txt \
    | tsv-add-const-column host_name "$host_name" \
    > $raw_out_dir/gc_stats.tsv

  cp -v _tmp/provenance.tsv $raw_out_dir
}

measure() {
  ### For release and CI
  local host_name=$1  # 'no-host' or 'lenny'
  local raw_out_dir=$2  # _tmp/osh-runtime or ../../benchmark-data/osh-runtime
  local osh_native=$3  # $OSH_CPP_NINJA_BUILD or $OSH_CPP_BENCHMARK_DATA

  print-tasks "$host_name" "$osh_native" \
    | run-tasks-wrapper "$host_name" "$raw_out_dir"
}

stage1() {
  local base_dir=${1:-$BASE_DIR}  # _tmp/osh-runtime or ../benchmark-data/osh-runtime
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1  # _tmp/osh-runtime
  mkdir -p $out_dir

  # Globs are in lexicographical order, which works for our dates.

  local -a raw_times=()
  local -a raw_gc_stats=()
  local -a raw_provenance=()

  if test -n "$single_machine"; then
    local -a a=( $base_dir/raw.$single_machine.* )

    raw_times+=( ${a[-1]}/times.tsv )
    raw_gc_stats+=( ${a[-1]}/gc_stats.tsv )
    raw_provenance+=( ${a[-1]}/provenance.tsv )

  else
    local -a a=( $base_dir/raw.$MACHINE1.* )
    local -a b=( $base_dir/raw.$MACHINE2.* )

    raw_times+=( ${a[-1]}/times.tsv ${b[-1]}/times.tsv )
    raw_gc_stats+=( ${a[-1]}/gc_stats.tsv ${b[-1]}/gc_stats.tsv )
    raw_provenance+=( ${a[-1]}/provenance.tsv ${b[-1]}/provenance.tsv )
  fi

  tsv-concat "${raw_times[@]}" > $out_dir/times.tsv

  tsv-concat "${raw_gc_stats[@]}" > $out_dir/gc_stats.tsv

  tsv-concat "${raw_provenance[@]}" > $out_dir/provenance.tsv
}

print-report() {
  local in_dir=$1

  benchmark-html-head 'OSH Runtime Performance'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF

  cmark <<'EOF'
## OSH Runtime Performance

Source code: [benchmarks/osh-runtime.sh](https://github.com/oilshell/oil/tree/master/benchmarks/osh-runtime.sh)

- [Elapsed Time](#elapsed-time)
- [Minor Page Faults](#page-faults)
- [Memory Usage](#memory-usage)
- [GC Stats](#gc-stats)
- [rusage Details](#rusage-details)
- [More Details](#more-details)
- [Shell and Host](#shell-and-host)

[Raw files](-wwz-index)

<a name="elapsed-time" />

### Elapsed Time by Shell (milliseconds)

Some benchmarks call many external tools, while some exercise the shell
interpreter itself.
EOF
  tsv2html $in_dir/elapsed.tsv

  cmark <<EOF
<a name="page-faults" />

### Minor Page Faults
EOF

  tsv2html $in_dir/page_faults.tsv

  cmark <<EOF
<a name="memory-usage" />

### Memory Usage (Max Resident Set Size in MB)

Memory usage is measured in MB (powers of 10), not MiB (powers of 2).
EOF
  tsv2html $in_dir/max_rss.tsv

  cmark <<EOF
<a name="gc-stats" />

### GC Stats
EOF
  tsv2html $in_dir/gc_stats.tsv

  cmark <<EOF
<a name="rusage-details" />

### rusage Details
EOF
  tsv2html $in_dir/details.tsv

  cmark <<EOF
<a name="more-details" />

### More Details
EOF
  tsv2html $in_dir/details_io.tsv

  cmark <<'EOF'
<a name="shell-and-host" />

### Shell and Host
EOF
  tsv2html $in_dir/shells.tsv
  tsv2html $in_dir/hosts.tsv

  cmark <<'EOF'

  </body>
</html>
EOF
}

test-oils-run() {
  local osh=$1
  local job_id=$2
  local host_name=$3

  # flags passed by caller
  local num_iters=${4:-1}
  local num_shells=${5:-1}
  local num_workloads=${6:-1}

  local time_py=${XSHAR_DIR:-$REPO_ROOT}/benchmarks/time_.py
  $time_py --tsv --rusage -- \
    $osh -c 'echo "smoke test: hi from benchmarks/osh-runtime.sh"'

  # Fresh build
  rm -r -f -v $BASE_DIR _tmp/{shell,host}-id

  # Write _tmp/provenance.* and _tmp/{host,shell}-id
  shell-provenance-2 \
    $host_name $job_id _tmp \
    bash dash $osh

  # e.g. 2024-05-01__10-11-12.ci-vm-name
  local raw_out_dir="$BASE_DIR/raw"
  mkdir -p $raw_out_dir

  # Similar to 'measure', for soil-run and release
  print-tasks-xshar $host_name $osh $num_iters $num_shells $num_workloads \
    | tee $BASE_DIR/tasks.txt

  run-tasks-wrapper $host_name $raw_out_dir < $BASE_DIR/tasks.txt
  echo

  # Note: 'stage1' in soil-run is a trivial concatenation, so we can create input for
  # benchmarks/report.R.  We don't need that here
}

soil-run() {
  ### Run it on just this machine, and make a report

  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  # TODO: This testdata should be baked into Docker image, or mounted
  download
  extract

  # could add _bin/cxx-bumpleak/oils-for-unix, although sometimes it's slower
  local -a osh_bin=( $OSH_CPP_NINJA_BUILD )
  ninja "${osh_bin[@]}"

  local single_machine='no-host'

  local job_id
  job_id=$(print-job-id)

  # Write _tmp/provenance.* and _tmp/{host,shell}-id
  shell-provenance-2 \
    $single_machine $job_id _tmp \
    bash dash bin/osh "${osh_bin[@]}"

  local host_job_id="$single_machine.$job_id"
  local raw_out_dir="$BASE_DIR/raw.$host_job_id"
  mkdir -p $raw_out_dir $BASE_DIR/stage1

  measure $single_machine $raw_out_dir $OSH_CPP_NINJA_BUILD

  # Trivial concatenation for 1 machine
  stage1 '' $single_machine

  benchmarks/report.sh stage2 $BASE_DIR

  benchmarks/report.sh stage3 $BASE_DIR
}

#
# Debugging
#

compare-cpython() {
  #local -a a=( ../benchmark-data/osh-runtime/*.lenny.2024* )
  local -a a=( ../benchmark-data/osh-runtime/*.hoover.2024* )

  # More of a diff here?
  #local -a a=( ../benchmark-data/osh-runtime/*.broome.2023* )
  # less diff here
  #local -a a=( ../benchmark-data/osh-runtime/*.lenny.2023* )

  local dir=${a[-1]}

  echo $dir

  head -n 1 $dir/times.tsv
  fgrep 'configure.cpython' $dir/times.tsv

  local bash_id=2
  local dash_id=8
  local osh_py_id=14
  local osh_cpp_id=20

  set +o errexit

  local out_dir=_tmp/cpython-configure
  mkdir -p $out_dir

  echo 'bash vs. dash'
  diff -u --recursive $dir/{files-2,files-8} > $out_dir/bash-vs-dash.txt
  diffstat $out_dir/bash-vs-dash.txt
  echo

  echo 'bash vs. osh-py'
  diff -u --recursive $dir/{files-2,files-14} > $out_dir/bash-vs-osh-py.txt
  diffstat $out_dir/bash-vs-osh-py.txt
  echo

  echo 'bash vs. osh-cpp'
  diff -u --recursive $dir/{files-2,files-20} > $out_dir/bash-vs-osh-cpp.txt
  diffstat $out_dir/bash-vs-osh-cpp.txt
  echo

  return

  diff -u $dir/{files-2,files-20}/STDOUT.txt
  echo

  diff -u $dir/{files-2,files-20}/pyconfig.h
  echo

  cdiff -u $dir/{files-2,files-20}/config.log
  echo
}

"$@"
