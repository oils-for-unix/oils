#!/usr/bin/env bash
#
# Why is CPython configure slower under OSH?
#
# Usage:
#   benchmarks/autoconf.sh <function name>
#
# Examples:
#   $0 patch-pyconf    # times builtin
#   $0 measure-times   # time-tsv with gc stats
#   $0 report-times    # times builtin
#
#   $0 measure-syscalls
#   $0 report-syscalls
#   $0 report-processes
#   $0 report-external
#
# Simpler:
#   $0 measure-rusage  # time-tsv

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/cachegrind.sh  # with-cachegrind
source benchmarks/callgrind.sh  # with-cachegrind
source test/tsv-lib.sh  # $TAB

readonly BASE_DIR_RELATIVE=_tmp/autoconf
readonly BASE_DIR=$REPO_ROOT/$BASE_DIR_RELATIVE
readonly PY_CONF=$REPO_ROOT/Python-2.7.13/configure

#
# Trying to measure allocation/GC overhead 
#
# This DOES NOT HELP because bumpleak/bumproot are **slower** on bigger heaps.
# There's less cache locality!
#

cpython-configure-tasks() {
  local -a variants=( opt+bumpleak opt+bumproot opt )
  for v in ${variants[@]}; do
    echo "${v}${TAB}_bin/cxx-$v/osh"
  done
}

cpython-setup() {
  cpython-configure-tasks | while read -r _ osh; do
    ninja $osh
  done
}

measure-alloc-overhead() {
  local base_dir=$BASE_DIR/alloc-overhead
  rm -r -f -v $base_dir

  cpython-configure-tasks | while read -r variant osh; do
    osh=$REPO_ROOT/$osh

    local task_dir=$base_dir/$variant

    mkdir -p $task_dir
    pushd $task_dir > /dev/null

    local -a flags=(
        --output "$base_dir/$variant.tsv" 
        --rusage
    )

    local -a time_argv

    time_argv=(
      time-tsv --print-header
      "${flags[@]}"
      --field variant
    )
    "${time_argv[@]}"

    time_argv=(
      time-tsv --append
      "${flags[@]}"
      --field "$variant"
      -- $osh $PY_CONF
    )

    #echo "${time_argv[@]}"
    "${time_argv[@]}"

    popd > /dev/null

  done
}

#
# Compare bash/dash/osh locally
#

measure-rusage() {
  local base_dir=$BASE_DIR/rusage
  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do

    local task_dir=$base_dir/$sh_label

    mkdir -p $task_dir
    pushd $task_dir > /dev/null

    local -a flags=(
        --output "$base_dir/$sh_label.tsv" 
        --rusage
    )

    local -a time_argv

    time_argv=(
      time-tsv --print-header
      "${flags[@]}"
      --field sh_label
    )
    "${time_argv[@]}"

    time_argv=(
      time-tsv --append
      "${flags[@]}"
      --field "$sh_label"
      -- $sh_path $PY_CONF
    )

    #echo "${time_argv[@]}"
    "${time_argv[@]}"

    popd > /dev/null

  done
}

#
# Now try strace
#

shell-tasks() {
  echo "bash${TAB}/usr/bin/bash"
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt/osh"
}

measure-syscalls() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/syscalls

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    local counts_dir=$base_dir/$sh_label
    mkdir -p $counts_dir

    pushd $dir
    #strace -o $counts -c $sh_path $PY_CONF
    # See how many external processes are started?
    #strace -o $counts -ff -e execve $sh_path $PY_CONF
    strace -o $counts_dir/syscalls -ff $sh_path $PY_CONF
    popd
  done
}

measure-hw-counters() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/hw-counters

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir
    perf stat $sh_path $PY_CONF > /dev/null
    popd
  done
}

measure-hw-counters2() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/hw-counters2

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir
	local prog='
	hardware:instructions:1e6 {
		@[pid, comm, probe] = count() 
	}
	hardware:cycles:1e6 {
		@[pid, comm, probe] = count() 
	}
	'
	sudo bpftrace -e "$prog" -c "$sh_path $PY_CONF" -o counters.txt > /dev/null
    popd
  done
}

measure-exits() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/exits

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir
	sudo /usr/bin/python3 /home/melvin/bcc/tools/exitsnoop.py > $dir/exit-log.txt &
	local snoop_pid=$!
	$sh_path $PY_CONF > /dev/null
	kill $snoop_pid
	awk '{print $1" "$5}' exit-log.txt | /home/melvin/child-stats.py $sh_label
    popd
  done
}

measure-faults() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/faults

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir
	local prog='
	kfunc:vmlinux:__handle_mm_fault {
		@faults[comm] = count();
		@fault_start[pid] = nsecs;
	}
	kretfunc:vmlinux:__handle_mm_fault {
		@fault_time[pid, comm] += nsecs - @fault_start[pid];
	}
	END {
		clear(@fault_start);
	}
	'
	sudo bpftrace -e "$prog" -c "$sh_path $PY_CONF" -o faults.txt > /dev/null
    popd
	sudo chown -R $(whoami) $dir
  done
}

measure-fork-to-exec() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/fork-to-exec

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir
    pushd $dir
    local prog="
    kprobe:sched_fork
    {
		printf(\"fork() from %s\n\", comm);
	}
    tracepoint:syscalls:sys_exit_clone
    {
		@fork_time[pid] = nsecs;
    }
    tracepoint:syscalls:sys_enter_execve
    /comm == \"$sh_label\"/
    {
		@exec_time[pid, comm] = nsecs;
    }
    tracepoint:syscalls:sys_exit_execve
    {
		@new_comm[pid] = comm;
    }
    END {
  	for (\$kv : @exec_time) {
  		if (@fork_time[\$kv.0.0] != 0) {
  			printf(\"%ld (%s -> %s) %lld us\n\", \$kv.0.0, \$kv.0.1, @new_comm[\$kv.0.0], (\$kv.1 - @fork_time[\$kv.0.0]) / 1e3);
  		}
  	}
  	clear(@exec_time);
  	clear(@new_comm);
  	clear(@fork_time);
    }
    "
    sudo bpftrace -e "$prog" -c "$sh_path $PY_CONF" -o trace.txt > /dev/null
    popd
    sudo chown -R $(whoami) $dir
  done
}

measure-sort() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  local base_dir=$BASE_DIR/hw-counters

  rm -r -f -v $base_dir

  shell-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir
    perf stat $sh_path -c 'cat /home/melvin/big.txt | sort > /dev/null'
    popd
  done
}

# --- _tmp/autoconf/bash
# 6047
# 4621
# --- _tmp/autoconf/dash
# 6088
# 4627
# --- _tmp/autoconf/osh
# 5691
# 4631
#
# Woah we start fewer processes!  But are not faster?

grep-exec() {
  egrep --no-filename -o 'execve\("[^"]+' "$@"
}

# andy@hoover:~/git/oilshell/oil$ benchmarks/autoconf.sh report-syscalls
# --- _tmp/autoconf/syscalls/bash
#      2592 _tmp/autoconf/syscalls/bash/syscalls.903220
#      2608 _tmp/autoconf/syscalls/bash/syscalls.898727
#      2632 _tmp/autoconf/syscalls/bash/syscalls.898387
#      2679 _tmp/autoconf/syscalls/bash/syscalls.898292
#      2853 _tmp/autoconf/syscalls/bash/syscalls.898927
#      2873 _tmp/autoconf/syscalls/bash/syscalls.898334
#      2920 _tmp/autoconf/syscalls/bash/syscalls.898895
#      3204 _tmp/autoconf/syscalls/bash/syscalls.898664
#    112549 _tmp/autoconf/syscalls/bash/syscalls.897471
#   1360223 total
# 
# --- _tmp/autoconf/syscalls/dash
#      2592 _tmp/autoconf/syscalls/dash/syscalls.909344
#      2607 _tmp/autoconf/syscalls/dash/syscalls.904921
#      2630 _tmp/autoconf/syscalls/dash/syscalls.904581
#      2683 _tmp/autoconf/syscalls/dash/syscalls.904486
#      2851 _tmp/autoconf/syscalls/dash/syscalls.905109
#      2873 _tmp/autoconf/syscalls/dash/syscalls.904528
#      2920 _tmp/autoconf/syscalls/dash/syscalls.905088
#      3204 _tmp/autoconf/syscalls/dash/syscalls.904858
#    112922 _tmp/autoconf/syscalls/dash/syscalls.903626
#   1372118 total
# 
# --- _tmp/autoconf/syscalls/osh
#     2592 _tmp/autoconf/syscalls/osh/syscalls.915226
#     2607 _tmp/autoconf/syscalls/osh/syscalls.910993
#     2630 _tmp/autoconf/syscalls/osh/syscalls.910647
#     2679 _tmp/autoconf/syscalls/osh/syscalls.910561
#     2851 _tmp/autoconf/syscalls/osh/syscalls.911162
#     2873 _tmp/autoconf/syscalls/osh/syscalls.910599
#     2920 _tmp/autoconf/syscalls/osh/syscalls.911143
#     3204 _tmp/autoconf/syscalls/osh/syscalls.910936
#    72921 _tmp/autoconf/syscalls/osh/syscalls.909769
#  1211074 total

report-processes() {
  for sh_dir in $BASE_DIR_RELATIVE/syscalls/*; do
    echo "--- $sh_dir"
    ls $sh_dir/* | wc -l
    grep-exec $sh_dir/syscalls.* | wc -l
    echo

  done
}

report-external() {
  local n=${1:-5}

  for sh_dir in $BASE_DIR_RELATIVE/syscalls/*; do
    echo "--- $sh_dir"

    grep-exec $sh_dir/syscalls.* | sort | uniq -c | sort -n | tail -n $n
    echo
  done
}

report-syscalls() {
  # Hm this is instructive, the shell itself makes the most syscalls
  # And fewer than other shells?

  for sh_dir in $BASE_DIR_RELATIVE/syscalls/*; do
    echo "--- $sh_dir"
    wc -l $sh_dir/syscalls.* | sort -n | tail
    echo
  done
}

#
# Cachegrind
#

measure-valgrind() {
  local tool=$1

  # opt seems to give OK results, but I thought dbg was more accurate
  #local osh=_bin/cxx-opt/osh
  local osh=_bin/cxx-dbg/osh

  ninja $osh

  local osh=$REPO_ROOT/$osh

  local base_dir=$REPO_ROOT/_tmp/$tool

  local dir=$base_dir/cpython-configure
  rm -r -f -v $dir

  local out_file=$base_dir/cpython-configure.txt

  mkdir -v -p $dir

  pushd $dir
  $tool $out_file $osh $PY_CONF
  popd
}

measure-cachegrind() {
  measure-valgrind with-cachegrind
}

measure-callgrind() {
  # This takes ~5 minutes with opt binary, ~6:43 with dbg
  # vs ~15 seconds uninstrumented
  time measure-valgrind with-callgrind
}

# Note:
# benchmarks/osh-runtime.sh compares our release, which does not have #ifdef
# GC_TIMING, so we don't know total GC time.

# TODO:
#
# - Run locally, reproduce GC_TIMING - this is not in the release build
#   - it seems to say only 143 ms total GC time, but we're seeing 1.5+ seconds
#   slowdown on Cpython configure vs. bash
#   - I want a local run that automates it, and returns PERCENTAGES for elapsed
#   time, sys time, user time
# - We also might not want to amortize free() inside Allocate()
#   - #ifdef LAZY_FREE I think!  That might show a big slowdown with free

patch-pyconf() {
  #sed -i $'s/ac_compile=\'$CC/ac_compile=\'times; $CC/g' $PY_CONF

  # temporary
  echo 'times > $SH_BENCHMARK_TIMES' >> $PY_CONF
}

measure-times() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  local base_dir=$BASE_DIR/times
  rm -r -f -v $base_dir

  local trace_dir=$base_dir/oils-trace
  mkdir -p $trace_dir

  shell-tasks | while read -r sh_label sh_path; do
    #case $sh_label in bash|dash) continue ;; esac

    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir

    local -a flags=(
        --output "$base_dir/$sh_label.tsv" 
        --rusage
    )

    local -a time_argv

    time_argv=(
      time-tsv --print-header
      "${flags[@]}"
      --field sh_label
    )
    "${time_argv[@]}"

    time_argv=(
      time-tsv --append
      "${flags[@]}"
      --field "$sh_label"
      -- $sh_path $PY_CONF
    )

    #echo "${time_argv[@]}"

    # 1269 argv0.json files created
    # we can miss some via NOLASTFORK optimization
      #OILS_TRACE_DIR=$trace_dir \

    _OILS_GC_VERBOSE=1 OILS_GC_STATS_FD=99 \
      SH_BENCHMARK_TIMES=$base_dir/$sh_label.times.txt \
      "${time_argv[@]}" \
      99>$base_dir/$sh_label.gc-stats.txt

    popd
  done
}

inner-long-tsv() {
  python2 -c '
import os, re, sys

def PrintRow(row):
  print("\t".join(row))

PrintRow(["shell", "who", "what", "seconds"])

for path in sys.argv[1:]:
  filename = os.path.basename(path)
  shell = filename.split(".")[0]

  f = open(path)
  s = f.read()

  secs = re.findall("0m([0-9.]+)s", s)
  assert len(secs) == 4, secs

  PrintRow([shell, "self", "user", secs[0]])
  PrintRow([shell, "self", "sys", secs[1]])
  PrintRow([shell, "child", "user", secs[2]])
  PrintRow([shell, "child", "sys", secs[3]])

  # Non-normalized, but OK
  total_secs = sum(float(s) for s in secs)
  PrintRow([shell, "both", "both", str(total_secs)])

  ' $BASE_DIR/times/*.times.txt
}

compare-dim() {
  # 8% more child system time
  local who=${1:-child}
  local what=${2:-user}

  echo "=== $who $what ==="

  # Annoying
  # https://www.math.utah.edu/docs/info/gawk_8.html
  # "If, for some reason, you need to force a number to be converted to a
  # string, concatenate the empty string, "", with that number. To force a
  # string to be converted to a number, add zero to that string."

  cat $BASE_DIR/times-long.tsv | awk -v "who=$who" -v "what=$what" '
  BEGIN { 
    TAB = "\t"

    i = 0

    printf "%s\t%s\t%s\t%s\n", "shell", "secs", "ratio", "diff secs"
  }
  $2 == who && $3 == what {
    if (i == 0) {
      first_secs = $4 + 0
    }
    i++

    secs = $4 + 0
    ratio = secs / first_secs
    diff = secs - first_secs

    # Need commas for OFMT to work correctly?
    printf "%s\t%5.3f\t%5.3f\t%5.3f\n", $1, secs, ratio, diff
  }
  '

  echo
}

compare-times() {
  log "INNER"
  log ''

  compare-dim self user

  compare-dim self sys

  compare-dim child user

  compare-dim child sys

  compare-dim both both

  # outer
  log "OUTER"
  log ''

  compare-dim both elapsed

  # These kinda match
  return
  compare-dim both user
  compare-dim both sys
}

outer-long-tsv() {
  log "=== outer times ==="
  awk '
  BEGIN {
    i = 0

    printf "%s\t%s\t%s\t%s\n", "shell", "who", "what", "seconds"
  }
  i == 0 {
    #print "Skipping header"
    i++
    next
  }
  i >= 1 { 
    elapsed = $2 + 0
    user = $3 + 0
    sys = $4 + 0
    sh_label = $6

    printf "%s\t%s\t%s\t%5.3f\n", sh_label, "both", "elapsed", elapsed
    printf "%s\t%s\t%s\t%5.3f\n", sh_label, "both", "user", user
    printf "%s\t%s\t%s\t%5.3f\n", sh_label, "both", "sys", sys

    i++
  }
  ' $BASE_DIR/outer-wide.tsv
}

report-times() {
  head $BASE_DIR/times/*.tsv
  echo
  head $BASE_DIR/times/*.times.txt
  echo

  inner-long-tsv  | tee $BASE_DIR/inner-long.tsv
  echo

  tsv-concat $BASE_DIR/times/*.tsv | tee $BASE_DIR/outer-wide.tsv
  outer-long-tsv | tee $BASE_DIR/outer-long.tsv
  echo

  tsv-concat $BASE_DIR/{inner,outer}-long.tsv | tee $BASE_DIR/times-long.tsv

  compare-times
}

### Why is clone() taking longer according to strace?

fork-tasks() {
  echo "bash${TAB}bash"
  echo "dash${TAB}dash"

  # Hm this is noisy, but cxx-opt-sh does seem slower
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt/osh"
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt-sh/osh"
}

measure-fork() {
  fork-tasks | while read -r sh_label sh_path; do
    #case $sh_label in bash|dash) continue ;; esac

    echo "=== $sh_path ==="

    # Builtin is very fast
    #time $sh_path -c 'for i in $(seq 100); do true; done'

    # Hm this is very noisy
    # TODO use hyperfine?
    time $sh_path -c 'for i in $(seq 100); do /bin/true; done'

    case $sh_label in
      osh)
        # Oops, we are not symlinking to the .stripped binary!
        # This is explicitly done for symbols and benchmarking.
        # Hm does that make it slower then?

        ls -l -L $sh_path
        ldd $sh_path
        ;;
    esac
  done
}

# $ head _tmp/elapsed/*.times.txt
# ==> _tmp/elapsed/bash.times.txt <==
# 0m0.213s 0m0.477s
# 0m8.233s 0m2.931s
# 
# ==> _tmp/elapsed/dash.times.txt <==
# 0m0.217s 0m0.463s
# 0m8.281s 0m2.922s
# 
# ==> _tmp/elapsed/osh.times.txt <==
# 0m0.360s 0m0.720s
# 0m8.790s 0m2.960s

# shell user time - GC and allocs
# shell system time - ???
# child user time - ???
#   TODO: count how many processes this is.  
#   It's more than 500 ms
#   Is that 500 processes, and 1 ms per process?

fork-time() {
  local osh=_bin/cxx-opt/osh

  $osh -c 'time for i in {1..1000}; do true; done'
  echo

  $osh -c 'time for i in {1..1000}; do ( true ); done'
  echo

  # Does this increase fork time or no?
  # Hm I can only get the forks up to 306ms for 1000, or 300 us
  # But the HereDocWriter does dup() and so forth
  $osh -c '
echo ysh-parse
time for i in {1..40}; do
  . test/ysh-parse-errors.sh
done
times
time for i in {1..1000}; do
  ( true )
done'
  echo
}

"$@"
