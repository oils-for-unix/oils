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

UniqueOpsByFile = function(ops) {
  # This is a row for every path/op_name
  u = ops %>% group_by(path) %>% distinct(op_name)
  u
  u %>% count(path) %>% arrange(n) -> ops_by_file

  Log('files with few ops:')
  ops_by_file %>% head(20) %>% print()

  Log('files with many ops:')
  ops_by_file %>% tail(10) %>% print()

  Log('parsing:')  # 17, 23, 34, 34, 46
  ops_by_file %>% filter(grepl('parse', path)) %>% print()
}

Report = function(ctx) {
  Basic(ctx)
  BigStrings(ctx$consts)

  Frames(ctx)
  Names(ctx$names)
  Consts(ctx$consts)
  Flags(ctx$flags)
  Ops(ctx$ops)
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
