#!/bin/bash
#
# Use sys.setprofile() and maybe sys.settrace() to trace Oil execution.
#
# Problem: Python callbacks for sys.setprofile() are too slow I think.
#
# Usage:
#   ./pytrace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BIGGEST=benchmarks/testdata/configure-coreutils
readonly ABUILD=benchmarks/testdata/abuild
readonly -a RUN_ABUILD=(bin/oil.py osh $ABUILD -h)
# Slightly faster but not significantly.
#readonly -a RUN_ABUILD=(_bin/osh $ABUILD -h)
readonly -a OSH_PARSE=(bin/oil.py osh --ast-format none -n)

#
# Use Python's cProfile, which uses _lsprof.  This is pretty fast.
#

time-bash-run-abuild() { time bash $ABUILD -h; }

# Old: ~2.7 seconds (no tracing)
# 2017/11/27, After ASDL optimization: 0.72 seconds.
time-run-abuild() { time "${RUN_ABUILD[@]}"; }
time-parse-abuild() { time "${OSH_PARSE[@]}" $ABUILD; }

time-parse-biggest() { time "${OSH_PARSE[@]}" $BIGGEST; }

_cprofile() {
  local out=$1
  shift
  time python -m cProfile -o $out "$@"
}

# 3.8 seconds.  So less than 2x overhead.
cprofile-osh-parse() {
  local in=${1:-$ABUILD}
  local out=${2:-abuild.cprofile}
  _cprofile $out "${OSH_PARSE[@]}" $in
  ls -l $out
}

cprofile-parse-abuild() {
  cprofile-osh-parse $ABUILD _tmp/abuild.cprofile
}
cprofile-parse-biggest() {
  cprofile-osh-parse $BIGGEST _tmp/biggest.cprofile
}
cprofile-run-abuild() {
  _cprofile _tmp/abuild-run.cprofile "${RUN_ABUILD[@]}"
}

# TODO: Try uftrace?  I guess you can compare wait4() call duration with bash
# vs. osh?
strace-run-abuild() {
  #local filter='read,wait4' 
  local filter='execve,wait4' 
  time strace -ff -e "$filter" "${RUN_ABUILD[@]}"
  #time strace -c "${RUN_ABUILD[@]}"
}

# Yeah I understand from this why Chrome Tracing / Flame Graphs are better.
# This format doesn't respect the stack!
# cumtime: bin/oil.py is the top, obviously
print-cprofile() {
  local profile=${1:-_tmp/abuild.cprofile}
  python -c '
import pstats
import sys
p = pstats.Stats(sys.argv[1])
p.sort_stats("tottime").print_stats()
' $profile
}

#
# My Own Tracing with pytrace.py.  Too slow!
#


# Abuild call/return events:
# Parsing: 4,345,706 events
# Execution: 530,924 events

# Total events:
# 14,918,308
# Actually that is still doable as binary.  Not sure it's viewable in Chrome
# though.
# 14 bytes * 14.9M is 209 MB.

abuild-trace() {
  _PY_TRACE=abuild.pytrace time "${PARSE_ABUILD[@]}"
}

#
# Depends on pytracing, which is also too slow.
#

# Trace a parsing function
parse() {
  #local script=$ABUILD 
  local script=$0
  time bin/oil.py osh --ast-format none -n $script >/dev/null
}

# Trace the execution
execute() {
  #local script=$ABUILD 
  local script=$0
  #time bin/oil.py osh -c 'echo hi'
  time bin/oil.py osh $0

  ls -l -h *.json
}

# Idea: I Want a flame graph based on determistic data!  That way you get the
# full stack trace.

# It wasn't happening in the python-flamegraph stuff for some reason.  Not sure
# why.  I think it is because I/O was exaggerated.
# 
# Interpreter hook:
#
# for thread_id, frame in sys._current_frames().items():
#   if thread_id == my_thread:
#     continue

# Note that opening file descriptors can cause bugs!  I have to open it above
# descriptor 10!

# python-flamegraph
# - suffers from measurement error due to threads.  
# - is RunCommandSub is being inflated?
#    - well actually i'm not sure.  I have to do it myself on a single thread
#    and see.
# pytracing:
# - the format is too bloated.  It can't handle abuild -h.  So I have to
# optimize it.
#
# I want to unify these two approaches: both flame graphs and function traces.
#
# Advantage: sys.setprofile() gets C function call events!
#
# Reservoir Sampling!  Get a list of all unique stacks.
#
# You can figure out the stack from the current/call/return sequence.  So you
# can use the reservoir sampling algorithm to get say 100,000 random stacks out
# of 14 M events.
#
# sys.getframes()

"$@"
