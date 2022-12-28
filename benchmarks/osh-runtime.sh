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

runtime-task() {
  local out_dir=$1  # output
  local job_id=$2
  local host=$3
  local host_hash=$4
  local sh_path=$5
  local shell_hash=$6
  local task_type=$7
  local task_arg=$8

  local shell_name=$(basename $sh_path)

  # NOTE: For abuild, this isn't a directory name.
  local x=$(basename $task_arg)
  local task_label="${shell_name}-${shell_hash}__${x}"

  local times_out="$PWD/$out_dir/$host.$job_id.times.csv"
  local files_out_dir="$PWD/$out_dir/$host.$job_id.files/$task_label"
  mkdir -p $files_out_dir

  local -a TIME_PREFIX=(
    $PWD/benchmarks/time_.py \
    --append \
    --output $times_out \
    --rusage \
    --field "$host" --field "$host_hash" \
    --field "$shell_name" --field "$shell_hash" \
    --field "$task_type" --field "$task_arg"
  )

  echo
  echo "--- $sh_path $task_type $task_arg ---"
  echo

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

  "${TIME_PREFIX[@]}" -- "$sh_path" "${argv[@]}" > $files_out_dir/STDOUT.txt
}

# For each configure file.
print-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance "${SHELLS[@]}" $OIL_NATIVE_REGEX |
  while read job_id host_name host_hash sh_path shell_hash; do

    # Skip shells for speed
    case $sh_path in
      mksh|zsh|_bin/osh)
        log "--- osh-runtime.sh: Skipping $sh_path"
        continue
        ;;
    esac

    # Need $PWD/$sh_path because we must change dirs to configure.
    case $sh_path in
      /*)
        # It's already absolute -- do nothing.
        ;;
      */osh*)  # matches _bin/osh and _bin/cxx-opt/osh_eval.stripped
        sh_path=$PWD/$sh_path
        ;;
    esac
    local prefix="$job_id $host_name $host_hash $sh_path $shell_hash"

    # NOTE: 'abuild-help' is a dummy label.
    echo "$prefix" hello-world hello-world
    echo "$prefix" abuild abuild-help

    if test -n "${QUICKLY:-}"; then
      continue
    fi

    echo "$prefix" cpython cpython-configure

    for dir in "${TAR_SUBDIRS[@]}"; do
      echo "$prefix" configure $TAR_DIR/$dir
    done
  done
}

# input columns: 5 from provenence, then task_type / task_arg
readonly NUM_COLUMNS=7

# output columns
readonly HEADER='status,elapsed_secs,user_secs,sys_secs,max_rss_KiB,host_name,host_hash,shell_name,shell_hash,task_type,task_arg'

measure() {
  local provenance=$1
  local out_dir=${2:-$BASE_DIR/raw}  # could be ../benchmark-data
  local pattern=${3:-}

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

  local times_out="$out_dir/$prefix.times.csv"
  mkdir -p $BASE_DIR/{raw,stage1} $out_dir

  # Write Header of the CSV file that is appended to.
  echo $HEADER > $times_out

  local tasks=$BASE_DIR/tasks.txt
  print-tasks $provenance > $tasks

  # TODO: Get rid of 'xargs' because it makes failure harder to handle and see.
  # We're not exiting with 255 to abort xargs!

  # An empty pattern matches every line.
  time egrep "$pattern" $tasks |
    xargs -n $NUM_COLUMNS -- $0 runtime-task $out_dir ||
    die "*** Some tasks failed. ***"

  cp -v $provenance $out_dir
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1

  mkdir -p $out_dir

  local -a raw=()
  if test -n "$single_machine"; then
    local -a a=($raw_dir/$single_machine.*.times.csv)
    raw+=( ${a[-1]} )
  else
    # Globs are in lexicographical order, which works for our dates.
    local -a a=($raw_dir/$MACHINE1.*.times.csv)
    local -a b=($raw_dir/$MACHINE2.*.times.csv)
    raw+=( ${a[-1]} ${b[-1]} )
  fi

  local times_csv=$out_dir/times.csv
  csv-concat "${raw[@]}" > $times_csv
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
  csv2html $in_dir/shells.csv
  csv2html $in_dir/hosts.csv

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

  local label='no-host'

  local provenance
  provenance=$(soil-shell-provenance $label "${oil_bin[@]}")

  measure $provenance

  # Make it run on one machine
  stage1 '' $label

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
