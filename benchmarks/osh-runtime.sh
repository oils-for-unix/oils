#!/bin/bash
#
# Test scripts found in the wild for both correctness and performance.
#
# Usage:
#   ./runtime.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source benchmarks/common.sh  # csv-concat

readonly BASE_DIR=_tmp/osh-runtime
readonly TAR_DIR=$PWD/$BASE_DIR  # Make it absolute

# Use the compiled version.  Otherwise /proc/self/exe is the Python
# interpreter, which matters for yash's configure script!
readonly OSH=$PWD/_bin/osh

#
# Dependencies
#

# NOTE: Same list in oilshell.org/blob/run.sh.
files() {
  cat <<EOF
tcc-0.9.26.tar.bz2
yash-2.46.tar.xz
ocaml-4.06.0.tar.xz
uftrace-0.8.1.tar.gz
EOF
}

conf-dirs() {
  cat <<EOF
$TAR_DIR/ocaml-4.06.0
$TAR_DIR/tcc-0.9.26
$TAR_DIR/uftrace-0.8.1
$TAR_DIR/yash-2.46
EOF
}


download() {
  files | xargs -n 1 -I {} --verbose -- \
    wget --directory $TAR_DIR 'https://www.oilshell.org/blob/testdata/{}'
}

extract() {
  time for f in $TAR_DIR/*.{gz,bz2,xz}; do
    tar -x --directory $TAR_DIR --file $f 
  done
  ls -l $TAR_DIR
}

#
# Computation
#

readonly PY27_DIR=$PWD/Python-2.7.13

cpython-configure() {
  local sh_path=${1:-bash}
  local out_dir=${2:-$BASE_DIR/${sh_path}-cpython-configure}
  mkdir -p $out_dir

  pushd $out_dir
  time $sh_path $PY27_DIR/configure || true
  popd

  tree $out_dir
}

# 18.9 seconds vs 11 seconds above.
osh-cpython-configure() {
  cpython-configure $PWD/_bin/osh $BASE_DIR/osh-cpython-configure
}

conf-task() {
  local raw_dir=$1  # output
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

  local times_out="$PWD/$raw_dir/$host.$job_id.times.csv"
  local vm_out_dir="$PWD/$raw_dir/$host.$job_id.virtual-memory"
  local files_out_dir="$PWD/$raw_dir/$host.$job_id.files/$task_label"
  mkdir -p $vm_out_dir $files_out_dir

  local time_tool=$PWD/benchmarks/time.py
  local -a TIME_PREFIX=(
    $time_tool \
    --output $times_out \
    --field "$host" --field "$host_hash" \
    --field "$shell_name" --field "$shell_hash" \
    --field "$task_type" --field "$task_arg"
  )

  # Can't use array because of set -u bug!!!  Only fixed in bash 4.4.
  extra_args=''
  if test "$shell_name" = 'osh'; then
    local pdump="${vm_out_dir}/${task_label}__parser.txt"
    local rdump="${vm_out_dir}/${task_label}__runtime.txt"
    extra_args="--parser-mem-dump $pdump --runtime-mem-dump $rdump"

    # Should we add a field here to say it has VM stats?
  fi

  echo
  echo "--- $sh_path $task_type $task_arg ---"
  echo

  case $task_type in
    abuild)
      # NOTE: $task_arg unused.

      "${TIME_PREFIX[@]}" -- \
        "$sh_path" $extra_args benchmarks/testdata/abuild -h \
        > $files_out_dir/STDOUT.txt
      ;;

    configure)
      local conf_dir=$task_arg

      pushd $conf_dir >/dev/null
      touch __TIMESTAMP

      "${TIME_PREFIX[@]}" -- "$sh_path" $extra_args ./configure \
        > $files_out_dir/STDOUT.txt

      find . -type f -newer __TIMESTAMP \
        | xargs -I {} -- cp --verbose {} $files_out_dir
      popd >/dev/null
      ;;

    *)
      die "Invalid task type $task_type"
      ;;
  esac
}

# TODO:
# - Add Python's configure -- same or different?
# - Unify abuild -h -- time it
# - --runtime-dump-mem and rename to --parser-dump-mem
#
# benchmark_name,shell,out_dir
# abuild-h
# X-configure
# config.status?
#
# Yeah need to come up with a name.  Not just conf-dirs.
# $dir-configure

# Do I add host/host_id?  Or just host_label and rely on provenance?

# Turn this into write-tasks?
# And then run-tasks?  run-all?

# Yeah it should be 
# osh-parser.sh write-tasks
# osh-runtime.sh write-tasks
# virtual-memory.sh write-tasks
#
# And then auto.sh run-tasks?  Then you can have consistent logging?

# For each configure file.
print-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | while read \
    job_id host_name host_hash sh_path shell_hash; do

    case $sh_path in
      mksh|zsh|bin/osh)
        log "--- Skipping $sh_path"
        continue
        ;;
    esac

    # Need $PWD/$sh_path because we must change dirs to configure.
    case $sh_path in
      */osh)
        sh_path=$PWD/$sh_path
        ;;
    esac

    # NOTE: 'help' is a dummy label.
    echo $job_id $host_name $host_hash $sh_path $shell_hash abuild help

    conf-dirs | xargs -n 1 -- \
      echo $job_id $host_name $host_hash $sh_path $shell_hash configure

  done
}

readonly HEADER='status,elapsed_secs,host_name,host_hash,shell_name,shell_hash,task_type,task_arg'
readonly NUM_COLUMNS=7  # 5 from provenence, then task_type / task_arg

all() {
  local provenance=$1
  local raw_dir=${2:-_tmp/osh-runtime/raw}
  #local base_dir=${2:-../benchmark-data/osh-parser}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  local times_out="$raw_dir/$prefix.times.csv"
  mkdir -p $BASE_DIR/{raw,stage1}

  # Write Header of the CSV file that is appended to.
  echo $HEADER > $times_out

  local tasks=$raw_dir/tasks.txt
  print-tasks $provenance > $tasks

  # Run them all
  #head -n 2 $tasks |
  time cat $tasks |
    xargs -n $NUM_COLUMNS -- $0 conf-task $raw_dir ||
    die "Some tasks failed."

  cp -v $provenance $raw_dir
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local out_dir=$BASE_DIR/stage1

  mkdir -p $out_dir

  # Just copy for now
  cp -v $raw_dir/*.times.csv $out_dir/times.csv

  local vm_csv=$out_dir/virtual-memory.csv

  local -a x=($raw_dir/lisa.*.virtual-memory)
  benchmarks/virtual_memory.py osh-runtime ${x[-1]} > $vm_csv

  #local raw_dir=${1:-../benchmark-data/osh-parser}
}

stage2() {
  local out=$BASE_DIR/stage2
  mkdir -p $out

  benchmarks/report.R osh-runtime $BASE_DIR/stage1 $out

  tree $out
}

_print-report() {
  local in_dir=$1
  local base_url='../../web/table'

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>OSH Runtime Performance</title>
    <script type="text/javascript" src="$base_url/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="$base_url/table-sort.css" />
    <link rel="stylesheet" type="text/css" href="benchmarks.css" />

  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>OSH Runtime Performance</h2>

    <h3>Elapsed Time by Shell (milliseconds)</h3>

    <p>Some benchmarks call many external tools, while some exercise the shell
    interpreter itself.  Parse time is included.</p>
EOF
  csv2html $in_dir/times.csv

  cat <<EOF
    <h3>Memory Used to Run</h3>

    <p>Running under <code>osh-ovm</code>.</p>
EOF
  web/table/csv2html.py $in_dir/virtual-memory.csv

  cat <<EOF

    <h3>Shell and Host Details</h3>
EOF
  csv2html $in_dir/shells.csv
  csv2html $in_dir/hosts.csv

  cat <<EOF
  </body>
</html>
EOF
}

stage3() {
  local out=$BASE_DIR/index.html
  mkdir -p $(dirname $out)
  _print-report $BASE_DIR/stage2 > $out
  cp -v benchmarks/benchmarks.css $BASE_DIR
  echo "Wrote $out"
}

report() {
  stage1
  stage2
  stage3
}

#
# Non-configure scripts
#

abuild-h() {
  local out_dir=_tmp/osh-runtime
  mkdir -p $out_dir

  # TODO: Should test the correctness too.
  local out=$out_dir/abuild-h-times.csv

  echo 'status,elapsed_secs,sh_path' > $out
  for sh_path in bash dash mksh zsh $OSH; do
    benchmarks/time.py --output $out --field "$sh_path" -- \
      $sh_path benchmarks/testdata/abuild -h
  done
}

#
# Misc
#

# Same problem as tcc
qemu-old() {
  local out_dir=$PWD/_tmp/qemu-old
  mkdir -p $out_dir
  configure-and-copy ~/src/qemu-1.6.0 $OSH $out_dir
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
