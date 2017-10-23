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

readonly ABUILD=~/git/alpine/abuild/abuild 
readonly -a RUN_ABUILD=(bin/oil.py osh $ABUILD -h)
readonly -a PARSE_ABUILD=(bin/oil.py osh --ast-format none -n $ABUILD)

#
# Use Python's cProfile, which uses _lsprof.  This is pretty fast.
#

# ~2.7 seconds (no tracing)
time-run-abuild() {
  time "${RUN_ABUILD[@]}"
}

# ~1.6 seconds (no tracing)
time-parse-abuild() {
  time "${PARSE_ABUILD[@]}"
}

# 3.8 seconds.  So less than 2x overhead.
cprofile-parse-abuild() {
  local out=abuild.cprofile 
  time python -m cProfile -o $out "${PARSE_ABUILD[@]}"
  ls -l $out
}

# Yeah I understand from this why Chrome Tracing / Flame Graphs are better.
# This format doesn't respect the stack!
# cumtime: bin/oil.py is the top, obviously
print-cprofile() {
  python -c '
import pstats
p = pstats.Stats("abuild.cprofile")
p.sort_stats("tottime").print_stats()
'
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
