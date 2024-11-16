#!/usr/bin/env bash

demo() {
  local ysh=_bin/cxx-opt/ysh
  ninja $ysh

  #OILS_GC_STATS=1 $ysh test/bug-2123.ysh

  # max RSS
  # 246
  /usr/bin/time --format '%e %M' $ysh test/bug-2123.ysh
}

"$@"
