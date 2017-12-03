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

readonly TAR_DIR=$PWD/_tmp/osh-runtime

# Use the compiled version.  Otherwise /proc/self/exe is the Python
# interpreter, which matters for yash's configure script!
readonly OSH=$PWD/_bin/osh

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

configure-and-copy() {
  local src_dir=$1
  local sh_path=$2
  local out_dir=$3

  mkdir -p $out_dir

  # These hand-written configure scripts must be run from their own directory,
  # unlike autoconf's scripts.

  pushd $src_dir >/dev/null
  touch __TIMESTAMP
  #$OSH -x ./configure

  #benchmarks/time.py --output $out_csv
  $sh_path ./configure >$out_dir/STDOUT.txt

  echo
  echo "--- NEW FILES ---"
  echo

  find . -type f -newer __TIMESTAMP | xargs -I {} --verbose -- cp {} $out_dir
  popd >/dev/null
}

configure-one() {
  local append_out=$1  # times
  local vm_out_dir=$2  # pass to virtual memory
  local sh_path=$3
  local shell_hash=$4
  local conf_dir=$5

  local prog_label=$(basename $conf_dir)
  local sh_label=$(basename $sh_path)
  local out_dir=$TAR_DIR/raw/${prog_label}__${sh_label}

  # TODO: benchmarks/time.
  # Except we don't want to time the copying.

  configure-and-copy $conf_dir $sh_path $out_dir
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

all() {
  local provenance=$1
  local base_dir=${2:-_tmp/osh-runtime/raw}
  #local base_dir=${2:-../benchmark-data/osh-parser}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local job_id=${name%.provenance.txt}  # strip suffix

  local times_out="$base_dir/$job_id.times.csv"
  local vm_out_dir="$base_dir/$job_id.virtual-memory"

  mkdir -p $vm_out_dir \

  # Write Header of the CSV file that is appended to.
  echo 'status,elapsed_secs,shell_name,shell_hash,benchmark_name' \
    > $times_out

  # TODO: read the host and pass it

  # job_id is a (host / host ID)?
  # It's probably simpler just to thread through those 2 vars and keep it in the same format.


  cat $provenance | while read _ _ _ sh_path shell_hash; do
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

    log "--- Running task with $sh_path"

    conf-dirs | xargs -n 1 -- $0 \
      configure-one $times_out $vm_out_dir $sh_path $shell_hash || true
  done

  cp -v $provenance $base_dir
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
