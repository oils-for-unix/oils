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

options(stringsAsFactors = F,
        # Make the report wide.  tibble.width doesn't appear to do this?
        width=200,
        tibble.print_max=Inf
)

Basic = function(ctx) {
  Banner('BASIC METRICS')

  # Number of files
  ctx$frames %>% count(path) -> by_path
  ShowValue('Number of files: %d', nrow(by_path))

  # 216K
  b = sum(ctx$frames$bytecode_bytes)
  ShowValue('Total bytecode bytes: %d', b)

  num_insts = nrow(ctx$ops)
  ShowValue('Total instructions: %d', num_insts)

  # Hm this isn't reliable because the code name isn't unique!  I think we need
  # firstlineno
  ctx$frames %>% count(path, code_name) %>% arrange(desc(n)) %>% head() -> f1
  ShowFrame('Duplicate path/name', f1)
}

BigStrings = function(consts) {
  Banner('BIG STRINGS')

  strs = consts %>% filter(type == 'str') %>% arrange(desc(len_or_val))
  strs %>% head(20) %>% print()
  total_bytes = sum(strs$len_or_val)

  # 184 KB of strings!  That's just the payload; the header is probably more.
  ShowValue('total string bytes: %d', total_bytes)

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
  Banner('CONSTS')

  # count of types of constants.  Strings dominate of course.
  # But there are only 7 or so immutable types!

  # - only 2 float constants.
  # - get rid of the unicode constants in posixpath.

  consts %>% count(type) %>% arrange(desc(n)) %>% head(20) -> frequent
  ShowFrame('Types of constants', frequent)
}

# Frames by number of consts, number of ops, etc.
Frames = function(ctx) {
  Banner('FRAMES')

  ctx$consts %>% count(path, code_name, sort=T) %>% head(20) -> f1
  ShowFrame('Frames with many consts', f1)

  ctx$ops %>% count(path, code_name, sort=T) %>% head(20) -> f2
  ShowFrame('Frames with many ops', f2)

  ctx$frames %>% arrange(desc(stacksize)) %>% head(10) -> f3
  ShowFrame('Frames with large stacksize', f3)

  ctx$frames %>% arrange(desc(nlocals)) %>% head(10) -> f4
  ShowFrame('Frames with many locals', f4)
}

# OpKind is FAST for LOAD_FAST, or SLICE for STORE_SLICE+1
#
# [,1] is the whole match, and [,2] is the first match.  Like $0 and $1 in
# normal regexes.
OpKind = function(op_name) {
  # optional +1 suffix
  str_match(op_name, '([A-Z]+)(?:\\+[0-9])?$')[,2]
}

Ops = function(ops, ops_defined = '_tmp/opcodes-defined.txt') {
  Banner('OPS')

  ops %>% count(op_name) %>% arrange(desc(n)) -> op_freq

  ShowFrame('Ops Used by Frequency', op_freq)

  u2 = ops %>% distinct(op_name) 
  ShowValue('Total unique opcodes: %d', nrow(u2))

  if (ops_defined != '') {
    defined = read.table(ops_defined, header=F)
    colnames(defined) = c('op_name')

    setdiff(defined, u2) -> f4
    ShowFrame('Unused opcodes:', f4)
  }

  op_freq %>%
    filter(str_detect(op_name, 'LOAD|STORE|FAST')) %>%
    mutate(kind = OpKind(op_name)) %>%
    arrange(kind) %>%
    select(kind, op_name, n) -> mem_ops
  ShowFrame('Memory Operations:', mem_ops)

  # NOTE: got rid of IMPORT_STAR!
  ops %>% filter(str_detect(op_name, 'IMPORT')) %>% count(op_name) -> imports
  ShowFrame('Imports:', imports)

  # These are all the big jump targets!  Max is 3,852, which is a lot less than
  # 65,536.  We don't need EXTENDED_ARG!
  ops %>% arrange(desc(op_arg)) %>% head(10) -> f1
  ShowFrame('Large op_arg (jump targets):', f1)
}

Flags = function(flags) {
  Banner('FLAGS')

  flags %>% count(flag) %>% arrange(desc(n)) -> f1
  ShowFrame('Common flags', f1)
}

Names = function(names) {
  Banner('NAMES')

  # Common types: free, cell, etc.
  names %>% count(kind) %>% arrange(desc(n)) %>% head(20) -> f1
  ShowFrame('Common types', f1)

  # Common names:
  # self, None, True, False, append, len
  names %>% count(name) %>% arrange(desc(n)) %>% head(20) -> f2
  ShowFrame('Common names', f2)

  names %>% mutate(len=nchar(name)) -> all
  names %>% count(name) %>% mutate(len=nchar(name)) -> unique

  ShowValue('Total length of all %d names: %d',
            nrow(all), sum(all$len))
  ShowValue('Total length of %d unique names: %d',
            nrow(unique), sum(unique$len))
}

# Hm max unique ops is 58
# _build/oil/bytecode-opy/core/cmd_exec.pyc     54
# _build/oil/bytecode-opy/warnings.pyc          55
# _build/oil/bytecode-opy/_abcoll.pyc           58
#
# But there are 119 total opcodes.  A lot of the math ones are uncommon.

# Written by opy/metrics.sh.  Could get rid of that file.
UniqueOpsByFile = function(ops) {
  Banner('UNIQUE OPS')

  # This is a row for every path/op_name
  u = ops %>% group_by(path) %>% distinct(op_name)
  u %>% count(path) %>% arrange(n) -> ops_by_file

  ops_by_file %>% head(20) -> f1
  ShowFrame('Files with few ops:', f1)

  ops_by_file %>% tail(10) -> f2
  ShowFrame('Files with many ops:', f2)

  ops_by_file %>% filter(grepl('reader|lex|parse', path)) -> f3
  ShowFrame('Unique ops for files that just parse:', f3)  # 17, 23, 34, 34, 46

  ops %>% filter(grepl('reader|lex|parse', path)) %>% distinct(op_name) ->
    string_ops
  ShowValue('Unique opcodes for parsing: %d', nrow(string_ops))
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

# This takes a table of (py_path, pyc_path) and calls file.info()$size on both.
# Then it computes the ratio.

FileSizes = function(all_deps_py, pyc_base_dir) {
  py_pyc = read.table(all_deps_py, header=F)
  colnames(py_pyc) = c('py_path', 'pyc_path')

  py_pyc$py_bytes = file.info(py_pyc$py_path)$size

  pyc_paths = file.path(pyc_base_dir, py_pyc$pyc_path)
  py_pyc$pyc_bytes = file.info(pyc_paths)$size

  py_pyc %>% filter(py_bytes != 0) %>% mutate(ratio = pyc_bytes / py_bytes) %>%
    arrange(ratio) -> py_pyc

  Banner('RATIO')

  py_pyc %>% head(10) -> small
  ShowFrame('small .pyc files:', small)

  py_pyc %>% tail(10) -> big
  ShowFrame('big .pyc files:', big)

  # This ratio is a ltitle misleading because it counts comments.
  py_total = sum(py_pyc$py_bytes)
  pyc_total =  sum(py_pyc$pyc_bytes)

  ShowValue('Overall: %d bytes of .py -> %d bytes of .pyc', py_total, pyc_total)
  ShowValue('Ratio: %f', pyc_total / py_total)

  Banner('FULL LISTING')

  py_pyc %>% select(c(pyc_bytes, pyc_path)) %>% arrange(desc(pyc_bytes)) -> f1
  ShowFrame('bytecode', f1)
  ShowValue('total (again): %d', pyc_total)

  py_pyc
}


CompareCol = function(ctx) {
  c(nrow(ctx$frames),
    nrow(ctx$names),
    nrow(ctx$consts),
    nrow(ctx$flags),
    nrow(ctx$ops)
  )
}

Compare = function(cpython_ctx, opy_ctx) {
  Banner('CPYTHON vs. OPY')

  data_frame(
    table_name = c('frames', 'names', 'consts', 'flags', 'ops'),
    cpython = CompareCol(cpython_ctx),
    opy = CompareCol(opy_ctx)
  ) -> f1

  ShowFrame('Overview', f1)

  Banner('Cell Variables')

  cpython_ctx$names %>% filter(kind == 'cell') -> f2
  opy_ctx$names %>% filter(kind == 'cell') -> f3

  ShowFrame('CPython', f2)
  ShowFrame('OPy', f3)
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'metrics') {
    in_dir = argv[[2]]
    ctx = Load(in_dir)
    Report(ctx)

  } else if (action == 'compare') {
    cpython_ctx = Load(argv[[2]])
    opy_ctx = Load(argv[[3]])
    Compare(cpython_ctx, opy_ctx)

  } else if (action == 'src-bin-ratio') {  # This takes different inputs
    all_deps_py = argv[[2]]
    pyc_base_dir = argv[[3]]
    ctx = FileSizes(all_deps_py, pyc_base_dir)

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))
  main(commandArgs(TRUE))
}
