#!/usr/bin/Rscript
#
# osh-parser.R -- Analyze output from shell scripts.
#
# Usage:
#   osh-parser.R OUT_DIR [TIMES_CSV...]

library(dplyr)
library(tidyr)  # spread()
library(stringr)

#source('benchmarks/common.R')


# Cool stats:
#
# > sum(fr$bytecode_bytes)
# [1] 216200
# 
# That's the total number of bytecode bytes.  I can get that down by removing
# unused code.
#
# Number of instructions:
# > nrow(op)
# [1] 80232

# > op %>% count(op_name) %>% arrange(n) %>% tail(n=20)
# # A tibble: 20 x 2
#    op_name               n
#    <fct>             <int>
#  1 BINARY_SUBSCR       533
#  2 POP_BLOCK           720
#  3 STORE_SUBSCR        721
#  4 DUP_TOP             816
#  5 STORE_ATTR          996
#  6 BUILD_TUPLE        1076
#  7 MAKE_FUNCTION      1738
#  8 COMPARE_OP         1893
#  9 POP_JUMP_IF_FALSE  2391
# 10 JUMP_FORWARD       2534
# 11 LOAD_NAME          2534
# 12 POP_TOP            2897
# 13 RETURN_VALUE       3141
# 14 STORE_FAST         3484
# 15 STORE_NAME         3566
# 16 CALL_FUNCTION      5698
# 17 LOAD_GLOBAL        5922
# 18 LOAD_ATTR          8771
# 19 LOAD_CONST        10209
# 20 LOAD_FAST         12663



options(stringsAsFactors = F)

main = function(argv) {
  action = argv[[1]]
  in_dir = argv[[2]]
  out_dir = argv[[3]]

  # TODO: load the 4 tables
  consts = read.table(foo, header=T)

  if (action == 'big-strings') {
    # arrange consts by size_or_len
    ParserReport(in_dir, out_dir)

  } else if (action == 'osh-runtime') {
    RuntimeReport(in_dir, out_dir)

  } else if (action == 'vm-baseline') {
    VmBaselineReport(in_dir, out_dir)

  } else if (action == 'ovm-build') {
    OvmBuildReport(in_dir, out_dir)

  } else if (action == 'oheap') {
    OheapReport(in_dir, out_dir)

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
  Log('PID %d done', Sys.getpid())
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
