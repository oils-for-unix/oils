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
source soil/common.sh  # find-dir-html
source test/common.sh
source test/tsv-lib.sh  # tsv-row

readonly BASE_DIR=_tmp/osh-runtime

# TODO: Move to ../oil_DEPS
readonly TAR_DIR=$PWD/_deps/osh-runtime  # Make it absolute

#
# Dependencies
#

# NOTE: Same list in oilshell.org/blob/run.sh.
tarballs() {
  cat <<EOF
tcc-0.9.26.tar.bz2
yash-2.46.tar.xz
ocaml-4.06.0.tar.xz
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
  local tsv_out=$1
  local files_base_dir=$2

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

    local files_out_dir="$PWD/$files_base_dir/files-$task_id"
    mkdir -v -p $files_out_dir

    local -a argv
    case $workload in
      hello-world)
        argv=( testdata/osh-runtime/hello_world.sh )
        ;;

      abuild-print-help)
        argv=( testdata/osh-runtime/abuild -h )
        ;;

      configure.cpython)
        argv=( testdata/osh-runtime/cpython-configure.sh 
               $sh_run_path $files_out_dir)  
        ;;

      configure.*)
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

        argv=( testdata/osh-runtime/configure-and-save.sh
               $sh_run_path $files_out_dir "$TAR_DIR/$conf_dir" )
        ;;

      *)
        die "Invalid workload $workload"
        ;;
    esac

    local -a time_argv=(
      time-tsv 
        --output $tsv_out --append 
        --rusage
        --field "$task_id"
        --field "$host_name" --field "$sh_path"
        --field "$workload"
        -- "$sh_path" "${argv[@]}"
    )

    local stdout_file="$files_out_dir/STDOUT.txt"

    # TODO: GC stats can be PER HOST
    local gc_stats_file=$BASE_DIR/raw/gc-$task_id.txt

    case $sh_path in
      */osh_eval*)
        OIL_GC_STATS_FD=99 "${time_argv[@]}" > $stdout_file 99> $gc_stats_file
        ;;
      *)
        "${time_argv[@]}" > $stdout_file
        ;;
    esac

    # NOTE: will have to join on (host_name, id)
    task_id=$((task_id + 1))

  done
}

print-tasks() {
  local host_name=$1  
  local osh_native=$2

  local -a workloads=(
    hello-world
    abuild-print-help

    configure.cpython
    configure.ocaml
    configure.tcc
    configure.yash
  )

  if test -n "${QUICKLY:-}"; then
    # Just do the first two
    workloads=(
      hello-world
      abuild-print-help
    )
  fi

  for sh_path in bash dash bin/osh $osh_native; do
    for workload in "${workloads[@]}"; do
      tsv-row $host_name $sh_path $workload
    done
  done
}

measure() {
  local host_name=$1  # 'no-host' or 'lenny'
  local host_job_id=$2
  local osh_native=$3  # $OSH_EVAL_NINJA_BUILD or $OSH_EVAL_BENCHMARK_DATA
  local out_dir=${4:-$BASE_DIR/raw}  # could be ../benchmark-data/osh-runtime

  # Dir structure:
  #
  # raw/
  #   times.tsv
  #   gc1.txt
  #   gc2.txt
  # stage1/
  #   times.tsv
  #   gc_stats.tsv
  #   provenance.tsv - benchmarks/provenance_to_tsv.py
  # stage2/
  #   elapsed.tsv
  #   elapsed.schema.tsv
  #   gc_stats.tsv
  #   gc_stats.schema.tsv

  local tsv_out="$out_dir/$host_job_id.times.tsv"
  local files_base_dir="$out_dir/$host_job_id.files"

  mkdir -p $BASE_DIR/{raw,stage1} $out_dir

  # Write header of the TSV file that is appended to.
  time-tsv -o $tsv_out --print-header \
    --rusage \
    --field task_id \
    --field host_name --field sh_path \
    --field workload

  # run-tasks outputs 3 things: raw times.tsv, per-task STDOUT and files, and
  # per-task GC stats

  # TODO: run-tasks can take $raw_dir, and then it outputs times.tsv, files/, and copies
  # _tmp/provenance.txt there

  print-tasks $host_name $osh_native | run-tasks $tsv_out $files_base_dir

  # TODO: call gc_stats_to_tsv.py here, adding HOST NAME, and put it in 'raw'
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1

  mkdir -p $out_dir

  local -a raw_times=()
  if test -n "$single_machine"; then

    # TODO: Change this to $BASE_DIR/raw.no-host.*/
    # That's the latest directory

    local -a a=($raw_dir/$single_machine.*.times.tsv)
    raw_times+=( ${a[-1]} )
  else
    # TODO: Change this to $BASE_DIR/raw.$MACHINE1.*/

    # Globs are in lexicographical order, which works for our dates.
    local -a a=($raw_dir/$MACHINE1.*.times.tsv)
    local -a b=($raw_dir/$MACHINE2.*.times.tsv)
    raw_times+=( ${a[-1]} ${b[-1]} )
  fi

  local times_tsv=$out_dir/times.tsv
  tsv-concat "${raw_times[@]}" > $times_tsv

  # TODO: 
  # - Add host column in 'measure' step
  # - concat multiple hosts in stage1
  benchmarks/gc_stats_to_tsv.py $raw_dir/gc-*.txt \
    > $BASE_DIR/stage1/gc_stats.tsv
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

Source code: [oil/benchmarks/osh-runtime.sh](https://github.com/oilshell/oil/tree/master/benchmarks/osh-runtime.sh)

### Elapsed Time by Shell (milliseconds)

Some benchmarks call many external tools, while some exercise the shell
interpreter itself.  Parse time is included.

Memory usage is measured in MB (powers of 10), not MiB (powers of 2).
EOF
  tsv2html $in_dir/elapsed.tsv

  cmark <<EOF
### Memory Usage (Max Resident Set Size in MB)
EOF
  tsv2html $in_dir/max_rss.tsv

  cmark <<EOF
### GC Stats
EOF
  tsv2html $in_dir/gc_stats.tsv

  cmark <<EOF
### Details of All Tasks
EOF
  tsv2html $in_dir/details.tsv


  cmark <<'EOF'

### Shell and Host Details
EOF
  tsv2html $in_dir/shells.tsv
  tsv2html $in_dir/hosts.tsv

  # Only show files.html link on a single machine
  if test -f $(dirname $in_dir)/files.html; then
    cmark <<'EOF'
---

[raw files](files.html)
EOF
  fi

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  ### Run it on just this machine, and make a report

  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  # TODO: This testdata should be baked into Docker image, or mounted
  download
  extract

  # TODO: could add _bin/cxx-bumpleak/osh_eval, but we would need to fix
  # $shell_name 
  local -a oil_bin=( $OSH_EVAL_NINJA_BUILD )
  ninja "${oil_bin[@]}"

  local single_machine='no-host'

  local job_id
  job_id=$(print-job-id)

  # Write _tmp/provenance.* and _tmp/{host,shell}-id
  shell-provenance-2 \
    $single_machine $job_id _tmp \
    bash dash bin/osh "${oil_bin[@]}"

  local host_job_id=$single_machine.$job_id

  measure $single_machine $host_job_id $OSH_EVAL_NINJA_BUILD

  # R uses the TSV version of the provenance.  TODO: concatenate per-host
  cp -v _tmp/provenance.tsv $BASE_DIR/stage1/provenance.tsv

  # Trivial concatenation for 1 machine
  stage1 '' $single_machine

  benchmarks/report.sh stage2 $BASE_DIR

  # Make _tmp/osh-parser/files.html, so index.html can potentially link to it
  find-dir-html _tmp/osh-runtime files

  benchmarks/report.sh stage3 $BASE_DIR
}

#
# Old
#

# Same problem as tcc
qemu-old() {
  local out_dir=$PWD/_tmp/qemu-old
  mkdir -p $out_dir
  configure-and-copy ~/src/qemu-1.6.0 $OSH_OVM $out_dir
}

# This doesn't work for ash either, because it uses the busybox pattern.  It
# says "exe: applet not found".  I guess yash doesn't configure under ash!
self-exe() {
  set +o errexit
  dash <<EOF
/proc/self/exe -V
EOF
  echo

  _bin/osh <<EOF
/proc/self/exe -V
EOF

  _tmp/shells/ash <<EOF
/proc/self/exe -V
EOF
}

"$@"
