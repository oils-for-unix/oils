#!/bin/bash
#
# Usage:
#   ./perf.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install() {
  # linux-tools-generic is the kernel module
  # Apparently you need a package specific to the kernel, not sure why.
  sudo apt install linux-tools-common linux-tools-4.13.0-36-generic linux-tools-generic
}

debug-symbols() {
  #dpkg --listfiles linux-tools-4.13.0-36-generic
  #sudo apt install python-dbg

  # I don't see symbols files here?  Just the interpreter?  They're built into the ELF file?
  #dpkg --listfiles python-dbg

  # has files in /usr/lib/debug
  # file /usr/lib/debug/.build-id/8d/9bd4ce26e45ef16075c67d5f5eeafd8b562832.debug
  # /usr/lib/debug/.build-id/8d/9bd4ce26e45ef16075c67d5f5eeafd8b562832.debug: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, BuildID[sha1]=8d9bd4ce26e45ef16075c67d5f5eeafd8b562832, not stripped
  #
  # https://sourceware.org/gdb/onlinedocs/gdb/Separate-Debug-Files.html

  # Does perf also support separate debug files?
  # How do I set the debug link in oil.ovm?  Or should I set build ID?

  # The GNU binary utilities (Binutils) package includes the ‘objcopy’ utility
  # that can produce the separated executable / debugging information file
  # pairs using the following commands:
  # objcopy --only-keep-debug foo foo.debug
  # strip -g foo

  sudo apt install zlib1g-dbg
  dpkg --listfiles zlib1g-dbg
  #libpython2.7-dbg 
}


# Parsing abuild in Debug mode:
# 14%  PyEval_EvalFrameEx  -- hm.  Interpreter dispatch is a lot?  More than I
#      thought.  Maybe need my own loop.
# 8%   type_call -- hm introspection?
# 7%   PyObject_GetAttr.  My intitution.  Should be done at compile time!
# 6%   do_richcmp  -- hm interesting
# 5%   PyObject_Malloc.

# More benchmarks:
# OPy running under OVM, compiling itself, compiling Oil, compiling OPy ports,
# etc.

# Parsing abuild, the optimized version.
#
# 80% PyEval_EvalFramEx.  Woah everything is inlined?
# 12.5%  PyObject_GenericGetAtr.  PyObject_GetAttr is much lower down.
# Some kernel.
# 0.76%  lookdict_string is not a bottleneck.  Hm.
#
# Wow.
# Maybe I need counters in optimized mode?

_record() {

  # TODO: The optimized build should have symbols!  Don't build with -s.  And
  # then put symbols next to the binary somehow?  How do the symbols packages
  # work?
  #perf record -o perf.data -- _bin/oil.ovm-dbg osh -n benchmarks/testdata/abuild | wc -l

  perf record -o perf.data -- _bin/oil.ovm-opt osh --ast-format none -n benchmarks/testdata/abuild
  #perf record -o perf.data -- _bin/osh --ast-format none -n benchmarks/testdata/abuild
}
record() { sudo $0 _record; }

# Perf note: Without -o, for some reason osh output is shown on the console.
# It doesn't go to wc?
#perf record -o perf.data -- _bin/osh -n benchmarks/testdata/abuild | wc -l

# After recording, run perf-data, then 'perf report'.  It automatically shows
# perf.data.

_perf-data() {
  # This gets run as root
  chmod 644 perf.data
  chown andy perf.data
  file perf.data
  ls -l perf.data
}
perf-data() { sudo $0 _perf-data; }

# Wow 11 billion instructions!  9 billion cycles.  2.3 billion branches.  Crazy.
# Only 21M branch misses, or 0.9%.  Interesting.
_stat() {
  perf stat -- _bin/osh -n benchmarks/testdata/abuild | wc -l
  # -e cache-misses only shows that stat
}
stat() { sudo $0 _stat; }

"$@"
