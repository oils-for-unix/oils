#!/usr/bin/env bash

demo() {
  local ysh=_bin/cxx-opt/ysh
  ninja $ysh

  OILS_GC_STATS=1 _OILS_GC_VERBOSE=1 $ysh test/bug-2123.ysh
  #time OILS_GC_STATS=1 $ysh test/bug-2123.ysh

  # max RSS
  # 246
  # /usr/bin/time --format '%e %M' $ysh test/bug-2123.ysh
}

debug() {
  local ysh=_bin/cxx-dbg/ysh
  ninja $ysh

  gdb --args $ysh test/bug-2123.ysh
}

"$@"
