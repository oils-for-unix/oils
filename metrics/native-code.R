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
        width=200
)

# Categorize names:
# - _doc(__)?
# - PRETTY
# - init?

# frame: A table with 3 columns.  ctx$symbols or ctx$compileunits.
Basic = function(frame) {
  ShowValue('Rows: %d', nrow(frame))

  frame %>% arrange(desc(filesize)) %>% head(30) -> f1
  ShowFrame('By Size On Disk:', f1)

  ShowValue('Total filesize: %d', sum(frame$filesize))

  # Number of files
  frame %>% arrange(desc(vmsize)) %>% head(30) -> f2
  ShowFrame('By Size in Virtual Memory:', f2)

  ShowValue('Total vmsize: %d', sum(frame$vmsize))
}

Report = function(ctx) {
  Banner('Summary of symbols.tsv (from %s):', ctx$opt)
  Basic(ctx$symbols)

  Banner('Summary of compileunits.tsv (from %s):', ctx$dbg)
  Basic(ctx$compileunits)

  Banner('Other analysis:')

  # This isn't foolproof, but docstrings seem to be named with a _doc or
  # __doc__ suffix.
  ctx$symbols %>% filter(str_detect(symbols, '_doc(__)?')) -> f3
  ShowFrame('Big Docstrings (approximate, based on name)', f3 %>% head(20))

  ShowValue('%d symbols in %d bytes', nrow(f3), sum(f3$filesize))
}

Load = function(in_dir) {
  list(
    symbols = read.table(
      file.path(in_dir, 'symbols.tsv'), sep='\t', header=T),
    compileunits = read.table(
      file.path(in_dir, 'compileunits.tsv'), sep='\t', header=T)
  )
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'metrics') {
    in_dir = argv[[2]]
    ctx = Load(in_dir)

    ctx$dbg = argv[[3]]
    ctx$opt = argv[[4]]

    Report(ctx)

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
