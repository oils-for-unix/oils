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
        tibble.print_max=40
)

Report = function(ctx) {
  Banner('Summary of methods.tsv:')
  ctx$methods %>% count(used) %>% arrange(desc(n)) -> f0
  ShowFrame('Methods used:', f0)

  ctx$methods %>% filter(used == T) %>% count(file) %>% arrange(desc(n)) -> f1
  ShowFrame('Methods by file (after filtering):', f1)
  ShowValue('Kept %d of %d methods in %d files', sum(ctx$methods$used),
            nrow(ctx$methods), nrow(f1))

  ctx$methods %>% count(flags) %>% arrange(desc(n)) -> f2
  ShowFrame('Methods by flag', f2)
}

Load = function(in_dir) {
  list(
    methods = read.table(
      file.path(in_dir, 'methods.tsv'), sep='\t', header=T)
  )
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'metrics') {
    in_dir = argv[[2]]
    ctx = Load(in_dir)
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
