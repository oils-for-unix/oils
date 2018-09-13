#!/usr/bin/Rscript
#
# bytecode.R -- Analyze output of opyc dis-tables.
#
# Usage:
#   bytecode.R ACTION IN_DIR OUT_DIR

library(dplyr)
library(tidyr)  # spread()
library(stringr)

source('benchmarks/common.R')

options(stringsAsFactors = F)

BigStrings = function(consts) {
  strs = consts %>% filter(type == 'str') %>% arrange(desc(len_or_val))
  strs %>% head(20) %>% print()
  total_bytes = sum(strs$len_or_val)

  # 184 KB of strings!  That's just the payload; the header is probably more.
  Log('total string bytes: %d', total_bytes)

  # This plot says:
  #
  # total bytes is 184 KB
  # - the top 10 strings sum to 20K bytes
  # - the top 100 strings sum to 30K bytes

  cum = cumsum(strs$len_or_val)
  plot(cum)

  #plot(ecdf(strs$len_or_val))
}

Consts = function(consts) {
  # count of types of constants.  Strings dominate of course.
  # But there are only 7 or so immutable types!

  # - only 2 float constants.
  # - get rid of the unicode constants in posixpath.

  consts %>% count(type) %>% arrange(n) %>% tail(20)
}

# Frames by number of consts, number of ops, etc.
Frames = function(ctx) {
  Log('Frames with many consts')
  ctx$consts %>% count(path, code_name, sort=T) %>% print()

  Log('Frames with many ops')
  ctx$ops %>% count(path, code_name, sort=T) %>% print()

  Log('Frames with large stacksize')
  ctx$frames %>% arrange(desc(stacksize)) %>% head(10) %>% print()

  Log('Frames with many locals')
  ctx$frames %>% arrange(desc(nlocals)) %>% head(10) %>% print()
}

Ops = function(ops) {
  ops %>% count(op_name) %>% arrange(n) -> op_freq

  Log('common:')
  op_freq %>% tail(n=20) %>% print()
  Log('rare:')
  op_freq %>% head(n=20) %>% print()

  # These are all the big jump targets!  Max is 3,852, which is a lot less than
  # 65,536.  We don't need EXTENDED_ARG!
  ops %>% arrange(op_arg) %>% tail(10) %>% print()
}

Flags = function(flags) {
  flags %>% count(flag) %>% arrange(n) %>% print()
}

Names = function(names) {
  # Common types: free, cell, etc.
  names %>% count(kind) %>% arrange(desc(n)) %>% print()

  # Common names:
  # self, None, True, False, append, len
  names %>% count(name) %>% arrange(desc(n)) %>% print()
}

Basic = function(ctx) {
  # Number of files
  ctx$frames %>% count(path) -> by_path
  Log('number of files: %d', nrow(by_path))

  # Hm this isn't reliable because the code name isn't unique!  I think we need
  # firstlineno
  ctx$frames %>% count(path, code_name) %>% print()

  # 216K
  b = sum(ctx$frames$bytecode_bytes)
  Log('Total bytecode bytes: %d', b)

  num_insts = nrow(ctx$ops)
  Log('Total instructions: %d', num_insts)
}

# Hm max unique ops is 58
# _build/oil/bytecode-opy/core/cmd_exec.pyc     54
# _build/oil/bytecode-opy/warnings.pyc          55
# _build/oil/bytecode-opy/_abcoll.pyc           58
#
# But there are 119 total opcodes.  A lot of the math ones are uncommon.

# Written by opy/metrics.sh.  Could get rid of that file.
UniqueOpsByFile = function(ops, ops_defined = '_tmp/opcodes-defined.txt') {
  # This is a row for every path/op_name
  u = ops %>% group_by(path) %>% distinct(op_name)
  u %>% count(path) %>% arrange(n) -> ops_by_file

  Log('files with few ops:')
  ops_by_file %>% head(20) %>% print()

  Log('files with many ops:')
  ops_by_file %>% tail(10) %>% print()

  Log('parsing:')  # 17, 23, 34, 34, 46
  ops_by_file %>% filter(grepl('reader|lex|parse', path)) %>% print()
  ops %>% filter(grepl('reader|lex|parse', path)) %>% distinct(op_name) -> string_ops
  Log('Total for parsing: %d', nrow(string_ops))
  
  Log('')
  u2 = ops %>% distinct(op_name) 
  Log('Total unique opcodes: %d', nrow(u2))

  if (ops_defined != '') {
    defined = read.table(ops_defined, header=F)
    colnames(defined) = c('op_name')

    Log('Unused opcodes:')
    setdiff(defined, u2) %>% print()
  }

  list(string_ops = string_ops)
}

# OPy emits 88 distinct opcodes out of 119.  Interesting.
# CPython emits 94 distinct opcodes.
# STORE_MAP and SETUP_WITH are the only differences.  Is this for dict literals?
#
#
# setdiff(cpy$ops %>% distinct(op_name), opy$ops %>% distinct(op_name))
#            op_name
# 1        STORE_MAP
# 2       SETUP_WITH
# 3       PRINT_ITEM
# 4    PRINT_NEWLINE
# 5    PRINT_ITEM_TO
# 6 PRINT_NEWLINE_TO

# Unused opcodes:
#                 op_name
# 1    BINARY_TRUE_DIVIDE
# 2             BUILD_SET
# 3           BUILD_SLICE
# 4         CONTINUE_LOOP
# 5           DELETE_ATTR
# 6         DELETE_GLOBAL
# 7        DELETE_SLICE+2
# 8        DELETE_SLICE+3
# 9          EXTENDED_ARG
# 10       INPLACE_DIVIDE
# 11 INPLACE_FLOOR_DIVIDE
# 12       INPLACE_LSHIFT
# 13       INPLACE_MODULO
# 14           INPLACE_OR
# 15        INPLACE_POWER
# 16  INPLACE_TRUE_DIVIDE
# 17                  NOP
# 18           PRINT_EXPR
# 19           PRINT_ITEM
# 20        PRINT_ITEM_TO
# 21        PRINT_NEWLINE
# 22     PRINT_NEWLINE_TO
# 23             ROT_FOUR
# 24           SETUP_WITH
# 25              SET_ADD
# 26            STOP_CODE
# 27            STORE_MAP
# 28        STORE_SLICE+2
# 29        STORE_SLICE+3
# 30        UNARY_CONVERT
# 31       UNARY_POSITIVE


Report = function(ctx) {
  Basic(ctx)
  BigStrings(ctx$consts)

  Frames(ctx)
  Names(ctx$names)
  Consts(ctx$consts)
  Flags(ctx$flags)

  Ops(ctx$ops)
  UniqueOpsByFile(ctx$ops)
}

Load = function(in_dir) {
  list(
       frames = read.table(file.path(in_dir, 'frames.tsv2'), header=T),
       names = read.table(file.path(in_dir, 'names.tsv2'), header=T),
       consts = read.table(file.path(in_dir, 'consts.tsv2'), header=T),
       flags = read.table(file.path(in_dir, 'flags.tsv2'), header=T),
       ops = read.table(file.path(in_dir, 'ops.tsv2'), header=T)
       )
}

# TODO: Just take a table of (py_path, pyc_path, key) and then produce bytes
# for py_path and pyc_path.  Does R have getsize?
#
# file.info()$size of both.  And then

MeasureFileSizes = function(all_deps_py) {
  py_pyc = read.table(all_deps_py, header=F)
  colnames(py_pyc) = c('py_path', 'pyc_path')

  py_pyc$py_bytes = file.info(py_pyc$py_path)$size

  pyc_paths = file.path('_build/oil/bytecode-opy', py_pyc$pyc_path)
  py_pyc$pyc_bytes = file.info(pyc_paths)$size

  py_pyc %>% mutate(ratio = pyc_bytes / py_bytes) %>% arrange(ratio) -> py_pyc

  Log('small .pyc files:')
  py_pyc %>% head(10) %>% print()

  Log('big .pyc files:')
  py_pyc %>% tail(10) %>% print()

  # This ratio is a ltitle misleading because it counts comments.
  py_total = sum(py_pyc$py_bytes)
  pyc_total =  sum(py_pyc$pyc_bytes)
  Log('Overall: %d bytes of .py -> %d bytes of .pyc', py_total, pyc_total)
  Log('Ratio: %f', pyc_total / py_total)

  py_pyc
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'metrics') {
    in_dir = argv[[2]]

    ctx = Load(in_dir)
    #out_dir = argv[[3]]
    Report(ctx)

  } else if (action == 'pyc-ratio') {  # This takes different inputs
    all_deps_py = argv[[2]]
    ctx = MeasureFileSizes(all_deps_py)

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
