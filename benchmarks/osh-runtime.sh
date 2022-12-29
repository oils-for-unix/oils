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

source benchmarks/common.sh  # csv-concat
source soil/common.sh  # find-dir-html
source test/common.sh
source test/tsv-lib.sh  # tsv-row

readonly BASE_DIR=_tmp/osh-runtime

# TODO: Move to ../oil_DEPS
readonly TAR_DIR=$PWD/_deps/osh-runtime  # Make it absolute

#
# Dependencies
#

readonly -a TAR_SUBDIRS=( ocaml-4.06.0 tcc-0.9.26 yash-2.46 )

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
  time for f in $TAR_DIR/*.{bz2,xz}; do
    tar -x --directory $TAR_DIR --file $f 
  done
  ls -l $TAR_DIR
}

#
# Computation
#

run-tasks() {
  local tsv_out=$1
  local files_base_dir=$2

  local task_id=0
  while read -r maybe_host sh_path task_type task_arg; do

    local files_out_dir="$files_base_dir/files-$task_id"
    mkdir -p $files_out_dir

    local -a argv
    case $task_type in
      hello-world)  # NOTE: $task_arg unused.
        argv=( testdata/osh-runtime/hello_world.sh )
        ;;

      abuild)  # NOTE: $task_arg unused.
        argv=( testdata/osh-runtime/abuild -h )
        ;;

      cpython)  # NOTE: $task_arg unused.
        argv=( testdata/osh-runtime/cpython-configure.sh 
               $sh_path $files_out_dir) 
        ;;

      configure)
        local conf_dir=$task_arg
        argv=( testdata/osh-runtime/configure-and-save.sh
               $sh_path $files_out_dir $conf_dir )
        ;;

      *)
        die "Invalid task type $task_type"
        ;;
    esac

    local -a time_argv=(
      time-tsv 
        --output $tsv_out --append 
        --rusage
        --field "$task_id"
        --field "$maybe_host" --field "$sh_path"
        --field "$task_type" --field "$task_arg"
        -- "$sh_path" "${argv[@]}"
    )

    local stdout_file="$files_out_dir/STDOUT.txt"

    # TODO: GC stats can be PER HOST
    local gc_stats_file=$BASE_DIR/raw/gc-$task_id.txt

    case $sh_path in
      */osh_eval*)
        # TODO: need join ID
        OIL_GC_STATS_FD=99 "${time_argv[@]}" > $stdout_file 99>$gc_stats_file
        ;;
      *)
        "${time_argv[@]}" > $stdout_file
        ;;
    esac

    # NOTE: will have to join on (maybe_host, id)
    task_id=$((task_id + 1))

  done
}

# For each configure file.
print-tasks() {
  local maybe_host=$1  

  for sh_path in bash dash bin/osh $OSH_EVAL_NINJA_BUILD; do
    # NOTE: 'abuild-help' is a dummy label.
    tsv-row $maybe_host $sh_path hello-world hello-world
    tsv-row $maybe_host $sh_path abuild abuild-help

    if test -n "${QUICKLY:-}"; then
      continue
    fi

    tsv-row $maybe_host $sh_path cpython cpython-configure

    for dir in "${TAR_SUBDIRS[@]}"; do
      tsv-row $maybe_host $sh_path configure $TAR_DIR/$dir
    done
  done
}

measure() {
  # TODO: just change this to prefix
  local provenance=$1
  local maybe_host=$2  # e.g. 'lenny' or 'no-host'
  local out_dir=${3:-$BASE_DIR/raw}  # could be ../benchmark-data/osh-runtime

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  # TODO:
  # - output times.tsv AND gc_stats.tsv, which is joined
  # - factor out gc_stats_to_tsv from benchmarks/gc
  # - provenance can be joined later?  It shouldn't be preserved in print-tasks
  #   - output _tmp/osh-runtime/stage1/provenance.tsv then?
  #
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
  #   elasped.tsv
  #   elasped.schema.tsv
  #   gc_stats.tsv
  #   gc_stats.schema.tsv

  local tsv_out="$out_dir/$prefix.times.tsv"
  local files_base_dir="$out_dir/$prefix.files"

  #set -x
  mkdir -p $BASE_DIR/{raw,stage1} $out_dir

  # Write header of the TSV file that is appended to.
  time-tsv -o $tsv_out --print-header \
    --rusage \
    --field task_id \
    --field host_name --field sh_path \
    --field task_type --field task_arg

  # run-tasks outputs 3 things: raw times.tsv, per-task STDOUT and files, and
  # per-task GC stats

  print-tasks $maybe_host | run-tasks $tsv_out $files_base_dir

  # R uses the TSV version of the provenance.
  # TODO: we don't even need the text version
  cp -v ${provenance%%.txt}.tsv $BASE_DIR/stage1/provenance.tsv
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1

  mkdir -p $out_dir

  local -a raw=()
  if test -n "$single_machine"; then
    local -a a=($raw_dir/$single_machine.*.times.tsv)
    raw+=( ${a[-1]} )
  else
    # Globs are in lexicographical order, which works for our dates.
    local -a a=($raw_dir/$MACHINE1.*.times.tsv)
    local -a b=($raw_dir/$MACHINE2.*.times.tsv)
    raw+=( ${a[-1]} ${b[-1]} )
  fi

  local times_csv=$out_dir/times.tsv
  csv-concat "${raw[@]}" > $times_csv

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
  csv2html $in_dir/elapsed.csv

  cmark <<EOF
### Memory Usage (Max Resident Set Size in MB)
EOF
  csv2html $in_dir/max_rss.csv

  cat <<EOF

    <h3>Shell and Host Details</h3>
EOF
  tsv2html $in_dir/shells.tsv
  tsv2html $in_dir/hosts.tsv

  cmark <<'EOF'
---

[raw files](files.html)
EOF

  cat <<EOF
  </body>
</html>
EOF
}

soil-shell-provenance() {
  ### Only measure shells in the Docker image

  local label=$1
  shift

  # This is a superset of shells; see filter-provenance
  # - _bin/osh isn't available in the Docker image, so use bin/osh instead

  benchmarks/id.sh shell-provenance "$label" bash dash bin/osh "$@"
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
  local -a oil_bin=(_bin/cxx-opt/osh_eval.stripped)
  ninja "${oil_bin[@]}"

  local maybe_host='no-host'

  local provenance
  provenance=$(soil-shell-provenance $maybe_host "${oil_bin[@]}")

  measure $provenance $maybe_host

  # Make it run on one machine
  stage1 '' $maybe_host

  benchmarks/report.sh stage2 $BASE_DIR
  benchmarks/report.sh stage3 $BASE_DIR

  # Index of raw files
  find-dir-html _tmp/osh-runtime files
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
